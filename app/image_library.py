"""Environment plans for native checkpoint, FLUX and Z-Image model adapters."""
from pathlib import Path
import shutil
from urllib.parse import urlsplit

from .downloads import Downloader
from .environment import hardware
from .image_models import model_spec
from .image_schemas import ImageModels
from .storage import contained, digest, read_json


def library_plan(environment, model_id, models=None):
    spec = model_spec(model_id)
    settings = environment.settings()
    env = environment.config.renderer_config()
    shared_url = settings.comfy_url or env.get('comfy_url', 'http://127.0.0.1:8188')
    shared = environment.probe(shared_url)
    local = urlsplit(shared_url).hostname in ('127.0.0.1', 'localhost', '::1')
    required = {'CLIPTextEncode','KSampler','VAEDecode','SaveImage','VAEEncode','ImageScale','LoadImage'}
    if spec['architecture'] == 'z_image':
        required.update(('UNETLoader','CLIPLoader','VAELoader','ModelSamplingAuraFlow','EmptySD3LatentImage'))
    else:
        required.update(('CheckpointLoaderSimple', 'EmptySD3LatentImage' if spec['architecture']=='flux_checkpoint' else 'EmptyLatentImage'))
    selection = ImageModels.model_validate(models).model_dump() if models is not None else settings.models.model_dump() if settings.image_model == model_id else {}
    shared_models = all(any((name.replace('\\','/')==selection[f['category']] if selection.get(f['category']) else name.replace('\\','/').rsplit('/',1)[-1]==f['name'])
                            for name in shared['choices'].get(f['category'],[])) for f in spec['files'])
    managed = settings.engine == 'managed' or (settings.engine == 'auto' and local and
              (bool(required-set(shared.get('node_types', []))) or not shared_models))
    url = f'http://127.0.0.1:{settings.managed_port}' if managed else shared_url
    current = environment.probe(url) if managed else shared
    device, vram = current['gpu'], current['vram_mb']
    if managed and not current['connected']:
        device = (hardware(environment.root).get('gpu') or [None])[0]
        vram = device.get('vram_mb') if device else None
    model_root = Path(settings.library_models_dir or (environment.root/'models/image-library' if managed else Path(env.get('comfy_dir') or environment.root/'engines/ComfyUI')/'models')).resolve()
    local_files = managed or (local and bool(settings.library_models_dir or (shared_url==env.get('comfy_url') and env.get('comfy_dir'))))
    available = environment.inventory(model_root,current,local_files)
    rows, errors = [], []
    for f in spec['files']:
        category = f['category']
        chosen = selection.get(category, '')
        if chosen and chosen not in {item['name'] for item in available[category]}:
            errors.append('所选模型文件不存在或尚未被目标服务识别：'+chosen)
        if not chosen:
            chosen = next((item['name'] for item in available[category] if item['name'].rsplit('/',1)[-1]==f['name']), f['name'])
        known = chosen.rsplit('/',1)[-1] == f['name']
        target = contained(model_root,category+'/'+chosen)
        comfy_name = next((n for n in current['choices'].get(category,[]) if n.replace('\\','/')==chosen),None)
        state = Downloader.verification_status(target,f['size'],f['sha256']) if known and local_files else 'invalid'
        # A service filename is not proof that a locally managed weight is intact.
        if known and local_files and (target.is_file() or not comfy_name):
            action = 'download' if state == 'invalid' else 'verify' if state == 'unknown' else 'available' if comfy_name else 'verified'
        else:
            action = 'available' if comfy_name else 'download' if known else 'local' if target.is_file() else 'missing'
        row = {**f,'name':chosen,'target':str(target),'comfy_name':comfy_name,'custom':not known,
               'action':action}
        if not known:
            row.update(size=target.stat().st_size if target.is_file() else 0,sha256=None,url=None)
        rows.append(row)
    missing = sorted(required-set(current.get('node_types',[])))
    engine_root,source,runtime_python=environment.paths()
    base_python=env.get('python')
    bootstrap=managed and not runtime_python.is_file() and (not base_python or not Path(base_python).is_file())
    source_needed=managed and not current['connected'] and (not (source/'main.py').is_file() or read_json(engine_root/'source-ready.json',{}).get('revision')!=environment.manifest['comfyui']['revision'])
    model_bytes=sum(m['size'] for m in rows if m['action']=='download')
    runtime_bytes=environment.manifest['bootstrap']['size'] if bootstrap else 0
    source_bytes=environment.manifest['comfyui']['size'] if source_needed else 0
    disk=model_root
    while not disk.exists():disk=disk.parent
    ready=current['connected'] and not missing and not errors and all(m['comfy_name'] and m['action']=='available' for m in rows)
    return {'image_model':model_id,'architecture':spec['architecture'],'model_spec':spec,
            'engine':'managed' if managed else 'shared','comfy_url':url,'connected':current['connected'],'missing_nodes':missing,
            'reference_support':not bool({'LoadImage','VAEEncode'}-set(current.get('node_types',[]))),
            'reference_modes':['edit'],'max_reference_images':1,'transparent_support':False,
            'sampling_support':current.get('sampling_support'),'gpu':device,'vram_mb':vram,
            'recommendation':{'resolution':spec['resolution'],'message':'使用该模型的原生 ComfyUI 工作流；建议先用推荐参数试图。'},
            'variant':'auto','variants':{'auto':{'name':spec['name']}},'models':rows,'models_dir':str(model_root),
            'download_bytes':model_bytes+runtime_bytes+source_bytes,'models_download_bytes':model_bytes,
            'runtime_download_bytes':runtime_bytes,'bootstrap_needed':bootstrap,'source_download_bytes':source_bytes,
            'available_models':available,'selection':selection,'selection_errors':errors,
            'verify_bytes':sum(m['size'] for m in rows if m['action']=='verify'),
            'requires_confirmation':not ready and bool(model_bytes or bootstrap or source_needed),
            'confirmation_token':digest({'image_model':model_id,'url':url,'directory':str(model_root),'models':rows,'bootstrap':bootstrap,'source':source_needed}),
            'engine_free_disk_bytes':shutil.disk_usage(environment.root).free,'free_disk_bytes':shutil.disk_usage(disk).free,
            'ready':bool(ready),'local_download':local_files,'license':{'notice':f"模型许可：{spec['license']}，使用限制以模型原始页面为准。",'url':spec['source']},'auto_download':False}
