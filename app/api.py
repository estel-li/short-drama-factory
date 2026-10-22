from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request, UploadFile, File, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .assets import Assets
from .config import ConfigStore
from .content import Content
from .database import Database
from .environment import catalog, hardware
from .jobs import Worker
from .projects import Projects
from .providers import LLMClient, ProviderError
from .schemas import Options, durations
from .image_schemas import ImageSettings, ImageModels, ImageRequest
from .skills import Skills
from .storage import ROOT, contained, now, read_json, write_json
from .transfer import Transfer
from .version import VERSION, PROTOCOL_VERSION
from .contracts import (ContractError, CreateProjectRequest, SaveStoryRequest, ValidateStoryRequest,
                        StageRequest, JobView, error_body, job_view, safe_message)

config = ConfigStore()
db = Database()
projects = Projects(config, db)
skills = Skills()
assets = Assets(config, projects)
content = Content(config, skills, projects)
worker = Worker(db, config, projects, content, assets)
transfer = Transfer(config, projects, skills)


@asynccontextmanager
async def lifespan(app):
    worker.start()
    yield
    worker.shutdown.set()
    worker.wake.set()


app = FastAPI(title='短剧工厂', version=VERSION, lifespan=lifespan)


@app.middleware('http')
async def local_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    host = request.headers.get('host', '')
    try:
        hostname = urlsplit('//' + host).hostname
    except ValueError:
        hostname = None
    if hostname not in ('127.0.0.1', 'localhost', '::1'):
        return JSONResponse({'error': '工作台仅接受本机地址，请使用 127.0.0.1 或 localhost。'}, status_code=403)
    if request.method not in ('GET', 'HEAD') and origin and origin not in ('http://' + host, 'https://' + host):
        return JSONResponse({'error': '请求来源不允许。'}, status_code=403)
    try:
        size = int(request.headers.get('content-length', '0'))
    except ValueError:
        return JSONResponse({'error': '无效请求长度。'}, status_code=400)
    if size > (2 * 1024**3 if request.url.path == '/api/import' else 12_000_000):
        return JSONResponse({'error': '请求体上限 12MB。'}, status_code=413)
    response = await call_next(request)
    if request.url.path.startswith('/api') or request.url.path == '/' or request.url.path.startswith('/web/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


def validation_message(errors):
    labels = {'body':'', 'characters':'人物列表', 'shots':'分镜', 'title':'标题', 'premise':'故事主线',
              'beats':'剧情节拍', 'duration':'时长', 'visual_description':'人物外观', 'id':'编号', 'uid':'镜头编号',
              'use_previous_last_frame':'首帧功能', 'scene':'场景', 'seed':'随机种子', 'providers':'提供商',
              'base_url':'服务地址', 'name':'名称', 'settings':'项目设置', 'profile':'视频质量',
              'notes':'成片注释','masks':'遮罩','start':'开始时间','end':'结束时间','text':'文字','review_interval':'抽帧间隔','edit_preset':'剪辑强度'}
    messages = {'list_type':'请填写列表格式（JSON 数组）', 'dict_type':'请填写对象格式（JSON 对象）',
                'string_type':'请填写文字', 'bool_type':'请填写 true 或 false', 'bool_parsing':'请填写 true 或 false',
                'missing':'请补充这一项', 'int_parsing':'请填写整数', 'int_type':'请填写整数',
                'float_parsing':'请填写有效数字', 'float_type':'请填写有效数字', 'finite_number':'请填写有限数字',
                'string_too_short':'文字内容不足', 'string_too_long':'文字超出长度限制',
                'too_short':'项目数量不足', 'too_long':'项目数量过多', 'literal_error':'请选择有效选项'}
    parts = []
    for error in errors[:5]:
        location = ' / '.join(str(part + 1) if isinstance(part, int) else labels.get(part, part) for part in error.get('loc', ()) if part != 'body')
        kind, context = error.get('type'), error.get('ctx', {})
        message = messages.get(kind, error.get('msg', '请检查填写内容').removeprefix('Value error, '))
        if kind == 'greater_than_equal': message = '不能小于 ' + str(context.get('ge'))
        if kind == 'less_than_equal': message = '不能大于 ' + str(context.get('le'))
        parts.append((location + '：' if location else '') + message)
    return '\n'.join(parts)


@app.exception_handler(RequestValidationError)
async def request_validation_error(request, exc):
    details = [{'field': '.'.join(str(x) for x in e.get('loc', ())), 'type': e['type'],
                'message': safe_message(validation_message([e]))} for e in exc.errors()[:20]]
    legacy = getattr(request.scope.get('route'), 'name', '') in {
        'project_create', 'project_settings', 'story_save', 'story_validate', 'run_stage'}
    return JSONResponse(error_body('VALIDATION_ERROR', validation_message(exc.errors()), details=details,
                                  next_actions=['correct_fields', 'retry_request']), status_code=400 if legacy else 422)


@app.exception_handler(ContractError)
async def contract_error(request, exc):
    return JSONResponse(error_body(exc.code, str(exc), retryable=exc.retryable,
                                  details=exc.details, next_actions=exc.next_actions), status_code=exc.status)


@app.exception_handler(ValueError)
@app.exception_handler(RuntimeError)
async def value_error(request, exc):
    message = validation_message(exc.errors()) if isinstance(exc, ValidationError) else str(exc)[:2000]
    details = [{'field': '.'.join(str(x) for x in e.get('loc', ())), 'type': e['type'],
                'message': safe_message(validation_message([e]))} for e in exc.errors()[:20]] if isinstance(exc, ValidationError) else []
    return JSONResponse(error_body('VALIDATION_ERROR' if details else 'OPERATION_REJECTED', message,
                                  details=details, next_actions=['inspect_request', 'inspect_project']), status_code=400)


@app.get('/')
def home():
    return FileResponse(ROOT / 'web' / 'index.html' if (ROOT / 'web' / 'index.html').exists() else ROOT / 'index.html')


@app.get('/api/config')
def get_config():
    value = config.public()
    value.update(profiles=config.renderer_config().get('profiles', {}), comfy_url=config.renderer_config().get('comfy_url'), api_key_configured=bool(config.key('deepseek')))
    value['image_models'] = image_model_catalog()['models']
    value['video_workflows'] = video_workflow_catalog()['workflows']
    return value


@app.post('/api/config')
def save_config(body: dict):
    if worker.active:
        raise ValueError('任务执行中，请完成或停止后修改全局配置。')
    value = config.save(body)
    projects.refresh()
    return value


@app.post('/api/provider/key')
def provider_key(body: dict):
    config.set_key(body['id'], body.get('key', ''))
    return {'ok': True}


@app.post('/api/key')
def old_key(body: dict):
    config.set_key('deepseek', body['key'])
    return {'ok': True}


@app.get('/api/providers/{pid}/models')
def provider_models(pid: str):
    return {'models': LLMClient(config.provider(pid), config.key(pid), config.get().get('proxy', '')).models()}


@app.post('/api/providers/{pid}/test')
def provider_test(pid: str, body: dict):
    if worker.active:
        raise ValueError('已有任务执行中，请完成或停止后测试模型。')
    client = LLMClient(config.provider(pid), config.key(pid), config.get().get('proxy', ''))
    with worker.execution_lock:
        if client.provider.local:
            content.prepare_local(lambda message: None)
        try:
            if body.get('probe'):
                return client.probe(body.get('model', ''))
            return client.generate([{'role': 'user', 'content': '用一句中文回答：连接测试成功。'}], model=body.get('model', ''))
        finally:
            if client.provider.local and client.provider.unload_after_use:
                client.unload(body.get('model', ''))


@app.post('/api/providers/{pid}/unload')
def provider_unload(pid: str, body: dict):
    return LLMClient(config.provider(pid), config.key(pid), config.get().get('proxy', '')).unload(body.get('model', ''))


@app.get('/api/skills')
def skills_list():
    return skills.list()


@app.get('/api/skills/{sid}')
def skill_get(sid: str):
    return skills.get(sid)


@app.post('/api/skills/{sid}')
def skill_save(sid: str, body: dict):
    if worker.active:
        raise ValueError('任务执行中，请停止后修改 Skill，以免同一项目混用不同规则。')
    return skills.save(sid, body['metadata'], body['files'])


@app.get('/api/presets')
def get_presets():
    return {'builtin': read_json(ROOT / 'presets' / 'builtin.json'), 'personal': read_json(ROOT / 'presets' / 'personal.json', {})}


@app.post('/api/presets')
def save_presets(body: dict):
    from .storage import identifier
    name = identifier(body['id'])
    options = Options.model_validate(body['options'])
    durations(options)
    value = read_json(ROOT / 'presets' / 'personal.json', {})
    value[name] = {'name': body.get('name', name), 'options': options.model_dump()}
    write_json(ROOT / 'presets' / 'personal.json', value)
    return {'ok': True}


@app.post('/api/duration-plan')
def duration_plan(body: dict):
    return durations(Options.model_validate(body))


@app.get('/api/projects')
def projects_list():
    return projects.list()


@app.get('/api/series')
def series_list():
    return worker.series.list()


@app.get('/api/series/{sid}')
def series_get(sid: str):
    return worker.series.get(sid)


@app.post('/api/series', status_code=202)
def series_create(body: dict):
    sid, start = worker.series.create(body)
    value = worker.series.get(sid)
    ids = []
    if start != 'draft':
        if value['mode'] == 'auto':
            ids = [worker.enqueue('__series_' + sid, 'series-plan', {'series_id': sid, 'start': start})]
        else:
            ids = worker.series.enqueue_batch(sid, kind=start)
            worker.wake.set()
    return {'id': sid, 'job_ids': ids}


@app.post('/api/series/{sid}/plan', status_code=202)
def series_plan(sid: str, body: dict):
    start = body.get('start', 'draft')
    if start not in ('draft', 'plan', 'all'):
        raise ValueError('请选择规划后保存、文字规划或全自动成片。')
    return {'job_id': worker.enqueue('__series_' + sid, 'series-plan', {'series_id': sid, 'start': start})}


@app.post('/api/series/{sid}/batch', status_code=202)
def series_batch(sid: str, body: dict):
    if db.busy('__series_' + sid):
        raise ValueError('整剧分集规划仍在执行，请完成或停止后再排队单集。')
    ids = worker.series.enqueue_batch(sid, body.get('numbers'), body.get('kind', 'all'))
    worker.wake.set()
    return {'job_ids': ids}


@app.post('/api/series/{sid}/stop')
def series_stop(sid: str):
    return worker.series.stop(sid)


@app.get('/api/project/{pid}')
def project_get(pid: str):
    return projects.get(pid)


@app.post('/api/projects')
def project_create(body: CreateProjectRequest):
    body = body.model_dump(exclude_unset=True)
    project = projects.create(body.get('input', ''), body.get('options', {}), body.get('storyboard'))
    jid = worker.enqueue(project.name, 'all') if body.get('start', True) else None
    return {'id': project.name, 'job_id': jid}


@app.post('/api/create', status_code=202)
def old_create(body: dict):
    options = {k: v for k, v in body.items() if k in Options.model_fields}
    options['execution_mode'] = 'auto'
    project = projects.create(body.get('outline', ''), options)
    jid = worker.enqueue(project.name, 'plan' if body.get('plan_only') else 'all')
    return {'id': project.name, 'job_id': jid}


@app.post('/api/projects/{pid}/settings')
def project_settings(pid: str, body: Options):
    return projects.save_options(pid, body.model_dump())


@app.post('/api/story')
def story_save(body: SaveStoryRequest):
    body = body.model_dump()
    return projects.save_story(body['id'], body['story'])


@app.post('/api/projects/{pid}/validate-story')
def story_validate(pid: str, body: ValidateStoryRequest):
    body = body.model_dump()
    projects.path(pid)
    return projects.normalize(pid, body.get('story'))


@app.post('/api/projects/{pid}/outline')
def outline_save(pid: str, body: dict):
    from .schemas import Outline
    projects.assert_idle(pid)
    value = Outline.model_validate(body).model_dump()
    project = projects.path(pid)
    before = read_json(project / 'outline.json')
    if before:
        projects.version(project, 'outline-before-edit', before)
    write_json(project / 'outline.json', value)
    if before != value:
        worker.invalidate(project, ('分镜.json',), 'outline-edited-storyboard')
        projects.archive_final(project)
        state = read_json(project / 'state.json', {})
        state.update(status='review', message='大纲已保存，继续后将重新生成受影响的分镜。', current_stage='outline', updated_at=now())
        stages = state.setdefault('stages', {})
        for stage in ('storyboard', 'prompt'):
            stages.pop(stage, None)
        stages['outline'] = {'status': 'done'}
        write_json(project / 'state.json', state)
    return value


@app.post('/api/projects/{pid}/stage/{stage}', status_code=202)
def run_stage(pid: str, stage: str, body: StageRequest):
    body = body.model_dump(exclude_unset=True, exclude_none=True)
    if stage not in ('outline', 'storyboard', 'prompt', 'plan', 'render', 'all'):
        raise ValueError('未知阶段。')
    if body.get('limit') is not None and (type(body['limit']) is not int or not 1 <= body['limit'] <= 150 or stage not in ('all','render')):
        raise ValueError('试跑数量须为 1～150 个待生成镜头，仅用于视频生成。')
    return {'job_id': worker.enqueue(pid, stage, body)}


@app.get('/api/projects/{pid}/preflight')
def preflight(pid: str):
    from .workflow_checks import workflow_report
    project = projects.path(pid)
    story = projects.get(pid)['story']
    return workflow_report(story, projects.options(project), config.renderer_config(),
        lambda shot, value: assets.resolve(project, shot, value, inspect_media=True), content.mode
    ) if story else {'ready': False, 'issues': [], 'shots': [], 'message': '请先生成分镜。'}


@app.get('/api/projects/{pid}/quality')
def quality(pid: str):
    from .finishing import versions, readiness
    project=projects.path(pid)
    return {'preflight':preflight(pid),'report':read_json(project/'媒体验收.json'),
            'finishing':readiness(project,projects.get(pid)['story']),
            'versions':versions(project),'current_edit':read_json(project/'current_edit.json') if (project/'成片.mp4').is_file() else None}


@app.post('/api/projects/{pid}/finishing-settings')
def save_finishing_settings(pid: str, body: dict):
    from .finishing_settings import validate_settings
    projects.assert_idle(pid)
    project = projects.path(pid)
    value = validate_settings(body, projects.get(pid)['story'])
    write_json(project / 'finishing-settings.json', value)
    return value


@app.post('/api/projects/{pid}/finish',status_code=202)
def finish(pid: str,body:dict):
    from .finishing_settings import validate_settings
    from .finishing import collect_clips
    projects.assert_idle(pid)
    project=projects.path(pid);story=projects.get(pid)['story']
    value=validate_settings(body,story)
    collect_clips(project,story)
    return {'job_id':worker.enqueue(pid,'finish',value)}


@app.post('/api/projects/{pid}/edits/{edit_id}/rebuild',status_code=202)
def rebuild(pid:str,edit_id:str):
    from .finishing import load_recipe
    projects.assert_idle(pid)
    load_recipe(projects.path(pid),edit_id)
    return {'job_id':worker.enqueue(pid,'rebuild-edit',{'edit_id':edit_id})}


@app.post('/api/projects/{pid}/shots/{uid}/template')
def template_save(pid:str,uid:str,body:dict):
    from .templates import save_template
    projects.assert_idle(pid)
    story=projects.get(pid)['story'];shot=next((s for s in (story or {}).get('shots',[]) if s['uid']==uid),None)
    if not shot:raise ValueError('镜头不存在。')
    name=body.get('name','')
    if not isinstance(name,str) or len(name)>200:raise ValueError('样板名称最多 200 字。')
    return save_template(projects.path(pid),story,shot,name)


@app.post('/api/resume', status_code=202)
def resume(body: dict):
    return {'id': body['id'], 'job_id': worker.enqueue(body['id'], 'all')}


@app.post('/api/projects/{pid}/shots/{uid}/regenerate', status_code=202)
def regenerate_shot(pid: str, uid: str, body: dict):
    import secrets
    projects.assert_idle(pid)
    story = projects.get(pid)['story']
    shot = next((s for s in (story or {}).get('shots',[]) if s['uid'] == uid), None)
    if not shot:
        raise ValueError('镜头不存在。')
    if shot['locked']:
        raise ValueError('请先解锁此镜头，再重新生成。')
    kind = body.get('kind', 'video')
    if kind == 'prompt':
        return {'job_id': worker.enqueue(pid, 'prompt', {'force': True, 'uids': [uid]})}
    if kind != 'video':
        raise ValueError('选择提示词或视频重生成。')
    shot['seed'] = secrets.randbelow(2**63)
    projects.save_story(pid, story)
    return {'job_id': worker.enqueue(pid, 'render'), 'seed': shot['seed']}


@app.post('/api/stop')
def stop(body: dict):
    worker.stop(body['id'])
    if worker.active and worker.active['project_id'] == body['id'] and worker.active.get('kind') in ('finish', 'rebuild-edit'):
        return {'message': '已请求停止后期，当前处理进程将终止，原片和已有成片版本会保留。'}
    if body.get('immediate'):
        return {'message': '已请求立即停止，仅中断确认属于本项目的生成任务。', **worker.interrupt_owned(body['id'])}
    return {'message': '将停止文字阶段，或在当前镜头完成后停止。成果会保留。'}


@app.post('/api/projects/{pid}/assets')
def add_asset(pid: str, body: dict):
    if body.get('type') in ('video', 'audio'):
        return assets.add_media(pid, body['data'], body['type'], body.get('name', ''))
    return assets.add_image(pid, body['data'], body.get('name', ''), body.get('character', ''))


@app.get('/api/jobs')
def jobs():
    return db.jobs()


@app.get('/api/jobs/page')
def jobs_page(limit: int = Query(100, ge=1, le=200), before: int | None = Query(None, ge=1),
              project_id: str | None = None, status: str | None = None):
    page = db.jobs_page(limit=limit, before=before, project_id=project_id, status=status)
    return {**page, 'items': [job_view(row) for row in page['items']]}


@app.get('/api/jobs/{jid}', response_model=JobView)
def job_get(jid: str):
    row = db.job(jid)
    if row is None:
        raise ContractError('JOB_NOT_FOUND', '任务不存在；不要据此重复提交生成。', status=404,
                            next_actions=['inspect_request_receipt'])
    return job_view(row)


@app.get('/api/jobs/{jid}/events')
def job_events(jid: str, after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200)):
    job_get(jid)
    result = db.job_events(jid, after=after, limit=limit)
    allowed = {'message', 'status', 'current_stage', 'current_shot', 'total_shots', 'progress',
               'file', 'bytes', 'total', 'phase', 'frames', 'seconds', 'kind'}
    for item in result['items']:
        item['data'] = {key: safe_message(value) if isinstance(value, str) else value
                        for key, value in item['data'].items() if key in allowed and not isinstance(value, (dict, list))}
    return result


