from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import av
import imageio_ffmpeg
import requests

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / ('config.json' if (ROOT / 'config.json').exists() else 'config.default.json')).read_text(encoding='utf-8'))
FPS = 24


def ensure_comfy(status=None, profile=None):
    task_root = Path(CONFIG.get('runtime_root', ROOT))
    workflow_environment = None
    if profile and CONFIG['profiles'][profile].get('workflow', 'native') != 'native':
        from app.config import ConfigStore
        from app.video_environment import VideoWorkflowEnvironment
        environment = VideoWorkflowEnvironment(ConfigStore(task_root))
        workflow_environment = environment
        plan = environment.prepare(profile, lambda message, **extra: status(message) if status else None, lambda: False)
        if plan.get('restart_required'):
            from app.processes import stop_owned_comfy
            stop_owned_comfy(CONFIG, task_root / 'data/comfy-runtime')
    try:
        requests.get(CONFIG['comfy_url'] + '/system_stats', timeout=3).raise_for_status()
        return
    except requests.RequestException:
        pass
    endpoint = urlsplit(CONFIG['comfy_url'])
    if CONFIG.get('mode') == 'remote' or endpoint.hostname not in ('localhost', '127.0.0.1'):
        raise RuntimeError('远程 ComfyUI 无法连接，请在远程机器启动并检查服务地址。')
    port = endpoint.port or (443 if endpoint.scheme == 'https' else 80)
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError('ComfyUI 端口已占用但暂时无响应，请稍后继续。')
    if status:
        status('正在启动本地生成引擎……')
    runtime = task_root / 'data/comfy-runtime'
    args = [CONFIG['python'], '-u', 'main.py', '--listen', '127.0.0.1', '--port', str(port),
            '--base-directory', str(runtime),
            '--disable-auto-launch', '--disable-api-nodes', '--reserve-vram', '1.5',
            '--cache-none', '--disable-pinned-memory', '--disable-async-offload',
            '--disable-comfy-compiler', '--disable-all-custom-nodes', '--whitelist-custom-nodes',
            'ComfyUI-DramaFactory-Runtime']
    optional_node = task_root / 'data/comfy-runtime/custom_nodes/ComfyUI-MiniMax-H3-PDD-Acc'
    if (optional_node / 'nodes.py').is_file():
        args.append('ComfyUI-MiniMax-H3-PDD-Acc')
    upscaler_node = task_root / 'data/comfy-runtime/custom_nodes/Comfyui_Minimax_h3_latent_Upscaler'
    if (upscaler_node / '__init__.py').is_file():
        args.append('Comfyui_Minimax_h3_latent_Upscaler')
    if CONFIG.get('fast_disk', True):
        args.append('--fast-disk')
    if CONFIG.get('disable_dynamic_vram', False):
        args.append('--disable-dynamic-vram')
    model_paths = Path(CONFIG.get('extra_model_paths_file') or task_root / 'extra_model_paths.yaml')
    if model_paths.is_file():
        args += ['--extra-model-paths-config', str(model_paths)]
    workflow_paths = task_root / 'data/video-workflow-paths.yaml'
    if workflow_paths.is_file():
        args += ['--extra-model-paths-config', str(workflow_paths)]
    stamp = time.strftime('%Y%m%d_%H%M%S')
    process_env = os.environ.copy()
    # Portable installs must not depend on the launcher's system temp directory.
    temporary = task_root / 'data/comfy-temp'
    temporary.mkdir(parents=True, exist_ok=True)
    for name in ('TEMP', 'TMP', 'TMPDIR'):
        process_env[name] = str(temporary)
    numba_cache = task_root / 'data/numba-cache'
    numba_cache.mkdir(parents=True, exist_ok=True)
    process_env['NUMBA_CACHE_DIR'] = str(numba_cache)
    for kind in ('input', 'output', 'user', 'temp', 'cache'):
        (runtime / kind).mkdir(parents=True, exist_ok=True)
    for kind in ('input', 'output', 'user', 'temp'):
        args += ['--' + kind + '-directory', str(runtime / kind)]
    args += ['--database-url', 'sqlite:///' + (runtime / 'user/comfyui.db').as_posix()]
    process_env['DRAMA_FACTORY_CACHE_DIR'] = str(runtime / 'cache')
    bundled_node = ROOT / 'nodes/ComfyUI-DramaFactory'
    if not bundled_node.is_dir():
        raise RuntimeError('随包缓存节点缺失，请重新解压完整工作台。')
    shutil.copytree(bundled_node, runtime / 'custom_nodes/ComfyUI-DramaFactory-Runtime', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    import yaml
    source_models = runtime / 'source_model_paths.yaml'
    source_models.write_text(yaml.safe_dump({'installed_models': {
        'base_path': str(Path(CONFIG['comfy_dir'])/'models'),
        **{category:category for category in ('diffusion_models','text_encoders','vae','loras','checkpoints','embeddings','vae_approx')}
    }}, allow_unicode=True), encoding='utf-8')
    args += ['--extra-model-paths-config', str(source_models)]
    node_paths = runtime / 'node_paths.yaml'
    node_paths.write_text(yaml.safe_dump({'drama_factory_runtime': {'base_path': str(runtime),
                          'custom_nodes': 'custom_nodes', 'is_default': True}}, allow_unicode=True), encoding='utf-8')
    args += ['--extra-model-paths-config', str(node_paths)]
    (task_root / 'logs').mkdir(parents=True, exist_ok=True)
    if CONFIG.get('safe_file_read', True):
        process_env['DRAMA_SAFE_FILE_READ'] = '1'
    with (task_root / f'logs/comfy_{stamp}.stdout.log').open('wb') as out, (task_root / f'logs/comfy_{stamp}.stderr.log').open('wb') as err:
        process = subprocess.Popen(args, cwd=CONFIG['comfy_dir'], stdout=out, stderr=err,
                                   env=process_env,
                                   creationflags=0x08000000 if os.name == 'nt' else 0)
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f'ComfyUI 启动失败，请查看 logs/comfy_{stamp}.stderr.log。')
        try:
            requests.get(CONFIG['comfy_url'] + '/system_stats', timeout=2).raise_for_status()
            if workflow_environment and not workflow_environment.plan(profile)['ready']:
                raise RuntimeError('视频引擎已启动，但所选工作流的节点或模型仍未加载。请检查本次 ComfyUI 启动日志。')
            return
        except requests.RequestException:
            time.sleep(1)
    raise RuntimeError('ComfyUI 启动超时，请查看启动日志。')


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def canvas(megapixels, ratio):
    a, b = map(int, ratio.split(':'))
    width = round(math.sqrt(megapixels * 1_000_000 * a / b) / 32) * 32
    height = round(math.sqrt(megapixels * 1_000_000 * b / a) / 32) * 32
    return width, height


