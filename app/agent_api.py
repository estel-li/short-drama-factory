"""Agent-oriented operations layered on the existing production services."""
from __future__ import annotations

import copy

from fastapi import APIRouter, Header

from .agent_contracts import AgentCreate, ProjectChange, PlanRequest, RunRequest, ResumeRequest, StopRequest
from .contracts import ContractError
from .project_locks import project_lock
from .storage import read_json, write_json


def deep_merge(original, changes):
    value = copy.deepcopy(original)
    for key, item in changes.items():
        value[key] = deep_merge(value[key], item) if isinstance(item, dict) and isinstance(value.get(key), dict) else copy.deepcopy(item)
    return value


def check_revision(projects, pid, expected):
    actual = projects.revision(pid)
    if actual != expected:
        raise ContractError('REVISION_CONFLICT', '项目已被修改，请重新读取后合并改动。', status=409,
                            details=[{'field': 'expected_revision', 'expected': expected, 'actual': actual}],
                            next_actions=['inspect_project', 'merge_changes'])
    return actual


def install_agent_routes(app, services):
    router = APIRouter(prefix='/api/v2')

    def view(s, pid):
        return {**s.projects.get(pid), 'revision': s.projects.revision(pid)}

    def dispatch(s, jid):
        s.worker.start(recover=False)
        s.worker.allow_job(jid)

    def replay(s, key, scope, payload):
        receipt = s.db.reserve_operation(key, scope, payload)
        return receipt, receipt['result'] if receipt['status'] == 'completed' else None

    @router.get('/operations/{key}')
    def operation_get(key: str):
        receipt = services().db.operation(key)
        if receipt is None:
            raise ContractError('OPERATION_NOT_FOUND', '没有此请求的提交记录。', status=404,
                                next_actions=['verify_instance', 'submit_with_same_key'])
        return receipt

    @router.get('/projects/{pid}')
    def project_get(pid: str):
        s = services()
        with project_lock(s.db, pid):
            return view(s, pid)

    @router.post('/projects', status_code=201)
    def create(body: AgentCreate, idempotency_key: str = Header(...)):
        s = services()
        payload = body.model_dump()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt, result = replay(s, idempotency_key, 'project.create', payload)
            if result is not None:
                return result
            pid = 'agent_' + receipt['operation_id'][:24]
            s.projects.create_reserved(pid, body.input, body.options, payload['storyboard'], receipt['operation_id'])
            result = {'id': pid, 'job_id': None, 'revision': s.projects.revision(pid),
                      'operation_id': receipt['operation_id'], 'request_key': idempotency_key}
            s.db.complete_operation(idempotency_key, result)
            return result

    @router.patch('/projects/{pid}')
    def update(pid: str, body: ProjectChange, idempotency_key: str = Header(...)):
        s = services()
        payload = body.model_dump(exclude_none=True)
        with project_lock(s.db, 'operation:' + idempotency_key), project_lock(s.db, pid):
            receipt, result = replay(s, idempotency_key, 'project.update:' + pid, payload)
            if result is not None:
                return result
            recovered = read_json(s.projects.path(pid) / 'state.json', {}).get('mutation_receipts', {}).get(idempotency_key)
            if recovered and recovered['request_hash'] == receipt['request_hash']:
                s.db.complete_operation(idempotency_key, recovered['result'])
                return recovered['result']
            check_revision(s.projects, pid, body.expected_revision)
            s.projects.assert_idle(pid)
            before = s.projects.get(pid)
            if body.settings is not None:
                s.projects.save_options(pid, deep_merge(before['settings'], body.settings), operation=receipt)
            else:
                story = copy.deepcopy(before['story']) if body.shots is not None else body.story.model_dump()
                if body.shots is not None:
                    if not story:
                        raise ContractError('STORY_REQUIRED', '项目尚无分镜。', status=409)
                    by_uid = {shot['uid']: shot for shot in story['shots']}
                    from .schemas import Shot
                    from .quality import POST_FIELDS
                    writable = set(Shot.model_fields) | POST_FIELDS | {'seed_offset', 'prompt_template_id'}
                    for edit in body.shots:
                        if edit.uid not in by_uid:
                            raise ContractError('SHOT_NOT_FOUND', '镜头 UID 不存在。', status=404)
                        if set(edit.changes) - writable or set(edit.changes) & {'uid', 'id'}:
                            raise ContractError('INVALID_SHOT_PATCH', '镜头修改包含不可写字段；保留 UID 与顺序编号。')
                        by_uid[edit.uid].update(edit.changes)
                s.projects.save_story(pid, story, operation=receipt)
            after = s.projects.get(pid)
            result = after['state']['mutation_receipts'][idempotency_key]['result']
            s.db.complete_operation(idempotency_key, result)
            return result

    @router.post('/projects/{pid}/validate')
    def validate(pid: str):
        s = services()
        from .execution_policy import validate_external_story
        from .workflow_checks import workflow_report
        with project_lock(s.db, pid):
            project = s.projects.path(pid)
            story, options = s.projects.get(pid)['story'], s.projects.options(project)
            resolve = lambda shot, value: s.assets.resolve(project, shot, value, inspect_media=True)
            validate_external_story(story, options, resolve, s.content.mode)
            return {'revision': s.projects.revision(pid),
                    **workflow_report(story, options, s.config.renderer_config(), resolve, s.content.mode)}

    @router.post('/projects/{pid}/plans', status_code=201)
    def plan(pid: str, body: PlanRequest):
        s = services()
        from .execution_plan import build_plan
        with project_lock(s.db, pid):
            revision = s.projects.revision(pid)
            value = build_plan(s.projects, s.assets, s.content, s.config, pid, body.model_dump(), revision)
            write_json(s.projects.path(pid) / 'execution-plans' / (value['plan_id'] + '.json'),
                       {'request': body.model_dump(), 'plan': value})
            return value

    @router.get('/projects/{pid}/plans/{plan_id}')
    def plan_get(pid: str, plan_id: str):
        s = services()
        from .storage import identifier
        identifier(plan_id)
        stored = read_json(s.projects.path(pid) / 'execution-plans' / (plan_id + '.json'))
        if not stored:
            raise ContractError('PLAN_NOT_FOUND', '执行计划不存在。', status=404)
        return stored['plan']

    @router.post('/projects/{pid}/run', status_code=202)
    def run(pid: str, body: RunRequest, idempotency_key: str = Header(...)):
        s = services()
        from .execution_plan import build_plan
        payload = body.model_dump()
        with project_lock(s.db, 'operation:' + idempotency_key), project_lock(s.db, pid):
            receipt, result = replay(s, idempotency_key, 'project.run:' + pid, payload)
            if result is not None:
                if (s.db.job(result['job_id']) or {}).get('status') == 'queued':
                    dispatch(s, result['job_id'])
                return result
            s.projects.assert_idle(pid)
            stored = read_json(s.projects.path(pid) / 'execution-plans' / (body.plan_id + '.json'))
            if not stored:
                raise ContractError('PLAN_NOT_FOUND', '执行计划不存在。', status=404)
            check_revision(s.projects, pid, stored['plan']['revision'])
            current = build_plan(s.projects, s.assets, s.content, s.config, pid, stored['request'], stored['plan']['revision'])
            if current['plan_id'] != body.plan_id:
                raise ContractError('PLAN_STALE', '素材、模型配置或原片已改变，请重新计算计划。', status=409,
                                    next_actions=['create_execution_plan'])
            if not current['ready']:
                raise ContractError('PLAN_BLOCKED', '执行计划有阻塞项，尚未排队。', status=409,
                                    details=current.get('blocked', []), next_actions=['resolve_blockers'])
            request = stored['request']
            job_payload = {'internal_text': request['internal_text'], 'plan_id': body.plan_id,
                           'agent_plan': True, 'strict_render': request['action'] == 'render',
                           'allowed_uids': current['affected_uids']}
            if request.get('regenerate'):
                job_payload['regenerate_uids'] = current['affected_uids']
            result = s.db.enqueue_operation(idempotency_key, 'project.run:' + pid, payload,
                                            pid, request['action'], job_payload)
        dispatch(s, result['job_id'])
        return result

    @router.post('/jobs/{jid}/resume', status_code=202)
    def resume(jid: str, body: ResumeRequest, idempotency_key: str = Header(...)):
        s = services()
        payload = body.model_dump()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt, result = replay(s, idempotency_key, 'job.resume:' + jid, payload)
            if result is not None:
                if (s.db.job(result['job_id']) or {}).get('status') == 'queued':
                    dispatch(s, result['job_id'])
                return result
            job = s.db.job(jid)
            if job is None:
                raise ContractError('JOB_NOT_FOUND', '任务不存在。', status=404)
            if job['status'] == 'running':
                s.worker.recover_orphaned_jobs(jid)
            with project_lock(s.db, job['project_id']):
                if body.expected_revision:
                    check_revision(s.projects, job['project_id'], body.expected_revision)
                result = s.db.requeue_operation(idempotency_key, 'job.resume:' + jid, payload, jid)
        dispatch(s, jid)
        return result

    @router.post('/jobs/{jid}/stop')
    def stop(jid: str, body: StopRequest, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt, result = replay(s, idempotency_key, 'job.stop:' + jid, body.model_dump())
            if result is not None:
                return result
            job = s.db.job(jid)
            if job is None:
                raise ContractError('JOB_NOT_FOUND', '任务不存在。', status=404)
            if job['status'] == 'running':
                s.worker.recover_orphaned_jobs(jid)
                job = s.db.job(jid)
            if job['status'] in ('queued', 'running'):
                if job['project_id'].startswith(('__environment', '__series_')):
                    s.db.cancel(job['project_id'])
                else:
                    s.worker.stop(job['project_id'])
                if body.immediate:
                    s.worker.interrupt_owned(job['project_id'])
            result = {'job_id': jid, 'status': s.db.job(jid)['status'], 'cancel_requested': bool(s.db.job(jid)['cancel_requested'])}
            s.db.complete_operation(idempotency_key, result)
            return result

    app.include_router(router)