@app.get('/api/images/environment')
def image_environment(variant: str = 'auto', image_model: str = 'qwen-image-2.1'):
    ImageSettings(variant=variant, image_model=image_model)
    return worker.images.environment.plan(variant, image_model=image_model)


@app.get('/api/images/models')
def image_model_catalog():
    from .image_models import model_catalog
    return {'models': {'qwen-image-2.1': {'name': 'Qwen-Image 2.1 · 多图参考与编辑',
             'architecture': 'qwen_image_21', 'sampling': {'steps': None, 'cfg': 1, 'sampler': 'euler', 'scheduler': 'auto'},
             'reference_modes': ['reference', 'edit'], 'max_reference_images': 10, 'transparent_support': True},
             **{key: {**value, 'max_reference_images': 1, 'transparent_support': False} for key,value in model_catalog().items()}}}


@app.get('/api/images/environment/progress')
def image_environment_progress():
    return read_json(config.root / 'data/image-environment-progress.json', {})


@app.post('/api/images/environment/plan')
def image_environment_plan(body: dict):
    ImageSettings(variant=body.get('variant', 'auto'), image_model=body.get('image_model', 'qwen-image-2.1'))
    return worker.images.environment.plan(body.get('variant', 'auto'), body.get('models'), body.get('image_model'))


