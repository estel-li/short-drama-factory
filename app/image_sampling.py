"""Resolve model defaults and validate against the selected ComfyUI, without loading weights."""
from .image_models import QWEN_UD_MODEL, is_qwen_model, model_spec


def sampling_for_plan(request, plan):
    if not is_qwen_model(plan.get('image_model', 'qwen-image-2.1')):
        from .image_models import model_spec, model_sampling
        return model_sampling(request, model_spec(plan['image_model']))
    return resolve_sampling(request, plan['variant'])


def resolve_sampling(request, variant):
    sampling = request.sampling.model_dump()
    turbo = variant.startswith('turbo')
    ud = request.image_model == QWEN_UD_MODEL
    if ud and turbo:
        raise ValueError('Qwen2.1 UD版使用标准采样，不支持 Turbo 方案。')
    sampling['steps'] = sampling['steps'] or (model_spec(QWEN_UD_MODEL)['sampling']['steps'] if ud else 8 if turbo else 40)
    official = turbo and sampling['steps'] == 8 and sampling['scheduler'] == 'auto' and sampling['denoise'] == 1
    sampling['scheduler'] = 'official_turbo' if official else ('simple' if sampling['scheduler'] == 'auto' else sampling['scheduler'])
    sampling['initial_latent'] = 'source_image' if sampling['denoise'] < 1 else 'empty'
    return sampling


def validate_sampling_support(sampling, plan):
    # Older task snapshots and third-party probes may not carry capabilities.
    support = plan.get('sampling_support')
    if support is None:
        return
    if sampling['sampler'] not in support['samplers']:
        raise ValueError('目标 ComfyUI 不支持所选采样器，请换一个采样器或升级图片引擎。')
    if sampling['scheduler'] != 'official_turbo' and sampling['scheduler'] not in support['schedulers']:
        raise ValueError('目标 ComfyUI 不支持所选调度器，请换一个调度器或升级图片引擎。')
    required = set()
    if plan['variant'].startswith('turbo'):
        if sampling['scheduler'] != 'official_turbo':
            required.add('BasicScheduler')
        if sampling['cfg'] != 1:
            required.add('CFGGuider')
    if sampling['denoise'] < 1:
        required.update(('VAEEncode', 'ImageScale'))
    if required - set(support['nodes']):
        raise ValueError('目标 ComfyUI 缺少高级采样节点，请升级图片引擎或恢复模型推荐参数。')
