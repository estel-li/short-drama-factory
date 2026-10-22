"""Explicit setup operations used by the headless CLI."""
from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict, Field

from .agent_api import deep_merge
from .contracts import ContractError
from .project_locks import project_lock
from .storage import digest, read_json


class ConfigurationPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: str = Field(min_length=1)
    changes: dict


class SpeechPrepare(BaseModel):
    model_config = ConfigDict(extra='forbid')
    download_confirmation: str = ''


def config_revision(config):
    return digest({k: v for k, v in config.get().items() if k != '_agent_receipts'})


def speech_plan():
    from . import speech
    from .downloads import Downloader
    model = read_json(speech.ROOT / 'manifests/quality.json')['model']
    target = speech.ROOT / 'data/quality' / model['filename']
    ready = target.is_file() and target.stat().st_size == model['size'] and Downloader.checksum(target) == model['sha256']
    specification = {'name': model['filename'], 'size': model['size'], 'sha256': model['sha256'], 'target': str(target)}
    return {'ready': ready, 'model': specification, 'download_bytes': 0 if ready else model['size'],
            'requires_confirmation': not ready, 'confirmation_token': digest(specification),
            'effects': ['download_model'] if not ready else []}


def install_environment_routes(app, services):
    router = APIRouter(prefix='/api/v2')

    @router.get('/config')
    def get_config():
        config = services().config
        return {'revision': config_revision(config),
                'config': {k: v for k, v in config.public().items() if k != '_agent_receipts'}}

    @router.patch('/config')
    def patch_config(body: ConfigurationPatch, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key), s.config.lock:
            receipt = s.db.reserve_operation(idempotency_key, 'config.patch', body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            recovered = s.config.get().get('_agent_receipts', {}).get(idempotency_key)
            if recovered and recovered['request_hash'] == receipt['request_hash']:
                s.db.complete_operation(idempotency_key, recovered['result'])
                return recovered['result']
            if config_revision(s.config) != body.expected_revision:
                raise ContractError('REVISION_CONFLICT', '配置已改变，请重新读取后合并。', status=409)
            with s.db.connect() as connection:
                if connection.execute("SELECT id FROM jobs WHERE status IN ('queued','running') LIMIT 1").fetchone():
                    raise ContractError('QUEUE_BUSY', '请等待队列空闲后修改全局配置。', status=409)
            allowed = {'projects_dir', 'environment', 'providers', 'proxy', 'setup_complete', 'image_generation'}
            if set(body.changes) - allowed:
                raise ContractError('INVALID_CONFIG_PATCH', '只修改公开配置字段；凭证使用专用设置入口。')
            value = deep_merge(s.config.get(), body.changes)
            s.config.save(value, operation=receipt)
            result = s.config.get()['_agent_receipts'][idempotency_key]['result']
            s.projects.refresh()
            s.db.complete_operation(idempotency_key, result)
            return result

    @router.get('/environment/speech/plan')
    def get_speech_plan():
        return speech_plan()

    @router.post('/environment/speech/prepare', status_code=202)
    def prepare_speech(body: SpeechPrepare, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, 'speech.prepare', body.model_dump())
            if receipt['status'] == 'completed':
                result = receipt['result']
            else:
                plan = speech_plan()
                if not plan['ready'] and body.download_confirmation != plan['confirmation_token']:
                    raise ContractError('DOWNLOAD_CONFIRMATION_REQUIRED', '请先检查语音检测模型下载计划并确认。', status=409,
                                        next_actions=['inspect_speech_plan', 'confirm_download'])
                result = s.db.enqueue_operation(idempotency_key, 'speech.prepare', body.model_dump(), '__environment',
                    'speech-prepare', {'allow_downloads': True, 'internal_text': 'forbid',
                                       'download_confirmation': plan['confirmation_token']})
            if (s.db.job(result['job_id']) or {}).get('status') == 'queued':
                s.worker.start(recover=False)
                s.worker.allow_job(result['job_id'])
            return result

    app.include_router(router)