@app.post('/api/images/settings')
def image_settings(body: dict):
    if worker.active:
        raise ValueError('请等待当前任务完成或停止后，再修改图片引擎设置。')
    settings = ImageSettings.model_validate(body)
    config.provider(settings.provider)
    value = config.get()
    value['image_generation'] = settings.model_dump()
    return config.save(value)['image_generation']


@app.post('/api/images/environment/prepare', status_code=202)
def image_prepare(body: dict):
    variant = body.get('variant', 'auto')
    image_model = body.get('image_model', 'qwen-image-2.1')
    ImageSettings(variant=variant, image_model=image_model)
    models = ImageModels.model_validate(body['models']).model_dump() if body.get('models') is not None else None
    jid = worker.enqueue('__image_environment', 'image-prepare', {'variant': variant, 'models': models, 'image_model': image_model,
                         'download_confirmation': body.get('download_confirmation', '')})
    # Worker owns subsequent progress; avoid replacing a running/done state after enqueue.
    return {'job_id': jid}


@app.post('/api/images/environment/stop')
def image_prepare_stop():
    worker.stop('__image_environment')
    path = config.root / 'data/image-environment-progress.json'
    write_json(path, {**read_json(path, {}), 'status': 'paused', 'message': '已请求停止图片环境准备，已下载的数据可继续使用。'})
    return {'message': '已请求停止图片环境准备，已下载的数据可继续使用。'}