def frames(seconds):
    count = max(5, math.ceil(seconds * FPS))
    return count + (5 - count % 17) % 17


def output_canvas(preset, ratio):
    from app.video_workflows import refined_size
    return refined_size(*canvas(preset['megapixels'], ratio), preset)


def api(path, data=None):
    url = CONFIG['comfy_url'] + path
    headers = {'Authorization': 'Bearer ' + CONFIG['comfy_auth_token']} if CONFIG.get('comfy_auth_token') else {}
    try:
        response = requests.get(url, timeout=30, headers=headers) if data is None else requests.post(url, json=data, timeout=60, headers=headers)
    except requests.RequestException as exc:
        raise RuntimeError('无法连接 ComfyUI，请先启动 8188 服务。') from exc
    if not response.ok:
        detail = response.text[:1600]
        raise RuntimeError(f'ComfyUI HTTP {response.status_code}: {detail}')
    return response.json() if response.content else {}


def cache_exists(category, filename, local_path):
    from urllib.parse import urlencode
    return api('/drama/cache?' + urlencode({'category': category, 'filename': filename}))['exists']


def validate_story(story, max_shots=150):
    if not isinstance(story, dict) or not str(story.get('title', '')).strip():
        raise ValueError('分镜缺少 title。')
    characters = story.get('characters', [])
    if not isinstance(characters, list):
        raise ValueError('characters 必须是列表。')
    ids = set()
    for character in characters:
        cid = character.get('id')
        if not isinstance(cid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}', cid) or cid in ids:
            raise ValueError('角色 id 必须唯一，只能使用英文、数字、下划线。')
        ids.add(cid)
        if not character.get('visual_description'):
            raise ValueError(f'角色 {cid} 缺少固定外观描述。')
    shots = story.get('shots', [])
    if not isinstance(shots, list) or not 1 <= len(shots) <= max_shots:
        raise ValueError(f'镜头数必须在 1～{max_shots}。')
    for index, shot in enumerate(shots, 1):
        shot['id'] = index
        duration = shot.get('duration', 4)
        if not isinstance(duration, (int, float)) or not 4 <= duration <= 15:
            raise ValueError(f'镜头 {index} 时长必须是 4～15 秒。')
        if not isinstance(shot.get('prompt'), str) or len(shot['prompt']) < 30:
            raise ValueError(f'镜头 {index} 缺少完整 H3 提示词。')
        if not isinstance(shot.get('characters', []), list) or set(shot.get('characters', [])) - ids:
            raise ValueError(f'镜头 {index} 引用了未定义角色。')
        dialogue = shot.setdefault('dialogue', [])
        if not isinstance(dialogue, list):
            raise ValueError(f'镜头 {index} dialogue 必须是列表。')
        for line in dialogue:
            if not isinstance(line, dict) or not isinstance(line.get('text'), str):
                raise ValueError(f'镜头 {index} 的对白格式不正确。')
    from app.continuity import validate_links
    validate_links(shots)
    return story


