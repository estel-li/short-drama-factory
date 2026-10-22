"""Typed, durable image and asset operations for external AI clients."""
from typing import Literal

from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict, Field

from .contracts import ContractError
from .image_schemas import ImageRequest
from .project_locks import project_lock


class AgentImageRequest(ImageRequest):
    optimize: bool = False


class AgentImageCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request: AgentImageRequest
    internal_text: Literal['forbid', 'allowed'] = 'forbid'
    optimize_only: bool = False


class ImageInputUpload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(default='', max_length=200)
    data: str = Field(min_length=1, max_length=11_000_000)


class AssetUpload(ImageInputUpload):
    type: Literal['image', 'video', 'audio'] = 'image'
    character: str = Field(default='', max_length=80, pattern=r'^[a-zA-Z0-9_-]{0,80}$')


def install_media_routes(app, services):
    router = APIRouter(prefix='/api/v2')

    def recover_dispatch(s, result):
        iid, jid = result['image_id'], result['job_id']
        value = s.worker.images.get(iid)
        if value.get('operation_id') != result['operation_id']:
            raise ContractError('IMAGE_RESERVATION_CONFLICT', '图片记录与原请求回执不匹配。', status=409)
        if value.get('job_id') != jid:
            if value.get('job_id'):
                raise ContractError('IMAGE_JOB_CONFLICT', '图片记录已经关联其他任务，请检查原请求。', status=409)
            s.worker.images.update(iid, job_id=jid)
        job = s.db.job(jid)
        if job is None:
            raise ContractError('JOB_NOT_FOUND', '原图片任务记录缺失。', status=404)
        if job['status'] == 'queued':
            s.worker.start(recover=False)
            s.worker.allow_job(jid)

    @router.post('/images', status_code=202)
    def create_image(body: AgentImageCreate, idempotency_key: str = Header(...)):
        s = services()
        payload = body.model_dump()
        # Omitted model/sampling values mean "use configured/model defaults";
        # they are not equivalent to explicitly supplied Qwen schema defaults.
        raw = body.request.model_dump(exclude_unset=True)
        raw.setdefault('optimize', False)
        payload['request'] = raw.copy()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, 'image.create', payload)
            if receipt['status'] == 'completed':
                result = receipt['result']
            else:
                if (body.request.optimize or body.optimize_only) and body.internal_text == 'forbid' and not body.request.optimized_prompt:
                    raise ContractError('TEXT_GENERATION_FORBIDDEN', '图片优化需要明确允许内部文字调用，或提供已完成的 optimized_prompt。',
                                        status=409, next_actions=['supply_external_prompt', 'allow_internal_text'])
                # Preserve model-specific and configured defaults. Expanding the
                # request schema would overwrite SDXL/FLUX presets with Qwen's
                # sampling defaults even when the caller did not choose them.
                if body.optimize_only:
                    raw['optimize'] = True
                iid = receipt['operation_id'][:24]
                value = s.worker.images.create(raw, reserved_id=iid, operation_id=receipt['operation_id'])
                kind = 'image-optimize' if body.optimize_only else 'image-generate'
                result = s.db.enqueue_operation(idempotency_key, 'image.create', payload, value['owner'], kind,
                                                {'image_id': iid, 'internal_text': body.internal_text, 'allow_downloads': False},
                                                result_fields={'id': iid, 'image_id': iid, 'owner': value['owner']})
            recover_dispatch(s, result)
            return result

    @router.post('/image-inputs', status_code=201)
    def upload_image_input(body: ImageInputUpload, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key):
            receipt = s.db.reserve_operation(idempotency_key, 'image_input.upload', body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            value = s.worker.images.inputs.upload(body.data, body.name)
            result = {**value, 'operation_id': receipt['operation_id'], 'request_key': idempotency_key}
            s.db.complete_operation(idempotency_key, result)
            return result

    @router.post('/projects/{pid}/assets', status_code=201)
    def upload_asset(pid: str, body: AssetUpload, idempotency_key: str = Header(...)):
        s = services()
        with project_lock(s.db, 'operation:' + idempotency_key), project_lock(s.db, pid):
            receipt = s.db.reserve_operation(idempotency_key, 'asset.upload:' + pid, body.model_dump())
            if receipt['status'] == 'completed':
                return receipt['result']
            if body.type != 'image' and body.character:
                raise ContractError('INVALID_ASSET_CHARACTER', '角色外观标识仅用于图片素材。', status=422)
            reserved = {'asset_id': receipt['operation_id'][:20], 'operation_id': receipt['operation_id']}
            if body.type == 'image':
                value = s.assets.add_image(pid, body.data, body.name, body.character, **reserved)
            else:
                value = s.assets.add_media(pid, body.data, body.type, body.name, **reserved)
            result = {**value, 'project_id': pid, 'revision': s.projects.revision(pid), 'request_key': idempotency_key}
            s.db.complete_operation(idempotency_key, result)
            return result

    app.include_router(router)