@app.post('/api/image-inputs', status_code=201)
def image_input_upload(body: dict):
    return worker.images.inputs.upload(body.get('data'), body.get('name', ''))


@app.get('/api/image-inputs/{rid}')
def image_input_get(rid: str):
    return worker.images.inputs.get(rid)


@app.get('/api/image-inputs/{rid}/file')
def image_input_file(rid: str):
    return FileResponse(worker.images.inputs.file(rid), media_type='image/png')


@app.post('/api/images/{iid}/use-as-reference', status_code=201)
def image_use_as_reference(iid: str):
    value = worker.images.get(iid)
    if not value['file_available']:
        raise ValueError('请先生成图片，再用作参考图。')
    return worker.images.inputs.add(contained(worker.images.path(iid), value['file']).read_bytes(), value['request']['prompt'][:100])


@app.get('/api/images/{iid}/references/{index}')
def image_reference_snapshot(iid: str, index: int):
    references = worker.images.get(iid).get('reference_inputs', [])
    if not 1 <= index <= len(references):
        raise ValueError('任务参考图不存在。')
    return FileResponse(contained(worker.images.path(iid), references[index - 1]['file']), media_type='image/png')


@app.get('/api/images')
def images_list():
    return worker.images.listing()


@app.post('/api/images', status_code=202)
def image_create(body: dict):
    image = worker.images.create(body.get('request', {}), confirmation=body.get('download_confirmation', ''))
    kind = 'image-optimize' if body.get('optimize_only') else 'image-generate'
    jid = worker.enqueue(image['owner'], kind, {'image_id': image['id']})
    worker.images.update(image['id'], job_id=jid)
    return {'id': image['id'], 'job_id': jid}


