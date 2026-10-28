"""Model-specific native ComfyUI graphs; no inference imports in the workbench."""
from __future__ import annotations

from .storage import ROOT, read_json

QWEN_MODEL = 'qwen-image-2.1'
QWEN_UD_MODEL = 'qwen-image-2.1-ud'


def is_qwen_model(model_id):
    return model_id in (QWEN_MODEL, QWEN_UD_MODEL)


def qwen_manifest(model_id):
    if not is_qwen_model(model_id):
        raise ValueError('不是受支持的 Qwen 生图模型。')
    base = read_json(ROOT / 'manifests/qwen-image-2.1.json')
    return {**base, **read_json(ROOT / 'manifests/qwen-image-2.1-ud.json')} if model_id == QWEN_UD_MODEL else base


def qwen_catalog():
    result = {}
    for model_id in (QWEN_MODEL, QWEN_UD_MODEL):
        manifest = qwen_manifest(model_id)
        result[model_id] = {
            'name': manifest['name'] if model_id == QWEN_UD_MODEL else 'Qwen-Image 2.1 · 多图参考与编辑',
            'architecture': 'qwen_image_21', 'source': manifest['source'],
            'sampling': manifest.get('sampling', {'steps': None, 'cfg': 1, 'sampler': 'euler', 'scheduler': 'auto'}),
            'reference_modes': ['reference', 'edit'], 'max_reference_images': 10, 'transparent_support': True,
            'variants': manifest['variants'], 'auto_prepare_on_select': model_id == QWEN_UD_MODEL,
        }
    return result


def model_catalog():
    return read_json(ROOT / 'manifests/image-models.json')['models']


def model_spec(model_id):
    if is_qwen_model(model_id):
        return qwen_catalog()[model_id]
    try:
        return model_catalog()[model_id]
    except KeyError:
        raise ValueError('生图模型不存在，请从模型列表重新选择。') from None


def model_sampling(request, spec):
    result = request.sampling.model_dump()
    result['steps'] = result['steps'] or spec['sampling']['steps']
    if result['scheduler'] == 'auto':
        result['scheduler'] = spec['sampling']['scheduler']
    result['initial_latent'] = 'source_image' if request.reference_images else 'empty'
    return result


def validate_model_inputs(request, spec):
    if request.transparent:
        raise ValueError('当前模型不输出原生透明通道，请使用 Qwen-Image 2.1，或关闭透明背景。')
    if request.reference_images:
        if request.reference_mode not in spec['reference_modes']:
            raise ValueError('当前模型支持单张图生图重绘，请选择“编辑原图”；多图语义参考请使用 Qwen-Image 2.1。')
        if len(request.reference_images) != 1:
            raise ValueError('当前模型仅支持一张原图，请移除多余参考图，或使用 Qwen-Image 2.1。')


def library_image_graph(request, prompt, plan, prefix, references=None):
    """Build checkpoint/FLUX/Z-Image graphs without mixing Qwen-only encoders."""
    from .image_environment import image_size
    spec = model_spec(plan['image_model'])
    validate_model_inputs(request, spec)
    sampling = model_sampling(request, spec)
    from .image_sampling import validate_sampling_support
    validate_sampling_support(sampling, plan)
    files = {m['role']: m.get('comfy_name') or m['name'] for m in plan['models']}
    resolution = spec['resolution'] if request.resolution == 'auto' else int(request.resolution)
    width, height = image_size(request.ratio, resolution)
    graph = {}

    def node(nid, kind, **inputs):
        graph[str(nid)] = {'class_type': kind, 'inputs': inputs}

    if spec['architecture'] in ('checkpoint', 'flux_checkpoint'):
        node(1, 'CheckpointLoaderSimple', ckpt_name=files['checkpoint'])
        model, clip, vae = ['1', 0], ['1', 1], ['1', 2]
    elif spec['architecture'] == 'z_image':
        node(1, 'UNETLoader', unet_name=files['diffusion_models'], weight_dtype='default')
        node(2, 'CLIPLoader', clip_name=files['text_encoders'], type='lumina2', device='default')
        node(5, 'VAELoader', vae_name=files['vae'])
        node(10, 'ModelSamplingAuraFlow', model=['1', 0], shift=3.0)
        model, clip, vae = ['10', 0], ['2', 0], ['5', 0]
    else:
        raise ValueError('该生图模型尚未实现对应工作流。')
    node(3, 'CLIPTextEncode', clip=clip, text=prompt)
    node(6, 'CLIPTextEncode', clip=clip, text=sampling['negative_prompt'])
    node(4, 'EmptySD3LatentImage' if spec['architecture'] in ('z_image', 'flux_checkpoint') else 'EmptyLatentImage',
         width=width, height=height, batch_size=1)
    latent = ['4', 0]
    if request.reference_images:
        if not references or len(references) != 1:
            raise ValueError('原图尚未上传到目标 ComfyUI，请检查图片任务的参考图快照。')
        width, height = image_size(f"{references[0]['width']}:{references[0]['height']}", resolution)
        node(21, 'LoadImage', image=references[0]['comfy_name'])
        node(14, 'ImageScale', image=['21', 0], upscale_method='lanczos', width=width, height=height, crop='disabled')
        node(15, 'VAEEncode', pixels=['14', 0], vae=vae)
        latent = ['15', 0]
    node(7, 'KSampler', model=model, seed=request.seed, steps=sampling['steps'], cfg=sampling['cfg'],
         sampler_name=sampling['sampler'], scheduler=sampling['scheduler'], positive=['3', 0], negative=['6', 0],
         latent_image=latent, denoise=sampling['denoise'])
    node(8, 'VAEDecode', samples=['7', 0], vae=vae)
    node(9, 'SaveImage', images=['8', 0], filename_prefix=prefix)
    return graph, width, height
