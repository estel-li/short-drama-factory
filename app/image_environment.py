"""Pinned Qwen image assets and a managed ComfyUI beside existing video engines."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from urllib.parse import urlsplit
import zipfile

import httpx

from .downloads import Downloader
from .environment import hardware, extract_portable
from .image_schemas import ImageSettings, ImageModels
from .processes import run_process
from .providers import Cancelled
from .storage import ROOT, contained, digest, read_json, write_json


class DownloadConfirmationRequired(Cancelled):
    def __init__(self, plan):
        super().__init__('图片环境缺少文件或模型校验失败，请在图片生成页面确认下载后继续。')
        self.plan = plan


REQUIRED_NODES = ('TextEncodeQwenImage21', 'UNETLoader', 'CLIPLoader', 'VAELoader',
                  'EmptyLatentImage', 'VAEDecode', 'SaveImage', 'SamplerCustomAdvanced',
                  'ManualSigmas', 'BasicGuider', 'RandomNoise', 'KSamplerSelect', 'KSampler')
MODEL_FIELDS = {'diffusion_models': ('UNETLoader', 'unet_name'),
                'text_encoders': ('CLIPLoader', 'clip_name'), 'vae': ('VAELoader', 'vae_name')}


def recommendation(vram_mb):
    """A starting profile, not a guarantee that a particular GPU can allocate it."""
    if vram_mb is None:
        return {'variant': 'turbo-int8', 'resolution': 768,
                'message': '未能读取目标 GPU 显存，先用量化模型和 768 档；可在高级设置调整。'}
    if vram_mb >= 40 * 1024:
        return {'variant': 'turbo-bf16', 'resolution': 1536, 'message': '大显存建议 BF16；首次先验证一张图片。'}
    if vram_mb >= 12 * 1024:
        return {'variant': 'turbo-int8', 'resolution': 1024, 'message': '建议官方 INT8 模型与 W4A8 文本编码器，按阶段卸载。'}
    return {'variant': 'turbo-int8', 'resolution': 512,
            'message': '显存较小，先用 512 档和量化模型；需要内存卸载，速度与可用性以实测为准。'}


def image_size(ratio, resolution):
    a, b = map(int, ratio.split(':'))
    width = max(64, round(resolution * math.sqrt(a / b) / 32) * 32)
    height = max(64, round(resolution / math.sqrt(a / b) / 32) * 32)
    return width, height


class ImageEnvironment:
    def __init__(self, config):
        self.config = config
        self.root = config.root
        self.manifest = read_json(ROOT / 'manifests/qwen-image-2.1.json')

    def settings(self):
        return ImageSettings.model_validate(self.config.get().get('image_generation', {}))

    def headers(self):
        token = self.config.key('comfy')
        return {'Authorization': 'Bearer ' + token} if token else {}

    def probe(self, url):
        try:
            with httpx.Client(timeout=5, trust_env=False) as client:
                nodes_response = client.get(url + '/object_info', headers=self.headers())
                nodes_response.raise_for_status()
                nodes = nodes_response.json()
                stats_response = client.get(url + '/system_stats', headers=self.headers())
                stats_response.raise_for_status()
                stats = stats_response.json()
            choices = {}
            for category, (node, field) in MODEL_FIELDS.items():
                spec = nodes.get(node, {}).get('input', {}).get('required', {}).get(field, [])
                choices[category] = spec[0] if spec and isinstance(spec[0], list) else spec[1].get('options', []) if len(spec) > 1 else []
            devices = stats.get('devices') or []
            gpu = next((d for d in devices if d.get('type') != 'cpu' and d.get('vram_total')), None)
            return {'connected': True, 'missing_nodes': [n for n in REQUIRED_NODES if n not in nodes],
                    'reference_support': 'LoadImage' in nodes and 'TextEncodeQwenImage21' in nodes,
                    'choices': choices, 'gpu': gpu,
                    'vram_mb': round(gpu['vram_total'] / 1024**2) if gpu else None}
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return {'connected': False, 'missing_nodes': list(REQUIRED_NODES), 'choices': {}, 'gpu': None, 'vram_mb': None}

    def inventory(self, model_root, current, local):
        result = {}
        for category in MODEL_FIELDS:
            found = {name.replace('\\', '/'): {'name': name.replace('\\', '/'), 'source': 'service'}
                     for name in current['choices'].get(category, []) if isinstance(name, str) and name.endswith('.safetensors')}
            folder = model_root / category
            if local and folder.is_dir():
                for path in folder.rglob('*.safetensors'):
                    if path.is_file() and path.resolve().is_relative_to(folder.resolve()):
                        name = path.relative_to(folder).as_posix()
                        found.setdefault(name, {'name': name, 'source': 'folder', 'size': path.stat().st_size})
            result[category] = sorted(found.values(), key=lambda item: item['name'].lower())
        return result

    def plan(self, variant='auto', models=None):
        settings = self.settings()
        env = self.config.renderer_config()
        shared_url = settings.comfy_url or env.get('comfy_url', 'http://127.0.0.1:8188')
        shared = self.probe(shared_url)
        local = urlsplit(shared_url).hostname in ('127.0.0.1', 'localhost', '::1')
        managed = settings.engine == 'managed' or (settings.engine == 'auto' and local and bool(shared['missing_nodes']))
        url = f'http://127.0.0.1:{settings.managed_port}' if managed else shared_url
        current = self.probe(url) if managed else shared
        device = current['gpu']
        vram = current['vram_mb']
        if managed and not current['connected']:
            available = hardware(self.root)
            device = (available.get('gpu') or [None])[0]
            vram = device.get('vram_mb') if device else None
        recommended = recommendation(vram)
        selected = variant if variant != 'auto' else settings.variant if settings.variant != 'auto' else recommended['variant']
        if selected not in self.manifest['variants']:
            raise ValueError('图片模型方案不存在。')
        model_root = Path(settings.models_dir or (self.root / 'models/qwen-image-2.1' if managed else Path(env.get('comfy_dir') or self.root / 'engines/ComfyUI') / 'models')).resolve()
        local_files = managed or (local and bool(settings.models_dir or (shared_url == env.get('comfy_url') and env.get('comfy_dir'))))
        available = self.inventory(model_root, current, local_files)
        selection = ImageModels.model_validate(models).model_dump() if models is not None else settings.models.model_dump()
        main_name = selection['diffusion_models'].rsplit('/', 1)[-1]
        known_variant = next((key for key, spec in self.manifest['variants'].items()
                              if main_name == self.manifest['models'][spec['files'][0]]['name']), None)
        if known_variant:
            if variant != 'auto' and selected != known_variant:
                raise ValueError('所选主模型与采样方案不一致，请选择自动方案或对应的 Turbo／标准方案。')
            selected = known_variant
        rows = []
        selection_errors = []
        for role in self.manifest['variants'][selected]['files']:
            model = self.manifest['models'][role]
            category = model['category']
            chosen = selection[category]
            missing = chosen and chosen not in {item['name'] for item in available[category]}
            if missing:
                selection_errors.append('所选模型文件不存在或尚未被目标服务识别：' + chosen)
            if chosen:
                known = next((m for m in self.manifest['models'].values() if m['category'] == category and m['name'] == chosen.rsplit('/', 1)[-1]), None)
                target = contained(model_root, category + '/' + chosen)
                size = target.stat().st_size if local_files and target.is_file() else 0
                model = {**(known or {}), 'name': chosen, 'category': category,
                         'size': known['size'] if known else size, 'custom': not bool(known)}
            elif local_files:
                # Recommended models may already live in a user-created subfolder.
                existing = next((item['name'] for item in available[category]
                                 if item['name'].rsplit('/', 1)[-1] == model['name']), None)
                if existing:
                    model = {**model, 'name': existing}
            available_name = next((name for name in current['choices'].get(model['category'], [])
                                   if (name.replace('\\', '/') == chosen if chosen else name.replace('\\', '/').split('/')[-1] == model['name'].rsplit('/', 1)[-1])), None)
            target = contained(model_root, model['category'] + '/' + model['name'])
            state = Downloader.verification_status(target, model['size'], model.get('sha256')) if local_files and not model.get('custom') else 'invalid'
            rows.append({**model, 'role': role, 'target': str(target), 'comfy_name': available_name,
                         'action': 'missing' if missing else 'available' if available_name else 'local' if model.get('custom') else 'verified' if state == 'verified' else 'verify' if state == 'unknown' else 'download'})
        disk = model_root
        while not disk.exists():
            disk = disk.parent
        engine_root, source, runtime_python = self.paths()
        base_python = env.get('python')
        bootstrap_needed = managed and not runtime_python.is_file() and (not base_python or not Path(base_python).is_file())
        model_bytes = sum(m['size'] for m in rows if m['action'] == 'download')
        runtime_bytes = self.manifest['bootstrap']['size'] if bootstrap_needed else 0
        source_needed = managed and not current['connected'] and (not (source / 'main.py').is_file() or read_json(engine_root / 'source-ready.json', {}).get('revision') != self.manifest['comfyui']['revision'])
        source_bytes = self.manifest['comfyui']['size'] if source_needed else 0
        ready = current['connected'] and not current['missing_nodes'] and all(m['comfy_name'] for m in rows)
        requires_confirmation = not ready and (model_bytes > 0 or bootstrap_needed or source_needed)
        token = digest({'url': url, 'variant': selected, 'directory': str(model_root), 'revision': self.manifest['comfyui']['revision'],
                        'models': [{k: m.get(k) for k in ('name', 'category', 'sha256', 'size')} for m in rows],
                        'downloads': [m['target'] for m in rows if m['action'] == 'download'],
                        'bootstrap_needed': bootstrap_needed, 'source_needed': source_needed})
        return {'engine': 'managed' if managed else 'shared', 'comfy_url': url,
                'connected': current['connected'], 'missing_nodes': current['missing_nodes'],
                'reference_support': current.get('reference_support', False),
                'gpu': device, 'vram_mb': vram, 'recommendation': recommended, 'variant': selected,
                'variants': self.manifest['variants'], 'models': rows, 'models_dir': str(model_root),
                'download_bytes': model_bytes + runtime_bytes + source_bytes, 'models_download_bytes': model_bytes,
                'runtime_download_bytes': runtime_bytes, 'bootstrap_needed': bootstrap_needed,
                'source_download_bytes': source_bytes, 'available_models': available, 'selection': selection,
                'selection_errors': selection_errors, 'verify_bytes': sum(m['size'] for m in rows if m['action'] == 'verify'),
                'requires_confirmation': requires_confirmation, 'confirmation_token': token,
                'engine_free_disk_bytes': shutil.disk_usage(self.root).free,
                'free_disk_bytes': shutil.disk_usage(disk).free,
                'ready': ready,
                'local_download': local_files,
                'license': self.manifest['license'], 'auto_download': settings.auto_download}

    def prepare(self, variant, report, cancel, models=None, confirmation=''):
        plan = self.plan(variant, models)
        if plan['ready']:
            return plan
        if plan['selection_errors']:
            raise ValueError('；'.join(plan['selection_errors']))
        if plan['requires_confirmation'] and confirmation != plan['confirmation_token']:
            report('请先确认图片模型下载。', download_required=True, download_plan=plan)
            raise DownloadConfirmationRequired(plan)
        if plan['engine'] == 'managed' and not plan['connected'] and not plan['gpu']:
            raise RuntimeError('未检测到可用的 NVIDIA 显卡。请检查驱动和显卡坞连接，或配置已有的远程图片服务。')
        if not plan['local_download']:
            raise RuntimeError('目标图片服务缺少节点或模型。本机的独立地址需填写实际模型目录；远程服务请在远端安装清单内模型。')
        if plan['engine'] == 'shared' and plan['missing_nodes']:
            raise RuntimeError('当前服务不支持 Qwen-Image 2.1；请选择自动或独立图片引擎，或升级该服务。')
        if plan['free_disk_bytes'] < plan['models_download_bytes'] + 1024**3:
            raise RuntimeError('图片模型目录空间不足，请更换目录或腾出空间（含环境预留空间）。')
        if plan['engine'] == 'managed' and plan['engine_free_disk_bytes'] < plan['runtime_download_bytes'] + (10 if plan['bootstrap_needed'] else 2) * 1024**3:
            raise RuntimeError('应用所在磁盘不足以准备图片引擎，请先腾出运行环境与解压空间。')
        downloader = Downloader(self.config.get().get('proxy', ''))
        # Local verification never implies permission to download replacement files.
        for model in plan['models']:
            if model['action'] != 'verify':
                continue
            report('正在校验本地模型：' + model['name'],
                   progress={'status': 'verifying', 'file': model['name']})
            if not downloader.verified(model['target'], model['size'], model['sha256'], cancel):
                revised = self.plan(variant, models)
                report('本地模型校验失败，请确认修复下载后继续。', download_required=True, download_plan=revised, progress={})
                raise DownloadConfirmationRequired(revised)
        for model in plan['models']:
            if cancel():
                raise Cancelled('图片环境准备已停止，下载可以恢复。')
            if model['action'] in ('available', 'local', 'verified', 'verify'):
                continue
            report('正在准备图片模型：' + model['name'], file=model['name'])
            downloader.fetch(model['url'], model['target'], model['size'], model['sha256'],
                             lambda info: report('图片模型 ' + info.get('status', ''), progress=info), cancel, self.config.key('hf'))
        if plan['engine'] == 'managed':
            self.prepare_engine(plan, downloader, report, cancel)
            self.start_engine(plan, report, cancel)
        result = self.plan(plan['variant'], plan['selection'])
        if not result['ready']:
            raise RuntimeError('模型已保存，但图片服务尚未识别这些文件。检查模型目录映射或重启图片服务后继续。')
        return result

    def paths(self):
        revision = self.manifest['comfyui']['revision']
        engine_root = self.root / 'engines' / ('qwen-comfy-' + revision[:12])
        source = engine_root / self.manifest['comfyui']['folder']
        python = engine_root / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        bootstrap = engine_root / 'bootstrap' / self.manifest['bootstrap']['folder'] / 'python_embeded/python.exe'
        if not python.is_file() and bootstrap.is_file() and (engine_root / 'bootstrap-ready.json').is_file():
            python = bootstrap
        return engine_root, source, python

    def prepare_engine(self, plan, downloader, report, cancel):
        engine_root, source, python = self.paths()
        info = self.manifest['comfyui']
        engine_root.mkdir(parents=True, exist_ok=True)
        archive = self.root / 'data/downloads' / ('qwen-comfy-' + info['revision'] + '.zip')
        if not (source / 'main.py').is_file() or read_json(engine_root / 'source-ready.json', {}).get('revision') != info['revision']:
            downloader.fetch(info['url'], archive, info['size'], info['sha256'],
                             lambda value: report('正在下载图片引擎源码', progress=value), cancel)
            with zipfile.ZipFile(archive) as zipped:
                for entry in zipped.infolist():
                    contained(engine_root, entry.filename)
                    if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise RuntimeError('引擎压缩包含不支持的符号链接。')
                zipped.extractall(engine_root)
            write_json(engine_root / 'source-ready.json', {'revision': info['revision']})
        process_env = os.environ.copy()
        temporary = self.root / 'data/image-engine-temp'
        temporary.mkdir(parents=True, exist_ok=True)
        for name in ('TEMP', 'TMP', 'TMPDIR'):
            process_env[name] = str(temporary)
        process_env['PIP_CACHE_DIR'] = str(self.root / 'data/pip-cache')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        logdir = self.root / 'logs'
        logdir.mkdir(exist_ok=True)
        with (logdir / 'image-engine-install.log').open('ab') as log:
            if not python.is_file():
                base_python = self.config.renderer_config().get('python', '')
                if not base_python or not Path(base_python).is_file():
                    if os.name != 'nt':
                        raise RuntimeError('自动准备 GPU 运行时目前面向 Windows；其他系统请配置现有推理 Python 或兼容远程服务。')
                    bootstrap = self.manifest['bootstrap']
                    portable = self.root / 'data/downloads' / bootstrap['name']
                    downloader.fetch(bootstrap['url'], portable, bootstrap['size'], bootstrap['sha256'],
                                     lambda value: report('正在下载独立 GPU 运行时', progress=value), cancel)
                    stage = engine_root / 'bootstrap'
                    stage.mkdir(exist_ok=True)
                    extract_portable(portable, stage, lambda value: report(value.get('message', '正在解压图片运行时'), progress=value), cancel)
                    python = stage / bootstrap['folder'] / 'python_embeded/python.exe'
                    if not python.is_file():
                        raise RuntimeError('官方 GPU 运行时解压结果不完整。')
                    for config_path in python.parent.glob('python*._pth'):
                        zipped_library = next(python.parent.glob('python*.zip'))
                        config_path.write_text(zipped_library.name + '\n.\nLib/site-packages\n' + str(source) + '\nimport site\n', encoding='utf-8')
                    write_json(engine_root / 'bootstrap-ready.json', {'sha256': bootstrap['sha256']})
                else:
                    report('正在建立独立图片 Python 环境，复用现有 PyTorch。')
                    result = run_process([base_python, '-m', 'venv', '--system-site-packages', str(engine_root / 'venv')],
                                         stdout=log, stderr=subprocess.STDOUT, env=process_env, creationflags=flags, cancel=cancel)
                    if result.returncode:
                        raise RuntimeError('无法建立图片 Python 环境，请检查 logs/image-engine-install.log。')
            receipt = engine_root / 'installed.json'
            if read_json(receipt, {}).get('revision') != info['revision']:
                report('正在安装图片引擎依赖，详细记录见 image-engine-install.log。')
                result = run_process([str(python), '-m', 'pip', 'install', '-r', str(source / 'requirements.txt'), '--disable-pip-version-check'],
                                     stdout=log, stderr=subprocess.STDOUT, env=process_env, creationflags=flags, cancel=cancel)
                if result.returncode:
                    raise RuntimeError('图片引擎依赖安装失败，请检查 logs/image-engine-install.log 后继续。')
                write_json(receipt, {'revision': info['revision'], 'base_python': self.config.renderer_config().get('python')})
        import yaml
        paths = {category: str(Path(plan['models_dir']) / category) for category in MODEL_FIELDS}
        (engine_root / 'model_paths.yaml').write_text(yaml.safe_dump({'image_studio': {'base_path': plan['models_dir'], **paths}}, allow_unicode=True), encoding='utf-8')

    def start_engine(self, plan, report, cancel):
        if self.probe(plan['comfy_url'])['connected']:
            return
        engine_root, source, python = self.paths()
        port = urlsplit(plan['comfy_url']).port
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('图片引擎端口已占用但不是可用的 ComfyUI，请在图片设置中换一个端口。')
        runtime = self.root / 'data/image-comfy-runtime'
        for name in ('input', 'output', 'temp', 'user'):
            (runtime / name).mkdir(parents=True, exist_ok=True)
        args = [str(python), '-u', str(source / 'main.py'), '--listen', '127.0.0.1', '--port', str(port),
                '--disable-auto-launch', '--disable-api-nodes', '--disable-all-custom-nodes',
                '--reserve-vram', '1', '--extra-model-paths-config', str(engine_root / 'model_paths.yaml')]
        for name in ('input', 'output', 'temp', 'user'):
            args += ['--' + name + '-directory', str(runtime / name)]
        args += ['--database-url', 'sqlite:///' + (runtime / 'user/comfyui.db').as_posix()]
        report('模型已就绪，正在启动独立图片引擎，首次启动可能需要一两分钟。', progress={})
        with (self.root / 'logs/image-engine.log').open('ab') as log:
            process = subprocess.Popen(args, cwd=source, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        write_json(engine_root / 'process.json', {'pid': process.pid, 'port': port, 'python': str(python)})
        started = time.monotonic()
        until = started + 120
        last_report = started
        while time.monotonic() < until:
            if cancel():
                process.terminate()
                process.wait(timeout=15)
                raise Cancelled('图片引擎启动已停止。')
            if process.poll() is not None:
                raise RuntimeError('图片引擎启动失败，请查看 logs/image-engine.log。')
            if self.probe(plan['comfy_url'])['connected']:
                return
            if time.monotonic() - last_report >= 5:
                report(f'模型已就绪，图片引擎启动中（已等待 {int(time.monotonic() - started)} 秒），无需下载。', progress={})
                last_report = time.monotonic()
            time.sleep(1)
        raise RuntimeError('图片引擎仍未就绪，请检查日志后继续；不会重复启动占用端口的进程。')