@app.get('/api/images/{iid}')
def image_get(iid: str):
    return worker.images.get(iid)


@app.get('/api/images/{iid}/file')
def image_file(iid: str):
    value = worker.images.get(iid)
    if not value.get('file'):
        raise ValueError('图片尚未生成。')
    path = contained(worker.images.path(iid), value['file'])
    if not path.is_file() or path.suffix.lower() != '.png':
        raise ValueError('图片文件不存在。')
    return FileResponse(path, media_type='image/png', filename=iid + '.png', content_disposition_type='inline')


@app.post('/api/images/{iid}/resume', status_code=202)
def image_resume(iid: str, body: dict | None = None):
    image_assert_idle(iid)
    result = worker.images.start(iid, worker.enqueue, confirmation=(body or {}).get('download_confirmation'))
    worker.wake.set()
    return result


@app.post('/api/images/{iid}/generate', status_code=202)
def image_generate_existing(iid: str, body: dict):
    image_assert_idle(iid)
    result = worker.images.start(iid, worker.enqueue, request=body.get('request'),
                                 optimize_only=bool(body.get('optimize_only')), confirmation=body.get('download_confirmation'))
    worker.wake.set()
    return result


@app.post('/api/images/{iid}/delete')
def image_delete(iid: str):
    image_assert_idle(iid)
    return worker.images.delete(iid)