def plan(outline, total_seconds=24, shot_seconds=4, style='温暖的二维动漫短剧', ratio='9:16', status=None):
    if not outline.strip():
        raise ValueError('请填写剧本大纲。')
    if not 4 <= shot_seconds <= 8 or not 4 <= total_seconds <= 600:
        raise ValueError('单镜头 4～8 秒，总时长 4～600 秒。')
    count = max(1, math.ceil(total_seconds / shot_seconds))
    key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if not key:
        key_file = ROOT / '.secrets/deepseek.key'
        if key_file.exists():
            key = key_file.read_text(encoding='utf-8').strip()
    if not key:
        raise RuntimeError('请先在设置里填写 DeepSeek API key。')
    system = '''你是 MiniMax H3 短剧分镜导演。把用户大纲转换成严格 JSON，绝不输出 Markdown。
结构：{"title":"中文标题","style":"统一风格","characters":[{"id":"英文id","name":"中文名","visual_description":"英文、固定发型服装配色年龄五官","voice_description":"中文音色描述"}],"shots":[{"id":1,"scene":"中文场景","summary":"中文镜头摘要","duration":4,"characters":["角色id"],"continuity_group":"场景标识","dialogue":[{"speaker":"角色名","text":"短中文对白"}],"prompt":"H3完整提示词"}]}。
每条 prompt 必须包含 integrated_multimodal_description: [Shot 1]、overall_soundscape:、non_diegetic_music: 三个段落；画面描述用英文，对白保留原文中文并用双引号标明，音色和说话人用英文明确标注。
每镜头是单一连续镜头，一个简单可执行动作，至多两名角色，至多一句中文对白；对白长度控制在每秒3个汉字以内，留出开头0.5秒、结尾0.8秒安静空间。不要口号、水印、画面文字、字幕。背景音乐默认 None，各镜头仅生成环境音与对白，避免拼接配乐跳变。
每个 prompt 完整重复该镜头中角色固定外观、声音、衣服和统一风格，不使用“same as previous”这种依赖未见上下文的文字。不自行在 prompt 添加 <Picture> 引用标记，运行器会按真实参考素材插入。
人物连续性：同一角色所有镜头相同服装、发型、外观；保持左右站位、道具、时间和动作因果，景别切换要合理。镜头 id 顺序连续。duration 按指定单镜头时长。严格输出要求的镜头数，不输出备选方案。'''
    payload = {
        'model': CONFIG['deepseek_model'],
        'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content':
            f'风格：{style}\n比例：{ratio}\n镜头数：{count}\n每镜头：{shot_seconds}秒\n大纲：\n{outline}'}],
        'response_format': {'type': 'json_object'},
        'max_tokens': min(32000, max(4000, count * 1000)),
        'stream': True,
        'thinking': {'type': 'disabled'},
    }
    if status:
        status('DeepSeek 正在拆解大纲与编写分镜……')
    pieces = []
    with requests.post(CONFIG['deepseek_url'] + '/chat/completions', headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
        json=payload, stream=True, timeout=(20, 180)) as response:
        if not response.ok:
            # 不记录请求头、key 或完整请求对象。
            raise RuntimeError(f'DeepSeek 调用失败 HTTP {response.status_code}。请检查 key、额度和模型名称。')
        for line in response.iter_lines():
            if not line or not line.startswith(b'data: '):
                continue
            data = line[6:]
            if data == b'[DONE]':
                break
            event = json.loads(data)
            for choice in event.get('choices', []):
                pieces.append(choice.get('delta', {}).get('content') or '')
                if choice.get('finish_reason') == 'length':
                    raise RuntimeError('分镜响应被截断，请缩短总时长后重试。')
    story = validate_story(json.loads(''.join(pieces)), max_shots=count)
    if len(story['shots']) != count:
        raise ValueError(f'DeepSeek 返回 {len(story["shots"])} 个镜头，要求 {count} 个；请重新生成。')
    story['aspect_ratio'] = ratio
    return story


