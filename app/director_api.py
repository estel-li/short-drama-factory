"""Headless director evidence, Skill publishing, selection and authored review."""
import copy
from pathlib import Path
import shutil
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Header
from fastapi.responses import FileResponse
from pydantic import Field

from .agent_api import check_revision
from .contracts import ContractError
from .director_contracts import (StrictModel, PrepareReference, EvidenceClip, PublishDirectorStyle,
                                BindDirectorStyle, DirectorReview, InstallDirectorStyle, ImportDirectorStyle)
from .director_media import source_path, sha256, probe
from .director_styles import DirectorStyles, binding, package_files, project_profile, brief, style_check, review_status
from .project_locks import project_lock
from .storage import contained, digest, read_json, write_json


class ClearStyle(StrictModel):
    expected_revision: str = Field(min_length=1)


def install_director_routes(app, services):
    router = APIRouter(prefix='/api/v2')

    def dispatch(s, result):
        if (s.db.job(result['job_id']) or {}).get('status') == 'queued':
            s.worker.start(recover=False)
            s.worker.allow_job(result['job_id'])

    @router.post('/director/analyses', status_code=202)
    def prepare(body: PrepareReference, idempotency_key: str = Header(...)):
        s, library = services(), DirectorStyles()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, 'director.prepare', body.model_dump())
            if receipt['status'] == 'completed':
                result = receipt['result']
            else:
                source_path(body.source_path)
                aid = receipt['operation_id']
                folder = library.analysis_path(aid)
                write_json(folder / 'request.json', {'request': body.model_dump(), 'operation_id': aid})
                result = s.db.enqueue_operation(idempotency_key, 'director.prepare', body.model_dump(), '__director_' + aid,
                    'director-prepare', {'analysis_id': aid, 'library': str(library.root), 'internal_text': 'forbid', 'allow_downloads': False},
                    result_fields={'analysis_id': aid, 'directory': str(folder)})
            folder = library.analysis_path(result['analysis_id'])
            record = read_json(folder / 'request.json')
            if not record:
                raise ContractError('DIRECTOR_ANALYSIS_MISSING', '原分析目录已丢失，不能自动重建为另一个参考片。', status=409)
            record['job_id'] = result['job_id']
            write_json(folder / 'request.json', record)
            dispatch(s, result)
            return result

    @router.get('/director/analyses/{aid}')
    def analysis(aid: str):
        value = copy.deepcopy(DirectorStyles().analysis(aid))
        job = services().db.job(value.get('job_id', ''))
        value['job_status'] = job.get('status') if job else None
        for item in value.get('artifacts', []):
            item['local_path'] = str(contained(value['directory'], item['path']))
            item['api_url'] = '/api/v2/director/analyses/' + quote(aid, safe='') + '/files/' + quote(item['path'], safe='/')
        return value

    @router.get('/director/analyses/{aid}/files/{relative:path}', response_class=FileResponse)
    def analysis_file(aid: str, relative: str):
        library = DirectorStyles()
        value = library.analysis(aid)
        item = next((item for item in value.get('artifacts', []) if item['path'] == relative), None)
        path = contained(library.analysis_path(aid), relative)
        if not item or not path.is_file():
            raise ContractError('DIRECTOR_EVIDENCE_NOT_FOUND', '证据文件不在已发布清单中。', status=404)
        return FileResponse(path, filename=path.name)

    @router.post('/director/analyses/{aid}/clips', status_code=202)
    def extra_clip(aid: str, body: EvidenceClip, idempotency_key: str = Header(...)):
        s, library = services(), DirectorStyles()
        with project_lock(s.db, 'operation:' + idempotency_key), library.lock('analysis-' + aid):
            scope = 'director.clip:' + aid
            receipt = s.db.reserve_operation(idempotency_key, scope, body.model_dump())
            if receipt['status'] == 'completed':
                result = receipt['result']
            else:
                evidence = library.analysis(aid)
                if evidence['status'] != 'prepared' or body.start < evidence['range']['start'] or body.end > evidence['range']['end']:
                    raise ContractError('DIRECTOR_CLIP_RANGE', '补充片段必须在已完成提取的区间内。', status=409)
                result = s.db.enqueue_operation(idempotency_key, scope, body.model_dump(), '__director_' + aid, 'director-clip',
                    {'analysis_id': aid, 'library': str(library.root), 'clip': body.model_dump(), 'clip_id': receipt['operation_id'],
                     'internal_text': 'forbid', 'allow_downloads': False}, result_fields={'analysis_id': aid})
        dispatch(s, result)
        return result

    @router.get('/director/styles')
    def list_styles():
        return DirectorStyles().listing()

    @router.post('/director/styles', status_code=201)
    def publish(body: PublishDirectorStyle, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, 'director.publish', body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            result = DirectorStyles().publish(body, receipt['operation_id'])
            result.update(request_key=idempotency_key, operation_id=receipt['operation_id'])
            s.db.complete_operation(idempotency_key, result)
            return result

    @router.get('/director/styles/{style_id}')
    def get_style(style_id: str, version: str | None = None):
        return DirectorStyles().get(style_id, version)

    @router.post('/director/styles/import', status_code=201)
    def import_style(body: ImportDirectorStyle, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, 'director.import', body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            result = DirectorStyles().import_package(body.package_directory, body.expected_version, receipt['operation_id'],
                                                    body.manifest_sha256, body.style_id, body.version)
            s.db.complete_operation(idempotency_key, result)
            return result

    @router.get('/director/styles/{style_id}/brief')
    def get_brief(style_id: str, version: str, mode: str = 'inspired'):
        if mode not in ('inspired', 'remake'):
            raise ContractError('DIRECTOR_MODE_INVALID', 'mode 应为 inspired 或 remake。')
        profile = DirectorStyles().get(style_id, version)['profile']
        if mode == 'remake' and not profile['shot_structure']:
            raise ContractError('DIRECTOR_STRUCTURE_REQUIRED', '此风格尚无可仿拍的参考结构。', status=409)
        return {'style_id': style_id, 'version': version, 'mode': mode, 'brief': brief(profile, mode), 'profile': profile}

    @router.post('/director/styles/{style_id}/versions/{version}/install', status_code=201)
    def install(style_id: str, version: str, body: InstallDirectorStyle, idempotency_key: str = Header(...)):
        s = services()
        scope = 'director.install:' + style_id + ':' + version
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, scope, body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            result = DirectorStyles().install(style_id, version, body.target_directory, receipt['operation_id'])
            s.db.complete_operation(idempotency_key, result)
            return result

    def set_binding(s, pid, body, key, selection):
        scope = 'director.bind:' + pid if selection is not None else 'director.clear:' + pid
        with project_lock(s.db, 'operation:' + key), project_lock(s.db, pid):
            receipt = s.db.reserve_operation(key, scope, body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            project = s.projects.path(pid)
            old = read_json(project / 'director-style.json', {})
            recovered = old.get('_receipts', {}).get(key)
            if recovered and recovered['request_hash'] == receipt['request_hash']:
                s.db.complete_operation(key, recovered['result'])
                return recovered['result']
            check_revision(s.projects, pid, body.expected_revision)
            s.projects.assert_idle(pid)
            selected = {}
            if selection is not None:
                value = DirectorStyles().get(body.style_id, body.version)
                if body.mode == 'remake' and not value['profile']['shot_structure']:
                    raise ContractError('DIRECTOR_STRUCTURE_REQUIRED', '此风格缺少参考结构；请选择风格迁移或补充分析。', status=409)
                relative = 'director-styles/' + body.style_id + '/' + body.version
                target = contained(project, relative)
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    stage = target.with_name(target.name + '.stage-' + uuid.uuid4().hex)
                    try:
                        shutil.copytree(value['directory'], stage)
                        staged_manifest, _ = package_files(stage)
                        if staged_manifest != value['manifest']:
                            raise ContractError('DIRECTOR_PACKAGE_CHANGED', '复制期间风格包改变，请检查后重试。', status=409)
                        stage.rename(target)
                    finally:
                        if stage.exists() and stage.resolve().is_relative_to(project.resolve()):
                            shutil.rmtree(stage)
                manifest, _ = package_files(target)
                if manifest != value['manifest']:
                    raise ContractError('DIRECTOR_SNAPSHOT_CHANGED', '项目中同版本的风格快照已改变，不能当作原版本重新绑定。', status=409)
                selected = {'style_id': body.style_id, 'version': body.version, 'mode': body.mode,
                            'package': relative, 'profile_hash': manifest['profile_hash'], 'package_hash': digest(manifest['files'])}
            revision = s.projects.revision(pid, director_style=selected)
            result = {'id': pid, 'selection': selected, 'revision': revision, 'request_key': key}
            saved = {**selected, '_receipts': old.get('_receipts', {})}
            saved['_receipts'][key] = {'request_hash': receipt['request_hash'], 'result': result}
            write_json(project / 'director-style.json', saved)
            s.db.complete_operation(key, result)
            return result

    @router.post('/projects/{pid}/director-style')
    def bind_style(pid: str, body: BindDirectorStyle, idempotency_key: str = Header(...)):
        return set_binding(services(), pid, body, idempotency_key, True)

    @router.post('/projects/{pid}/director-style/clear')
    def clear_style(pid: str, body: ClearStyle, idempotency_key: str = Header(...)):
        return set_binding(services(), pid, body, idempotency_key, None)

    @router.get('/projects/{pid}/director-style')
    def project_style(pid: str):
        s = services()
        with project_lock(s.db, pid):
            project = s.projects.path(pid)
            profile = project_profile(project)
            selected = binding(project)
            final = project / '成片.mp4'
            return {'selection': selected, 'profile': profile, 'brief': brief(profile, selected['mode']) if profile else '',
                    'check': style_check(s.projects, pid), 'revision': s.projects.revision(pid),
                    'review': review_status(s.projects, pid, sha256(final) if final.is_file() else None)}

    @router.post('/projects/{pid}/director-style/review')
    def review(pid: str, body: DirectorReview, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key), project_lock(s.db, pid):
            receipt = s.db.reserve_operation(idempotency_key, 'director.review:' + pid, body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            project = s.projects.path(pid)
            saved = read_json(project / 'director-style-review.json', {})
            if receipt['operation_id'] in saved.get('_receipts', {}):
                result = saved['_receipts'][receipt['operation_id']]
                s.db.complete_operation(idempotency_key, result)
                return result
            check_revision(s.projects, pid, body.expected_revision)
            s.projects.assert_idle(pid)
            profile = project_profile(project)
            final = project / '成片.mp4'
            if not profile or not final.is_file() or sha256(final) != body.final_sha256:
                raise ContractError('DIRECTOR_REVIEW_STALE', '需要已绑定的风格以及与当前成片相符的 SHA256。', status=409)
            ids = [item.rule_id for item in body.assessments]
            if len(set(ids)) != len(ids) or set(ids) != {rule['id'] for rule in profile['rules']}:
                raise ContractError('DIRECTOR_REVIEW_INCOMPLETE', '须逐项记录全部规则；未检查项明确使用 not_checked。')
            duration = probe(final)['duration']
            for assessment in body.assessments:
                if assessment.status != 'not_checked' and not assessment.evidence:
                    raise ContractError('DIRECTOR_REVIEW_EVIDENCE', '通过/失败的判断需要成片时间码依据。')
                if any(span.end > duration + .1 for span in assessment.evidence):
                    raise ContractError('DIRECTOR_REVIEW_EVIDENCE', '验收依据超出当前成片时长。')
            result = {'id': pid, 'recorded': True, 'request_key': idempotency_key}
            receipts = {**saved.get('_receipts', {}), receipt['operation_id']: result}
            write_json(project / 'director-style-review.json', {'revision': body.expected_revision,
                'final_sha256': body.final_sha256, 'selection': binding(project),
                'assessments': [item.model_dump() for item in body.assessments],
                '_receipts': receipts})
            s.db.complete_operation(idempotency_key, result)
            return result

    app.include_router(router)