def image_assert_idle(iid):
    value = worker.images.get(iid)
    if worker.active and worker.active['project_id'] == value['owner']:
        raise ValueError('原任务正在完成收尾，请稍后重试。')


@app.post('/api/images/{iid}/regenerate', status_code=202)
def image_regenerate(iid: str, body: dict):
    previous = worker.images.get(iid)
    if previous['project_id']:
        projects.assert_idle(previous['project_id'])
        if previous['target']:
            worker.images.reference_request(previous['project_id'], previous['target'])
    request = ImageRequest.model_validate(previous['request']).model_dump()
    request.update(seed=None, optimized_prompt=request['optimized_prompt'] or previous.get('optimized_prompt', ''))
    changes = body.get('request', {})
    if changes.get('optimize') is False or any(key in changes and changes[key] != request.get(key) for key in ('prompt', 'purpose', 'style', 'ratio', 'transparent', 'reference_images', 'reference_mode', 'image_model')):
        request['optimized_prompt'] = ''
    request.update(changes)
    image = worker.images.create(request, previous['project_id'], previous['target'], parent_id=iid,
                                  confirmation=body.get('download_confirmation', ''))
    jid = worker.enqueue(image['owner'], 'image-generate', {'image_id': image['id']})
    worker.images.update(image['id'], job_id=jid)
    return {'id': image['id'], 'job_id': jid}


@app.post('/api/images/{iid}/stop')
def image_stop(iid: str):
    image = worker.images.get(iid)
    if image['busy']:
        worker.stop(image['owner'])
    worker.images.interrupt(iid)
    if image.get('status') != 'complete':
        worker.images.update(iid, status='paused', message='已请求停止图片任务，已有结果保留。')
    return {'message': '已请求停止图片任务，已有图片保留。'}


@app.get('/api/projects/{pid}/image-references')
def image_references(pid: str):
    return {'candidates': worker.images.candidates(pid), 'images': worker.images.listing(pid)}


@app.post('/api/projects/{pid}/image-references/generate', status_code=202)
def image_reference_generate(pid: str, body: dict):
    projects.assert_idle(pid)
    candidates = worker.images.candidates(pid)
    targets = body.get('targets')
    if targets is not None and (not isinstance(targets, list) or not targets or
                               any(not isinstance(t, str) or t not in {c['key'] for c in candidates} for t in targets)):
        raise ValueError('请选择当前项目中的角色、场景或道具。')
    if not candidates:
        raise ValueError('请先生成分镜和角色设定，再生成参考图。')
    return {'job_id': worker.enqueue(pid, 'image-references', {'targets': targets, 'download_confirmation': body.get('download_confirmation', '')})}


@app.post('/api/projects/{pid}/image-references/{target}/generate', status_code=202)
def image_reference_one(pid: str, target: str, body: dict):
    projects.assert_idle(pid)
    request = worker.images.reference_request(pid, target, body.get('request'))
    image = worker.images.create(request, pid, target, confirmation=body.get('download_confirmation', ''))
    jid = worker.enqueue(pid, 'image-generate', {'image_id': image['id']})
    worker.images.update(image['id'], job_id=jid)
    return {'id': image['id'], 'job_id': jid}


@app.post('/api/projects/{pid}/image-references/{target}/sources')
def image_reference_sources(pid: str, target: str, body: dict):
    return worker.images.set_reference_sources(pid, target, body)


@app.post('/api/projects/{pid}/image-references/{target}/adopt')
def image_reference_adopt(pid: str, target: str, body: dict):
    return worker.images.adopt(pid, target, body['image_id'])


@app.get('/api/health')
def health():
    try:
        headers = {'Authorization': 'Bearer ' + config.key('comfy')} if config.key('comfy') else {}
        response = httpx.get(config.renderer_config()['comfy_url'] + '/system_stats', headers=headers, timeout=2)
        healthy = response.is_success
    except (httpx.HTTPError, KeyError):
        healthy = False
    return {'comfy': healthy, 'active_project': worker.active['project_id'] if worker.active else None,
            'version': app.version, 'application_root': str(ROOT), 'protocol_version': PROTOCOL_VERSION}


