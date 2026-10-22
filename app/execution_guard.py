"""Recheck frozen execution inputs immediately before any worker effects."""
from .contracts import ContractError
from .execution_plan import build_plan
from .project_locks import project_lock
from .storage import read_json, write_json


def begin_execution(worker, job, payload):
    if not payload.get('agent_plan'):
        return None
    pid = job['project_id']
    with project_lock(worker.db, pid):
        project = worker.projects.path(pid)
        receipt_path = project / 'execution-plans' / ('job-' + job['id'] + '.json')
        receipt = read_json(receipt_path)
        revision = worker.projects.revision(pid)
        if receipt:
            if receipt.get('requires_replan') or revision != receipt['resume_revision']:
                raise ContractError('PLAN_STALE', '暂停后的项目输入已改变，请重新生成执行计划。', status=409)
            stored = read_json(project / 'execution-plans' / (payload['plan_id'] + '.json'))
            request = {**stored['request'], 'uids': stored['plan']['affected_uids']} if stored['plan']['affected_uids'] else stored['request']
            current = build_plan(worker.projects, worker.assets, worker.content, worker.config, pid,
                                 request, revision)
            if current['input_fingerprint'] != receipt['resume_input_fingerprint']:
                raise ContractError('PLAN_STALE', '暂停后的素材、原片或模型发生变化，请重新规划。', status=409)
            return receipt_path
        stored = read_json(project / 'execution-plans' / (payload['plan_id'] + '.json'))
        if not stored or revision != stored['plan']['revision']:
            raise ContractError('PLAN_STALE', '排队期间项目已改变，请重新生成执行计划。', status=409)
        plan = build_plan(worker.projects, worker.assets, worker.content, worker.config, pid,
                          stored['request'], revision)
        if plan['plan_id'] != payload['plan_id'] or not plan['ready']:
            raise ContractError('PLAN_STALE', '排队期间素材、模型或原片已改变，请重新生成执行计划。', status=409)
        write_json(receipt_path, {'plan_id': payload['plan_id'], 'resume_revision': revision,
                                 'resume_input_fingerprint': plan['input_fingerprint'],
                                 'environment_fingerprint': plan.get('environment_fingerprint')})
        return receipt_path


def checkpoint_execution(worker, job, receipt_path):
    if receipt_path is not None:
        with project_lock(worker.db, job['project_id']):
            previous = {}
            try:
                previous = read_json(receipt_path, {})
                pid = job['project_id']
                revision = worker.projects.revision(pid)
                stored = read_json(worker.projects.path(pid) / 'execution-plans' / (previous['plan_id'] + '.json'))
                request = {**stored['request'], 'uids': stored['plan']['affected_uids']} if stored['plan']['affected_uids'] else stored['request']
                current = build_plan(worker.projects, worker.assets, worker.content, worker.config, pid,
                                     request, revision)
                if current.get('environment_fingerprint') != previous.get('environment_fingerprint'):
                    raise ContractError('PLAN_STALE', '执行期间模型或环境配置已改变，需要重新规划。', status=409)
                if stored['request']['action'] in ('render', 'finish') and revision != previous['resume_revision']:
                    raise ContractError('PLAN_STALE', '执行期间项目输入已改变，需要重新规划。', status=409)
                write_json(receipt_path, {**previous, 'resume_revision': revision,
                                         'resume_input_fingerprint': current['input_fingerprint']})
            except Exception as exc:
                worker.log_failure(exc)
                try:
                    write_json(receipt_path, {**previous, 'requires_replan': True})
                except OSError as failure:
                    worker.log_failure(failure)