def graph_for(shot, project_id, profile='draft', ratio='9:16', references=None, seed=1, bindings=None):
    preset = CONFIG['profiles'][profile]
    width, height = canvas(preset['megapixels'], ratio)
    references = references or []
    bindings = bindings or {}
    mode = shot.get('compiled_mode') or ('Ref2VA' if references else 'T2VA')
    is_reference = mode == 'Ref2VA'
    model = CONFIG['ref_model'] if is_reference else CONFIG['fl_model']
    graph = {}

    def node(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    node(1, 'UNETLoader', unet_name=model, weight_dtype='default')
    node(2, 'CLIPLoader', clip_name=CONFIG['text_encoder'], type='minimax', device='default')
    node(3, 'VAELoader', vae_name=CONFIG['video_vae'])
    node(4, 'VAELoader', vae_name=CONFIG['audio_vae'])
    model_link = ['1', 0]
    if preset['turbo']:
        node(5, 'LoraLoaderModelOnly', model=model_link,
             lora_name=CONFIG['ref_lora'] if is_reference else CONFIG['fl_lora'], strength_model=preset.get('lora_strength', 1.0))
        model_link = ['5', 0]
    if CONFIG.get('attention'):
        node(6, 'ModelAttentionBackend', model=model_link, attention=CONFIG['attention'])
        model_link = ['6', 0]
    prompt = shot['prompt']
    common = dict(clip=['2', 0], vae=['3', 0], prompt=prompt, width=width, height=height, length=frames(shot['duration']))
    if is_reference:
        instructions = []
        actual_images = bindings.get('images', []) or [{'comfy_file': r['image'], 'name': r['name']} for r in references]
        for index, ref in enumerate(actual_images, 1):
            number = 20 + index
            node(number, 'LoadImage', image=ref['comfy_file'])
            common[f'ref_images.ref_image_{index}'] = [str(number), 0]
            instructions.append(f'<Picture {index}> is the visual identity reference for {ref["name"]}. '
                                'Preserve their exact face, hairstyle and clothes; follow the new shot action and camera.')
        if not shot.get('compiled_mode'):
            common['prompt'] = '\n'.join(instructions) + '\n\n' + prompt
        if bindings.get('audios') or bindings.get('videos'):
            common['audio_vae'] = ['4', 0]
        for index, ref in enumerate(bindings.get('videos', []), 1):
            number = 40 + index * 2
            node(number, 'LoadVideo', file=ref['comfy_file'])
            node(number + 1, 'GetVideoComponents', video=[str(number), 0])
            common[f'ref_videos.ref_video_{index}'] = [str(number + 1), 0]
            if ref.get('include_audio', True):
                common[f'ref_video_audios.ref_video_audio_{index}'] = [str(number + 1), 1]
        for index, ref in enumerate(bindings.get('audios', []), 1):
            number = 60 + index
            node(number, 'LoadAudio', audio=ref['comfy_file'])
            common[f'ref_audios.ref_audio_{index}'] = [str(number), 0]
        common['ref_image_size'] = 'match'
        node(7, 'MiniMaxH3ReferenceToVideo', **common)
    else:
        for index, key in enumerate(('first_frame', 'last_frame')):
            if bindings.get(key):
                number = 71 + index
                node(number, 'LoadImage', image=bindings[key]['comfy_file'])
                common[key] = [str(number), 0]
        node(7, 'MiniMaxH3ImageToVideo', **common)
    node(8, 'RandomNoise', noise_seed=seed)
    node(9, 'BasicGuider', model=model_link, conditioning=['7', 0])
    node(10, 'KSamplerSelect', sampler_name=preset.get('sampler', 'res_multistep'))
    node(11, 'BasicScheduler', model=model_link, scheduler=preset.get('scheduler', 'simple'), steps=preset['steps'], denoise=preset.get('denoise', 1.0))
    node(12, 'SamplerCustomAdvanced', noise=['8', 0], guider=['9', 0], sampler=['10', 0],
         sigmas=['11', 0], latent_image=['7', 1])
    node(13, 'VAEDecodeTiled', samples=['12', 0], vae=['3', 0], tile_size=256, overlap=64, temporal_size=32, temporal_overlap=8)
    node(14, 'VAEDecodeAudio', samples=['12', 0], vae=['4', 0])
    node(15, 'CreateVideo', images=['13', 0], audio=['14', 0], fps=FPS)
    cache_id = shot.get('uid') or f'{shot["id"]:03d}'
    node(16, 'SaveVideo', video=['15', 0], filename_prefix=f'drama/{project_id}/shot_{cache_id}',
         format='mp4', **{'format.codec': 'h264'})
    from app.video_workflows import apply_workflow
    return apply_workflow(graph, preset, is_reference)


def validate_graph(graph):
    catalog = api('/object_info')
    for nid, node in graph.items():
        kind = node['class_type']
        if kind not in catalog:
            raise RuntimeError(f'ComfyUI 缺少节点：{kind}')
        inputs = node['inputs']
        schema = catalog[kind]['input']
        for field, spec in schema.get('required', {}).items():
            if field not in inputs:
                raise RuntimeError(f'节点 {kind} 缺少输入 {field}')
            if field != 'image' and isinstance(spec[0], list) and inputs[field] not in spec[0]:
                raise RuntimeError(f'节点 {kind} 找不到模型或参数：{inputs[field]}')
        for field, value in inputs.items():
            if isinstance(value, list):
                if value[0] not in graph:
                    raise RuntimeError(f'节点 {nid} 引用了不存在的节点。')


def ffmpeg(args):
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', *map(str, args)],
                            capture_output=True, encoding='utf-8', errors='replace', creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError('视频处理失败：' + result.stderr[-1800:])


def media_info(path, verify_timestamps=False):
    with av.open(str(path)) as container:
        if not container.streams.video:
            raise RuntimeError('视频产物没有视频流。')
        video = container.streams.video[0]
        duration = float(video.duration * video.time_base) if video.duration is not None else container.duration / av.time_base
        count = video.frames
        monotonic = True
        if verify_timestamps or not count:
            count, previous = 0, None
            for frame in container.decode(video):
                if frame.pts is None or previous is not None and frame.pts <= previous:
                    monotonic = False
                previous = frame.pts
                count += 1
        return {'duration': duration, 'width': video.width, 'height': video.height, 'audio': bool(container.streams.audio),
                'frames': count, 'fps': float(video.average_rate) if video.average_rate else 0,
                'time_base': str(video.time_base), 'timestamps_monotonic': monotonic}


def timestamp(seconds):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def assemble(project, story, clips, ratio, status=None, subtitles=True, cancel=None):
    from app.finishing import build
    settings = load_json(project / 'settings.json')
    if (project / 'finishing-settings.json').is_file():
        settings.update(load_json(project / 'finishing-settings.json'))
    settings['subtitles'] = subtitles
    width, height = output_canvas(CONFIG['profiles'][settings['profile']], ratio)
    return build(project, story, clips, width, height, settings, status or (lambda text: None),cancel=cancel,proxy=CONFIG.get('proxy',''))


class Runner:
    def __init__(self, project, stop=None, callback=None):
        self.project = Path(project)
        self.stop = stop or threading.Event()
        self.callback = callback
        path = self.project / 'state.json'
        self.state = load_json(path) if path.exists() else {'shots': {}, 'message': '', 'status': 'ready'}
        self.client = str(uuid.uuid4())
        self.binding_resolver = None
        self.prompt_compiler = None
        self.model_versions = {}

    def report(self, message, **changes):
        self.state.update(changes)
        self.state['message'] = message
        self.state['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        save_json(self.project / 'state.json', self.state)
        if self.callback:
            self.callback(copy.deepcopy(self.state))
        print(message, flush=True)

    def wait(self, prompt_id, conditioning=False, phase='decode'):
        deadline = time.monotonic() + CONFIG['shot_timeout_seconds']
        last_update = 0
        while time.monotonic() < deadline:
            history = api('/history/' + prompt_id).get(prompt_id)
            if history:
                for event, details in history.get('status', {}).get('messages', []):
                    if event in ('execution_error', 'execution_interrupted'):
                        raise RuntimeError(f'镜头生成失败：{details.get("exception_message", event)}')
                if history.get('status', {}).get('completed'):
                    stamps = [details.get('timestamp') for event, details in history.get('status', {}).get('messages', []) if isinstance(details.get('timestamp'), (int, float))]
                    if stamps:
                        record = self.state.get('shots', {}).get(str(self.state.get('current_shot')), {})
                        record.setdefault('timings', {})[phase] = {'seconds': round((max(stamps) - min(stamps)) / 1000, 3), 'prompt_id': prompt_id}
                    if conditioning:
                        return history
                    for output in history.get('outputs', {}).values():
                        for key in ('images', 'gifs', 'videos'):
                            for item in output.get(key, []):
                                if item.get('filename', '').lower().endswith(('.mp4', '.webm', '.mkv')):
                                    return item
                    raise RuntimeError('任务完成，但未找到视频输出。')
            if time.monotonic() - last_update > 25:
                self.report(f'镜头 {self.state.get("current_shot")} 正在生成，已等待 {int(CONFIG["shot_timeout_seconds"]-(deadline-time.monotonic()))} 秒……')
                last_update = time.monotonic()
            time.sleep(3)
        raise RuntimeError('镜头等待超时。ComfyUI 可能仍在计算；点击继续会重新关联同一任务。')

    def references(self, shot, story):
        assets = load_json(self.project / 'references.json') if (self.project / 'references.json').exists() else {}
        refs = []
        for cid in shot.get('characters', []):
            asset = assets.get(cid)
            image = asset.get('image') if isinstance(asset, dict) else asset
            origin = asset.get('shot_id', 0) if isinstance(asset, dict) else 0
            origin_uid = asset.get('shot_uid') if isinstance(asset, dict) else None
            if origin_uid == shot.get('uid') and origin_uid or not origin_uid and origin >= shot['id']:
                continue
            local_file = asset.get('local_file') if isinstance(asset, dict) else None
            image_path = self.project / local_file if local_file else Path(CONFIG['comfy_dir']) / 'input' / (image or '')
            image_root = self.project if local_file else Path(CONFIG['comfy_dir']) / 'input'
            if not image_path.resolve().is_relative_to(image_root.resolve()):
                raise RuntimeError('参考素材路径越出允许目录。')
            if image and image_path.is_file():
                if not local_file:
                    local_file = 'assets/legacy_ref_' + cid + image_path.suffix
                    target = self.project / local_file
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(image_path, target)
                    image_path = target
                    assets[cid] = {**(asset if isinstance(asset, dict) else {'image':image,'shot_id':origin}), 'local_file':local_file}
                    save_json(self.project / 'references.json', assets)
                name = next(c['name'] for c in story['characters'] if c['id'] == cid)
                refs.append({'image': image, 'name': name,
                             'sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(), 'local_file': local_file,'character':cid})
        return refs[:2]

    def capture_reference(self, shot, clip):
        if not load_json(self.project / 'settings.json').get('auto_reference', True):
            return
        # 单角色镜头自动成为该角色的参考；多人镜头不能可靠分离身份。
        cast = shot.get('characters', [])
        if len(cast) != 1:
            return
        path = self.project / 'references.json'
        assets = load_json(path) if path.exists() else {}
        origin = assets.get(cast[0], {})
        if origin and not isinstance(origin, dict):
            return
        clip_hash = hashlib.sha256(clip.read_bytes()).hexdigest()
        if origin:
            if origin.get('shot_id') == 0 or origin.get('shot_uid') not in (None, shot.get('uid')):
                return
            if not origin.get('shot_uid') and origin.get('shot_id') != shot['id']:
                return
            if origin.get('clip_sha256') == clip_hash:
                return
        relative = f'drama_refs/{self.project.name}/{cast[0]}.png'
        local_relative = 'assets/auto_' + cast[0] + '.png'
        target = self.project / local_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg(['-ss', '0.6', '-i', clip, '-frames:v', '1', target])
        from app.comfyio import upload_file
        relative = upload_file(target, f'drama_refs/{self.project.name}', target.name, CONFIG['comfy_url'], CONFIG.get('comfy_auth_token',''))
        assets[cast[0]] = {'image': relative, 'shot_id': shot['id'], 'shot_uid': shot.get('uid'), 'local_file': local_relative,
                          'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'clip_sha256': clip_hash}
        save_json(path, assets)

    def encode(self, graph, shot, signature):
        cache_id = shot.get('uid') or f'{shot["id"]:03d}'
        filename = f'drama/{self.project.name}/shot_{cache_id}_{signature[:12]}.safetensors'
        target = Path(CONFIG['comfy_dir']) / 'models/embeddings' / filename
        if not cache_exists('conditioning', filename, target):
            from app.video_workflows import subgraph
            encoding = subgraph(graph, ['7'])
            if 'audio_vae' in graph['7']['inputs']:
                encoding['4'] = graph['4']
            encoding['30'] = {'class_type': 'DramaSaveConditioning', 'inputs': {'conditioning': ['7', 0], 'filename': filename}}
            validate_graph(encoding)
            self.report(f'镜头 {shot["id"]}：先编码提示词与参考素材，随后释放大编码器。', current_stage='encoding')
            record = self.state['shots'][str(shot['id'])]
            prompt_id = record.get('encoding_prompt_id')
            queue = api('/queue')
            known = {q[1] for key in ('queue_running', 'queue_pending') for q in queue.get(key, [])}
            history = api('/history/' + prompt_id).get(prompt_id) if prompt_id else None
            if history and history.get('status', {}).get('status_str') == 'error':
                prompt_id = None
            if not prompt_id or (prompt_id not in known and not history):
                prompt_id = api('/prompt', {'prompt': encoding, 'client_id': self.client})['prompt_id']
                record['encoding_prompt_id'] = prompt_id
                self.report('提示词编码任务已提交。')
            self.wait(prompt_id, conditioning=True, phase='encoding')
            if not cache_exists('conditioning', filename, target):
                raise RuntimeError('编码任务完成，但条件缓存没有保存。')
        api('/free', {'unload_models': True, 'free_memory': True})
        time.sleep(2)
        from app.video_workflows import subgraph, replace_link
        encoding_ids = set(subgraph(graph, ['7']))
        render = {nid: value for nid, value in graph.items() if nid not in encoding_ids or nid in ('3','4')}
        render['7'] = {'class_type': 'DramaLoadConditioning', 'inputs': {'filename': filename}}
        render['17'] = {'class_type': 'EmptyMiniMaxH3LatentAV', 'inputs': {
            field: graph['7']['inputs'][field] for field in ('width', 'height', 'length')}}
        replace_link(render, ['7',1], ['17',0])
        return render

    def sample(self, graph, shot, signature):
        cache_id = shot.get('uid') or f'{shot["id"]:03d}'
        filename = f'{self.project.name}/shot_{cache_id}_{signature[:12]}.safetensors'
        target = Path(CONFIG['comfy_dir']) / 'output/drama_latents' / filename
        if not cache_exists('latent', filename, target):
            from app.video_workflows import subgraph
            sampling = subgraph(graph, ['12'])
            sampling['31'] = {'class_type': 'DramaSaveLatent', 'inputs': {'samples': ['12', 0], 'filename': filename}}
            validate_graph(sampling)
            save_json(self.project / 'prompts' / f'{shot["id"]:03d}_sample.json', sampling)
            record = self.state['shots'][str(shot['id'])]
            prompt_id = record.get('sampling_prompt_id')
            queue = api('/queue')
            known = {q[1] for key in ('queue_running', 'queue_pending') for q in queue.get(key, [])}
            history = api('/history/' + prompt_id).get(prompt_id) if prompt_id else None
            if history and history.get('status', {}).get('status_str') == 'error':
                prompt_id = None
            if not prompt_id or (prompt_id not in known and not history):
                prompt_id = api('/prompt', {'prompt': sampling, 'client_id': self.client})['prompt_id']
                record['sampling_prompt_id'] = prompt_id
                self.report(f'镜头 {shot["id"]}：H3 正在生成并保存音画潜空间。', current_stage='sampling')
            self.wait(prompt_id, conditioning=True, phase='sampling')
            if not cache_exists('latent', filename, target):
                raise RuntimeError('采样已完成，但音画潜空间没有保存。')
        api('/free', {'unload_models': True, 'free_memory': True})
        time.sleep(2)
        from app.video_workflows import subgraph, replace_link
        decoding = subgraph(graph, ['16'], stop={'12'})
        decoding.pop('12')
        decoding['32'] = {'class_type': 'DramaLoadLatent', 'inputs': {'filename': filename}}
        replace_link(decoding, ['12',0], ['32',0])
        return decoding

    def run(self, limit=None):
        lock = self.project / '.running'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError('此项目已在运行。若进程异常退出，请使用启动面板的恢复功能。') from exc
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        try:
            story = validate_story(load_json(self.project / '分镜.json'))
            settings = load_json(self.project / 'settings.json')
            ensure_comfy(self.report, profile=settings['profile'])
            clips = []
            render_count = 0
            self.report('开始顺序生成', status='rendering', total_shots=len(story['shots']))
            records = self.state.setdefault('shots_by_uid', {})
            for shot in story['shots']:
                key = shot.get('uid') or str(shot['id'])
                records.setdefault(key, self.state['shots'].get(str(shot['id']), {}))
            self.state['shots'] = {str(s['id']): records[s.get('uid') or str(s['id'])] for s in story['shots']}
            for index, shot in enumerate(story['shots']):
                if self.stop.is_set() or (self.project / '.stop').exists():
                    self.report('已停止，生成完的镜头已保存。', status='paused')
                    return
                locked_record = records[shot.get('uid') or str(shot['id'])]
                from app.quality import render_contract, render_contract_matches
                from app.continuity import enabled, extract_last_frame, materialize_frame
                chained = enabled(shot)
                if not chained and shot.get('locked') and locked_record.get('status') == 'done' and locked_record.get('clip'):
                    if (locked_record.get('render_contract') and not render_contract_matches(locked_record['render_contract'],story,shot)) or (not locked_record.get('render_contract') and shot.get('uid') in self.state.get('changed_shots',[])):
                        raise RuntimeError('锁定镜头内容已变化，请解锁并重生成，不能复用旧配音。')
                    locked_clip = Path(locked_record['clip'])
                    if not locked_clip.resolve().is_relative_to(self.project.resolve()):
                        raise RuntimeError('锁定镜头产物不属于当前项目。')
                    if locked_clip.is_file():
                        self.capture_reference(shot, locked_clip)
                        clips.append(locked_clip)
                        continue
                refs = self.references(shot, story) if settings.get('auto_reference', True) and not chained else []
                if chained:
                    self.report(f'镜头 {shot["id"]}：首帧功能，提取上一分镜实际末帧。', current_shot=shot['id'], current_stage='first_frame')
                    frame = extract_last_frame(self.project, shot, story['shots'][index - 1], clips[-1], self.stop.is_set)
                    bindings = {'first_frame': materialize_frame(self.project, frame, CONFIG)}
                    shot['compiled_mode'] = 'I2VA'
                else:
                    bindings = self.binding_resolver(shot, story, refs) if self.binding_resolver else {}
                if self.prompt_compiler:
                    self.report(f'镜头 {shot["id"]}/{len(story["shots"])}：校验并编译 H3 提示词。', current_shot=shot['id'], current_stage='prompt')
                    self.prompt_compiler(story, shot, bindings)
                elif chained:
                    from app.content import prompt_valid
                    prompt_valid(shot['prompt'], 'I2VA', bindings, shot.get('dialogue'), strict_keyframes=True, seconds=frames(shot['duration']) / FPS)
                graph = graph_for(shot, self.project.name, settings['profile'], settings['ratio'], refs,
                                  shot.get('seed') if shot.get('seed') is not None else settings.get('seed', 12345) + shot.get('seed_offset', shot['id']), bindings=bindings)
                signature = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()
                old_graph = copy.deepcopy(graph)
                old_graph['16']['inputs']['filename_prefix'] = f'drama/{self.project.name}/shot_{shot.get("seed_offset", shot["id"]):03d}'
                legacy_signature = hashlib.sha256(json.dumps(old_graph, sort_keys=True).encode()).hexdigest()
                for ref in refs:
                    digest = ref['sha256']
                    signature = hashlib.sha256((signature + digest).encode()).hexdigest()
                    legacy_signature = hashlib.sha256((legacy_signature + digest).encode()).hexdigest()
                record = self.state['shots'].get(str(shot['id']), {})
                if record.get('signature') == legacy_signature and record.get('status') == 'done':
                    signature = legacy_signature
                compatible_legacy = not record.get('model_versions') and record.get('signature') == signature
                if self.model_versions:
                    from app.rendering import semantic_signature, used_models
                    previous_models = record.get('model_versions', {})
                    if previous_models and record.get('status') == 'done':
                        compatible_legacy |= record.get('signature') == semantic_signature(graph, bindings, refs, previous_models, use_all_models=True) and used_models(graph, previous_models) == used_models(graph, self.model_versions)
                    signature = semantic_signature(graph, bindings, refs, self.model_versions)
                if chained:
                    # A regenerated/reordered predecessor invalidates all dependent renders.
                    signature = hashlib.sha256((signature + frame['source_shot_uid'] + frame['source_clip_sha256']).encode()).hexdigest()
                    compatible_legacy = False
                    if shot.get('locked') and record.get('status') == 'done' and record.get('signature') != signature:
                        raise RuntimeError(f'镜头 {shot["id"]} 已锁定，但上一分镜或首帧依赖已改变。请解锁此镜头后继续，避免使用旧首帧。')
                    record['first_frame'] = frame
                cache_id = shot.get('uid') or f'{shot["id"]:03d}'
                clip = Path(record['clip']) if record.get('status') == 'done' and record.get('clip') else self.project / 'clips' / (cache_id + '.mp4')
                if not clip.resolve().is_relative_to(self.project.resolve()):
                    raise RuntimeError('镜头产物路径不属于当前项目。')
                if (record.get('signature') == signature or compatible_legacy or shot.get('locked')) and record.get('status') == 'done' and clip.exists():
                    record.update(signature=signature, model_versions=self.model_versions, render_contract=render_contract(story,shot))
                    self.capture_reference(shot, clip)
                    clips.append(clip)
                    continue
                if limit is not None and render_count >= limit:
                    self.report('试跑已完成，可点击继续生成剩余镜头。', status='paused')
                    return
                self.report(f'生成镜头 {shot["id"]}/{len(story["shots"])}：{shot.get("summary", "")}', current_shot=shot['id'])
                validate_graph(graph)
                if record.get('signature') != signature:
                    if clip.exists():
                        history = self.project / 'takes' / cache_id
                        history.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(clip, history / (time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6] + '.mp4'))
                    record = {'signature': signature, 'status': 'new', 'model_versions': self.model_versions}
                    if chained:
                        record['first_frame'] = frame
                self.state['shots'][str(shot['id'])] = record
                records[shot.get('uid') or str(shot['id'])] = record
                save_json(self.project / 'prompts' / f'{shot["id"]:03d}.json', graph)
                graph = self.encode(copy.deepcopy(graph), shot, signature)
                graph = self.sample(graph, shot, signature)
                save_json(self.project / 'prompts' / f'{shot["id"]:03d}_render.json', graph)
                queue = api('/queue')
                known_ids = {q[1] for key in ('queue_running', 'queue_pending') for q in queue.get(key, [])}
                prompt_id = record.get('prompt_id') if record.get('signature') == signature else None
                old_history = api('/history/' + prompt_id).get(prompt_id) if prompt_id else None
                if old_history and old_history.get('status', {}).get('status_str') == 'error':
                    prompt_id = None
                if prompt_id and prompt_id not in known_ids and not api('/history/' + prompt_id):
                    prompt_id = None
                if not prompt_id:
                    if queue.get('queue_running') or queue.get('queue_pending'):
                        self.report('等待 ComfyUI 现有任务完成；不会清空你的队列。')
                    started = api('/prompt', {'prompt': graph, 'client_id': self.client})
                    prompt_id = started['prompt_id']
                    if started.get('node_errors'):
                        raise RuntimeError('工作流校验失败：' + json.dumps(started['node_errors'], ensure_ascii=False))
                self.state['shots'][str(shot['id'])].update(status='queued', prompt_id=prompt_id, signature=signature)
                self.report('正在解码并保存当前镜头的画面与音频。', current_stage='decoding')
                item = self.wait(prompt_id)
                output_root = Path(CONFIG['comfy_dir']) / ('temp' if item.get('type') == 'temp' else 'output')
                source = output_root / item.get('subfolder', '') / item['filename']
                if not source.resolve().is_relative_to(output_root.resolve()):
                    raise RuntimeError('ComfyUI 返回了无效的输出路径。')
                clip.parent.mkdir(exist_ok=True)
                from app.comfyio import download_file
                download_file(item, clip, CONFIG['comfy_url'], CONFIG.get('comfy_auth_token',''), self.stop.is_set)
                info = media_info(clip, verify_timestamps=True)
                expected_width, expected_height = output_canvas(CONFIG['profiles'][settings['profile']], settings['ratio'])
                if info['frames'] != frames(shot['duration']) or (info['width'], info['height']) != (expected_width, expected_height) or not info['audio'] or not info['timestamps_monotonic']:
                    raise RuntimeError('生成镜头的帧数、尺寸、原生音频或时间戳校验失败。')
                record['media'] = info
                self.state['shots'][str(shot['id'])].update(status='done', clip=str(clip), clip_relative=str(clip.relative_to(self.project)).replace('\\', '/'))
                record['render_contract']=render_contract(story,shot)
                self.state['changed_shots']=[uid for uid in self.state.get('changed_shots',[]) if uid!=shot.get('uid')]
                self.report(f'镜头 {shot["id"]} 已保存。')
                self.capture_reference(shot, clip)
                clips.append(clip)
                render_count += 1
            self.report('全部镜头完成，正在合片与生成字幕……', status='assembling', current_stage='assembling')
            output = assemble(self.project, story, clips, settings['ratio'], self.report, settings.get('subtitles', True),cancel=lambda: self.stop.is_set() or (self.project / '.stop').exists())
            self.report('短剧已完成。', status='complete', current_stage='done', output=str(output))
        except Exception as exc:
            self.report(str(exc), status='error')
            raise
        finally:
            lock.unlink(missing_ok=True)


def create_project(outline, options):
    pid = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]
    project = ROOT / 'projects' / pid
    project.mkdir(parents=True)
    (project / '大纲.txt').write_text(outline, encoding='utf-8')
    settings = {'profile': options.get('profile', 'draft'), 'ratio': options.get('ratio', '9:16'),
                'style': options.get('style', '温暖的二维动漫短剧'), 'total_seconds': int(options.get('total_seconds', 24)),
                'shot_seconds': int(options.get('shot_seconds', 4)), 'seed': int(options.get('seed', 12345)),
                'auto_reference': bool(options.get('auto_reference', True)), 'subtitles': bool(options.get('subtitles', True))}
    if settings['profile'] not in CONFIG['profiles'] or settings['ratio'] not in ('9:16', '16:9', '1:1'):
        raise ValueError('未知生成参数。')
    save_json(project / 'settings.json', settings)
    save_json(project / 'state.json', {'status': 'new', 'shots': {}, 'message': '项目已创建。'})
    return project


def main():
    parser = argparse.ArgumentParser(description='DeepSeek → H3 → 自动合片')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('outline', type=Path)
    p.add_argument('--seconds', type=int, default=24)
    p.add_argument('--shot-seconds', type=int, default=4)
    p.add_argument('--profile', choices=CONFIG['profiles'], default='draft')
    p.add_argument('--ratio', choices=['9:16', '16:9', '1:1'], default='9:16')
    p = sub.add_parser('render')
    p.add_argument('project', type=Path)
    p.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.command == 'plan':
        project = create_project(args.outline.read_text(encoding='utf-8-sig'), {
            'total_seconds': args.seconds, 'shot_seconds': args.shot_seconds, 'profile': args.profile, 'ratio': args.ratio})
        settings = load_json(project / 'settings.json')
        story = plan((project / '大纲.txt').read_text(encoding='utf-8'), settings['total_seconds'],
                     settings['shot_seconds'], settings['style'], settings['ratio'], print)
        save_json(project / '分镜.json', story)
        print(project)
    else:
        Runner(args.project).run(args.limit)


if __name__ == '__main__':
    main()