@app.get('/api/capabilities')
def capabilities():
    return {'protocol_version': PROTOCOL_VERSION, 'application_version': VERSION,
            'features': {'exact_jobs': True, 'job_events': True, 'structured_errors': True,
                         'execution_plans': False, 'idempotency': False, 'revisioned_edits': False},
            'video': video_workflow_catalog(), 'images': image_model_catalog(),
            'schemas': '/openapi.json',
            'effects': {'/api/environment/verify': ['creates_project', 'gpu_render'],
                        '/api/projects': ['creates_project', 'starts_unless_start_false'],
                        '/api/projects/{id}/stage/render': ['may_call_text_provider', 'gpu_render']}}


@app.get('/api/doctor')
def doctor():
    """Read-only probes; never starts engines, downloads, or calls a text model."""
    status = health()
    checks = [{'code': 'API_CONNECTED', 'status': 'passed', 'message': '生产服务可访问。'}]
    if not status['comfy']:
        checks.append({'code': 'ENGINE_UNAVAILABLE', 'status': 'blocked',
                       'message': '视频引擎不可访问；可以继续编辑分镜，生成前需准备引擎。',
                       'next_actions': ['inspect_environment', 'prepare_environment']})
    else:
        try:
            info = environment_catalog()
            missing = info.get('missing_nodes', []) + info.get('configured_missing', [])
            checks.append({'code': 'VIDEO_ENVIRONMENT', 'status': 'blocked' if missing or info.get('cache_protocol', 0) < 2 else 'passed',
                           'missing': missing, 'cache_protocol': info.get('cache_protocol'),
                           'message': '检查视频节点、已配置模型与缓存协议。'})
        except (ValueError, RuntimeError) as exc:
            checks.append({'code': 'ENVIRONMENT_UNKNOWN', 'status': 'unknown', 'message': safe_message(exc)})
    providers = [{'id': p['id'], 'local': p.get('local', False), 'key_configured': p.get('key_configured', False)}
                 for p in config.public()['providers']]
    return {'protocol_version': PROTOCOL_VERSION, 'instance': status, 'read_only': True,
            'ready': all(c['status'] == 'passed' for c in checks), 'checks': checks,
            'providers': providers, 'limits': ['不执行推理；图片模型与特定工作流还需对应环境计划检查。']}


@app.get('/api/environment/catalog')
def environment_catalog():
    return catalog({**config.renderer_config(), 'comfy_auth_token': config.key('comfy')})


@app.get('/api/video/workflows/plan')
def video_workflow_plan(profile: str):
    return worker.video_environment.plan(profile)


@app.get('/api/video/workflows')
def video_workflow_catalog():
    from .video_workflows import workflow_catalog
    return {'workflows': workflow_catalog(), 'profiles': config.renderer_config()['profiles']}


@app.get('/api/video/workflows/progress')
def video_workflow_progress(job_id: str = ''):
    import json
    with db.connect() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE project_id='__video_environment' " +
            ("AND id=? " if job_id else "") + "ORDER BY rowid DESC LIMIT 1",
            (job_id,) if job_id else ()).fetchone()
    if not row:
        return {'status': 'idle', 'message': '尚未准备视频工作流。'}
    state = read_json(config.root/'data/video-environment-progress.json', {})
    if state.get('job_id') != row['id']:
        state = {}
    message = row['message'] or ('正在排队，等待当前任务完成。' if row['status'] == 'queued' else
                               '准备已暂停，可重新检查后继续。' if row['status'] == 'paused' else '正在准备工作流。')
    return {**state, 'job_id': row['id'], 'profile': json.loads(row['payload']).get('profile'),
            'status': row['status'], 'message': message, 'cancel_requested': bool(row['cancel_requested'])}


@app.post('/api/video/workflows/prepare', status_code=202)
def video_workflow_prepare(body: dict):
    profile = str(body.get('profile', ''))
    plan = worker.video_environment.plan(profile)
    if plan.get('requires_confirmation') and body.get('download_confirmation') != plan['confirmation_token']:
        raise ValueError('工作流资源发生变化，请重新检查并确认下载。')
    return {'job_id': worker.enqueue('__video_environment', 'video-prepare',
            {'profile':profile,'download_confirmation':body.get('download_confirmation','')})}


@app.post('/api/video/workflows/stop')
def video_workflow_stop():
    worker.stop('__video_environment')
    return {'ok':True}


@app.post('/api/video/workflows/profiles', status_code=201)
def video_workflow_profile(body: dict):
    if worker.active:
        raise ValueError('请等待当前任务完成后再保存视频工作流方案。')
    import uuid
    from .schemas import Quality
    profiles = config.renderer_config()['profiles']
    base = profiles.get(str(body.get('base_profile', '')))
    if not base:raise ValueError('原视频工作流不存在。')
    changes = body.get('changes', {})
    allowed = {'megapixels','steps','lora_strength','head_strength','upscale_by','refine_denoise',
        'source_start_seconds','guide_position','context_frames','audio_context_frames',
        'control_strength','control_start','control_end','canny_low','canny_high'}
    if not isinstance(changes,dict) or set(changes)-allowed:raise ValueError('工作流参数不支持。')
    quality=Quality.model_validate({**base,**changes,'label':str(body.get('label','')).strip()}).model_dump()
    name='custom-'+uuid.uuid4().hex[:12]
    value=config.get();value['environment']['profiles']={**profiles,name:quality};config.save(value)
    return {'id':name,'profile':quality}


@app.get('/api/environment')
def environment_get():
    return {'hardware': hardware(), 'manifests': worker.installer.manifests(),
            'installation': read_json(ROOT / 'data/installation.json'),
            'progress': read_json(ROOT / 'data/installation_progress.json'), 'hf_token_configured': bool(config.key('hf'))}


@app.get('/api/environment/progress')
def environment_progress():
    return read_json(ROOT / 'data/installation_progress.json', {})


@app.post('/api/environment/plan')
def installation_plan(body: dict):
    return worker.installer.plan(body)


@app.post('/api/environment/install', status_code=202)
def installation_begin(body: dict):
    return {'job_id': worker.enqueue('__environment', 'install', body)}


@app.post('/api/environment/stop')
def installation_stop():
    db.cancel('__environment')
    return {'message': '下载会在下一个数据块停止，安装进度会保留。'}


@app.post('/api/environment/verify', status_code=202)
def environment_verify():
    if worker.active:
        raise ValueError('请等待或停止当前任务后运行环境验证。')
    profiles = config.renderer_config().get('profiles', {})
    profile = 'draft' if 'draft' in profiles else next(iter(profiles))
    options = Options(input_mode='storyboard', execution_mode='auto', duration_rule='count',
                      total_seconds=4, shot_count=1, profile=profile, auto_reference=False).model_dump()
    story = {'title': '环境验证：清晨的红伞', 'characters': [], 'shots': [{
        'id': 1, 'duration': 4, 'mode': 'T2VA', 'characters': [], 'dialogue': [],
        'prompt': 'integrated_multimodal_description:\n[Shot 1] 0.0-4.46s. A red umbrella rests beside a wooden chair in a quiet anime room. Soft morning light enters the window. Static medium shot, gentle curtain movement, no people, no text or watermark.\noverall_soundscape:\nSoft rain outside, quiet room tone. No dialogue.\nnon_diegetic_music:\nN/A'}]}
    project = projects.create('验证本机 H3 条件编码、采样、音画解码与合片。此项目不请求文字模型。', options, story)
    return {'id': project.name, 'job_id': worker.enqueue(project.name, 'render')}


@app.get('/api/projects/{pid}/records')
def project_records(pid: str):
    project = projects.path(pid)
    records = []
    for path in sorted((project / 'requests').glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:300]:
        value = read_json(path, {})
        records.append({'file': path.name, 'stage': value.get('stage', path.name.split('_')[0]),
                        'snapshot': value.get('snapshot'), 'response_usage': value.get('response', {}).get('usage')})
    return {'requests': records, 'renderer': read_json(project / 'renderer_snapshot.json'),
            'media': read_json(project / '媒体验收.json')}


@app.get('/api/projects/{pid}/requests/{name}')
def project_request(pid: str, name: str):
    project = projects.path(pid)
    path = contained(project / 'requests', name)
    if path.parent != project / 'requests' or path.suffix != '.json' or not path.is_file():
        raise ValueError('请求记录不存在。')
    return read_json(path)


@app.post('/api/export')
def export_package(body: dict):
    path = transfer.export(body.get('projects', []), bool(body.get('include_videos')))
    return {'url': '/api/exports/' + path.name, 'size': path.stat().st_size}


@app.get('/api/exports/{name}')
def exported_file(name: str):
    path = contained(ROOT / 'data/exports', name)
    if path.suffix != '.zip' or not path.is_file():
        raise ValueError('导出文件不存在。')
    return FileResponse(path, filename=path.name)


@app.post('/api/import')
def import_package(file: UploadFile = File(...)):
    if worker.active:
        raise ValueError('请完成或停止当前任务后导入。')
    return transfer.import_package(file.file)


@app.get('/media/{pid}/{relative:path}')
def media(pid: str, relative: str):
    project = projects.path(pid)
    path = contained(project, relative)
    allowed = path.suffix.lower() in ('.mp4', '.webm', '.mov', '.png', '.jpg', '.jpeg', '.webp', '.wav', '.mp3', '.flac', '.m4a', '.ogg', '.srt', '.ass', '.txt')
    allowed = allowed or path.name in ('分镜.json', 'outline.json')
    if not path.is_file() or not allowed or any(p.startswith('.') for p in Path(relative).parts):
        raise ValueError('文件不可访问。')
    return FileResponse(path)


if (ROOT / 'web').is_dir():
    app.mount('/web', StaticFiles(directory=ROOT / 'web'), name='web')
