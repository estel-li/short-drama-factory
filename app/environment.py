from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import psutil
import yaml

from .downloads import Downloader
from .providers import Cancelled
from .storage import ROOT, contained, identifier, read_json, write_json

REQUIRED_NODES = ['MiniMaxH3ImageToVideo', 'MiniMaxH3ReferenceToVideo', 'EmptyMiniMaxH3LatentAV',
                  'DramaSaveConditioning', 'DramaLoadConditioning', 'DramaSaveLatent', 'DramaLoadLatent']
MODEL_FIELDS = {'fl_model': ('UNETLoader', 'unet_name'), 'ref_model': ('UNETLoader', 'unet_name'),
                'text_encoder': ('CLIPLoader', 'clip_name'), 'video_vae': ('VAELoader', 'vae_name'),
                'audio_vae': ('VAELoader', 'vae_name'), 'fl_lora': ('LoraLoaderModelOnly', 'lora_name'),
                'ref_lora': ('LoraLoaderModelOnly', 'lora_name'), 'attention': ('ModelAttentionBackend', 'attention')}


def extract_portable(archive, stage, progress, cancel):
    executable = ROOT / 'tools/7zr.exe'
    provenance = read_json(ROOT / 'tools/7zip-source.json')
    if not executable.is_file() or not provenance or Downloader.checksum(executable) != provenance['sha256']:
        raise RuntimeError('随应用提供的官方 7-Zip 工具缺失或校验失败。')
    flags = 0x08000000 if os.name == 'nt' else 0
    listing = subprocess.run([str(executable), 'l', '-slt', str(archive)], capture_output=True, text=True,
                             encoding='utf-8', errors='replace', creationflags=flags, timeout=60)
    if listing.returncode:
        raise RuntimeError('无法读取 ComfyUI 便携包目录。')
    entries = listing.stdout.split('----------', 1)[-1]
    expanded = 0
    for line in entries.splitlines():
        if line.startswith('Path = '):
            contained(stage, line[7:])
        elif line.startswith('Size = '):
            expanded += int(line[7:])
        elif line.startswith(('Symbolic Link = ', 'Hard Link = ')):
            raise RuntimeError('安装压缩包包含不支持的链接条目。')
    if shutil.disk_usage(stage).free < expanded:
        raise RuntimeError('ComfyUI 安装磁盘没有足够的解压空间。')
    log = stage / 'extraction.log'
    with log.open('wb') as errors:
        process = subprocess.Popen([str(executable), 'x', str(archive), '-o' + str(stage), '-y', '-bso0', '-bsp0', '-bse1'],
            stdout=subprocess.DEVNULL, stderr=errors, creationflags=flags)
        started, last = time.monotonic(), 0
        while process.poll() is None:
            if cancel():
                process.terminate()
                process.wait(timeout=20)
                raise Cancelled('解压已停止，已下载的压缩包会保留。再次安装将重新解压。')
            if time.monotonic() - last >= 5:
                progress({'status': 'extracting', 'message': f'正在解压 ComfyUI，已用 {int(time.monotonic()-started)} 秒。', 'expanded_bytes': expanded})
                last = time.monotonic()
            time.sleep(0.5)
    if process.returncode:
        raise RuntimeError('ComfyUI 解压失败，请查看安装目录中的 extraction.log。')


def catalog(config):
    headers = {'Authorization': 'Bearer ' + config['comfy_auth_token']} if config.get('comfy_auth_token') else {}
    try:
        response = httpx.get(config['comfy_url'] + '/object_info', headers=headers, timeout=30)
        response.raise_for_status()
        nodes = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError('ComfyUI 无法连接，暂时不能获取节点与模型列表。') from exc
    choices = {}
    for name, (node, field) in MODEL_FIELDS.items():
        spec = nodes.get(node, {}).get('input', {}).get('required', {}).get(field)
        choices[name] = spec[0] if spec and isinstance(spec[0], list) else spec[1].get('options', []) if spec and len(spec) > 1 else []
    try:
        capability = httpx.get(config['comfy_url'] + '/drama/capabilities', headers=headers, timeout=10)
        cache_protocol = capability.json().get('cache_protocol', 0) if capability.is_success else 0
    except (httpx.HTTPError, ValueError):
        cache_protocol = 0
    return {'models': choices, 'missing_nodes': [n for n in REQUIRED_NODES if n not in nodes], 'cache_protocol': cache_protocol,
            'configured_missing': [name for name in MODEL_FIELDS if config.get(name) and config[name] not in choices[name]]}


def hardware(path=ROOT):
    existing = Path(path).resolve()
    while not existing.exists():
        existing = existing.parent
    gpu = []
    try:
        output = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version,compute_cap', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000 if os.name == 'nt' else 0)
        if output.returncode == 0:
            for line in output.stdout.splitlines():
                name, memory, driver, capability = [v.strip() for v in line.split(',')]
                gpu.append({'name': name, 'vram_mb': int(memory), 'driver': driver, 'compute_capability': capability})
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return {'os': platform.system(), 'architecture': platform.machine(), 'gpu': gpu,
            'ram_bytes': psutil.virtual_memory().total, 'free_disk_bytes': shutil.disk_usage(existing).free}


def inspect_safetensors(path):
    size = path.stat().st_size
    with path.open('rb') as source:
        length = int.from_bytes(source.read(8), 'little')
        if not 2 <= length <= min(size - 8, 32_000_000):
            raise RuntimeError('本地模型不是完整的 safetensors 文件：' + path.name)
        header = json.loads(source.read(length))
    tensors = {k: v for k, v in header.items() if k != '__metadata__'}
    if not tensors:
        raise RuntimeError('本地模型没有张量数据：' + path.name)
    payload = size - length - 8
    for tensor in tensors.values():
        start, end = tensor['data_offsets']
        if not 0 <= start <= end <= payload or any(not isinstance(n, int) or n < 0 for n in tensor['shape']):
            raise RuntimeError('本地模型数据范围不完整：' + path.name)
    return {'tensor_count': len(tensors), 'size': size, 'metadata': header.get('__metadata__', {})}


class Installer:
    def __init__(self, config):
        self.config = config

    def manifests(self):
        return [read_json(p) for p in (ROOT / 'manifests').glob('*.json')]

    def manifest(self, mid='h3-5060ti-16g'):
        value = read_json(ROOT / 'manifests' / (identifier(mid) + '.json'))
        if not value:
            raise ValueError('安装清单不存在。')
        return value

    def discover(self, roots):
        files = {}
        for root in roots:
            if not Path(root).is_dir():
                continue
            for current, dirs, names in os.walk(root, followlinks=False):
                dirs[:] = [d for d in dirs if d not in ('.git', '.venv', '__pycache__', 'node_modules')]
                for name in names:
                    if name.endswith('.safetensors'):
                        files.setdefault(name, []).append(str(Path(current) / name))
        return files

    def plan(self, options):
        manifest = self.manifest(options.get('manifest', 'h3-5060ti-16g'))
        env = self.config.renderer_config()
        env.update({key: options[key] for key in ('comfy_dir', 'python', 'comfy_url') if options.get(key)})
        mode = options.get('mode', env.get('mode', 'existing'))
        if mode not in ('existing', 'fresh', 'remote'):
            raise ValueError('安装方式不支持。')
        install_dir = Path(options.get('install_dir') or ROOT / 'engines').resolve()
        models_dir = Path(options.get('models_dir') or ROOT / 'models').resolve()
        roots = options.get('model_search_dirs', [])
        if mode == 'existing' and env.get('comfy_dir'):
            roots = [str(Path(env['comfy_dir']) / 'models'), *roots]
            legacy_paths = self.config.root / 'extra_model_paths.yaml'
            if legacy_paths.exists():
                for group in (yaml.safe_load(legacy_paths.read_text(encoding='utf-8')) or {}).values():
                    if isinstance(group, dict) and group.get('base_path'):
                        roots.append(group['base_path'])
        roots = list(dict.fromkeys([str(models_dir), *map(str, roots)]))
        files = self.discover(roots) if mode != 'remote' else {}
        planned = []
        for model in manifest['models']:
            choices = files.get(model['name'], [])
            preferred = Path(env.get(model['role'], '')).name if mode == 'existing' else ''
            existing = files.get(preferred, []) or choices
            planned.append({**model, 'existing': existing[0] if existing else None,
                'target': str(contained(models_dir, model['category'] + '/' + model['name'])),
                'action': 'reuse' if existing else 'download'})
        portable = next(a for a in manifest['comfyui']['portable_assets'] if a['name'] == 'ComfyUI_windows_portable_nvidia.7z')
        wheels = manifest.get('runtime_wheels', []) if mode == 'fresh' else []
        needed = sum(m['size'] for m in planned if m['action'] == 'download') + (portable['size'] if mode == 'fresh' else 0) + sum(w['size'] for w in wheels)
        if mode == 'remote':
            planned, needed = [], 0
        return {'mode': mode, 'install_dir': str(install_dir), 'models_dir': str(models_dir), 'search_dirs': roots,
                'manifest': manifest['id'], 'models': planned, 'portable': portable, 'runtime_wheels': wheels, 'download_bytes': needed,
                'hardware': hardware(models_dir), 'note': '便携包解压还需额外空间。复用文件会进行校验；已配置的不同量化版本可保留。'}

    def execute(self, options, progress, cancel):
        plan = self.plan(options)
        if plan['mode'] == 'remote':
            return catalog({**self.config.renderer_config(), 'comfy_url': options.get('comfy_url') or self.config.renderer_config()['comfy_url'], 'comfy_auth_token': self.config.key('comfy')})
        if plan['hardware']['os'] != 'Windows' or plan['hardware']['architecture'].lower() not in ('amd64', 'x86_64') or not plan['hardware']['gpu']:
            raise RuntimeError('从零安装目前支持 Windows x64 + NVIDIA。可改为连接已有或远程 ComfyUI。')
        if plan['hardware']['free_disk_bytes'] < plan['download_bytes']:
            raise RuntimeError('模型目标磁盘空间不足。')
        downloader = Downloader(self.config.get().get('proxy', ''))
        env = self.config.renderer_config()
        env.update({key: options[key] for key in ('comfy_dir', 'python', 'comfy_url') if options.get(key)})
        if plan['mode'] == 'fresh':
            install_root = Path(plan['install_dir'])
            install_root.mkdir(parents=True, exist_ok=True)
            final_root = contained(install_root, 'ComfyUI_windows_portable')
            if not (final_root / 'ComfyUI/main.py').exists():
                artifact = plan['portable']
                archive = ROOT / 'data/downloads' / artifact['name']
                downloader.fetch(artifact['url'], archive, artifact['size'], artifact['digest'].split(':')[1], progress, cancel)
                stage = contained(install_root, '.install-' + uuid.uuid4().hex)
                stage.mkdir()
                progress({'status': 'extracting', 'message': '正在解压官方 ComfyUI 便携包。'})
                extract_portable(archive, stage, progress, cancel)
                if cancel():
                    raise Cancelled('解压已完成，安装已停止，可再次继续。')
                extracted = contained(stage, 'ComfyUI_windows_portable')
                if not (extracted / 'ComfyUI/main.py').is_file():
                    raise RuntimeError('便携包目录结构与固定安装清单不一致。')
                if final_root.exists():
                    backup = contained(install_root, 'ComfyUI_windows_portable.before-install-' + str(time.time_ns()))
                    final_root.rename(backup)
                extracted.rename(final_root)
            env.update(comfy_dir=str(final_root / 'ComfyUI'), python=str(final_root / 'python_embeded/python.exe'),
                       comfy_url=options.get('comfy_url') or 'http://127.0.0.1:8188', mode='existing',
                       **self.manifest(plan['manifest']).get('startup', {}))
            if plan['runtime_wheels']:
                packages = {w['package']: w['version'] for w in plan['runtime_wheels']}
                check = subprocess.run([env['python'], '-c', 'import importlib.metadata as m,json; print(json.dumps({n:m.version(n) for n in '+repr(list(packages))+'}))'],
                    capture_output=True, text=True, timeout=30, creationflags=0x08000000)
                versions = json.loads(check.stdout) if check.returncode == 0 else {}
                if versions != packages:
                    local_wheels = []
                    for wheel in plan['runtime_wheels']:
                        path = ROOT / 'data/downloads/wheels' / wheel['name']
                        downloader.fetch(wheel['url'], path, wheel['size'], wheel['sha256'], progress, cancel)
                        local_wheels.append(str(path))
                    progress({'status': 'installing-runtime', 'message': '正在安装已固定版本的 PyTorch CUDA 运行依赖。'})
                    log_dir = self.config.root / 'logs'
                    log_dir.mkdir(parents=True, exist_ok=True)
                    with (log_dir / 'torch_install.log').open('wb') as log:
                        process = subprocess.Popen([env['python'], '-m', 'pip', 'install', '--no-deps', '--no-index', '--force-reinstall', *local_wheels],
                            stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000)
                        while process.poll() is None:
                            time.sleep(0.5)
                        if process.returncode:
                            raise RuntimeError('PyTorch 安装失败，请查看 logs/torch_install.log。')
        if not Path(env.get('comfy_dir', '')).joinpath('main.py').is_file() or not Path(env.get('python', '')).is_file():
            raise RuntimeError('ComfyUI 或推理 Python 路径不正确。')
        used = {}
        for model in plan['models']:
            if cancel():
                raise Cancelled('安装已停止，文件和下载进度已保留。')
            path = Path(model['existing']) if model['existing'] else Path(model['target'])
            if model['existing']:
                progress({'status': 'verifying', 'message': '检查已有模型：' + path.name})
                actual = downloader.checksum(path, cancel)
                if path.name == model['name'] and (path.stat().st_size != model['size'] or actual != model['sha256']):
                    if options.get('strict_models', False):
                        raise RuntimeError('已有同名模型与固定清单不同：' + path.name + '。关闭严格版本校验以复用本地版本，或指定新的模型目录下载清单版本。')
                    inspect_safetensors(path)
                    progress({'status': 'reused-local-variant', 'message': '保留本地模型版本：' + path.name, 'sha256': actual})
            else:
                url = f'https://huggingface.co/{model["repo"]}/resolve/{model["revision"]}/{model["filename"]}'
                path = downloader.fetch(url, path, model['size'], model['sha256'], progress, cancel, self.config.key('hf'))
                actual = model['sha256']
            used[model['role']] = {'path': str(path), 'sha256': actual, 'category': model['category'],
                                  'source': 'manifest' if actual == model['sha256'] else 'user-local-variant'}
            env[model['role']] = path.name
        node_target = contained(Path(env['comfy_dir']) / 'custom_nodes', 'ComfyUI-DramaFactory')
        node_source = ROOT / 'nodes/ComfyUI-DramaFactory'
        if node_target.exists():
            shutil.copytree(node_target, self.config.root / 'data/backups' / ('nodes-' + str(time.time_ns())))
        shutil.copytree(node_source, node_target, dirs_exist_ok=True)
        extra = {}
        for model in used.values():
            extra.setdefault(model['category'], set()).add(str(Path(model['path']).parent))
        mapping = {'drama_factory_models': {'base_path': plan['models_dir'], **{k: '\n'.join(sorted(v)) for k, v in extra.items()}}}
        extra_path = self.config.root / 'extra_model_paths.yaml'
        original_mapping = yaml.safe_load(extra_path.read_text(encoding='utf-8')) if extra_path.exists() else {}
        if extra_path.exists():
            shutil.copy2(extra_path, extra_path.with_name('extra_model_paths.backup-' + str(time.time_ns()) + '.yaml'))
        extra_path.write_text(yaml.safe_dump({**(original_mapping or {}), **mapping}, allow_unicode=True, sort_keys=False), encoding='utf-8')
        env['extra_model_paths_file'] = str(extra_path)
        value = self.config.get()
        write_json(self.config.root / 'config' / ('before-install-' + str(time.time_ns()) + '.json'), value)
        value.update(environment=env, setup_complete=True)
        self.config.save(value)
        receipt = {'manifest': plan['manifest'], 'environment': env, 'models': used, 'completed_at': time.strftime('%Y-%m-%d %H:%M:%S')}
        write_json(self.config.root / 'data/installation.json', receipt)
        if plan['mode'] == 'fresh':
            import pipeline
            pipeline.CONFIG.clear()
            pipeline.CONFIG.update(env)
            pipeline.ensure_comfy(lambda message: progress({'status': 'verifying', 'message': message}))
            receipt['catalog'] = catalog(env)
            if receipt['catalog']['missing_nodes'] or receipt['catalog']['configured_missing']:
                raise RuntimeError('文件安装完成，但实时模型或节点检查未通过，请检查安装日志。')
            write_json(self.config.root / 'data/installation.json', receipt)
            progress({'status': 'complete', 'message': '安装完成，生成引擎已启动，节点与模型检查通过。可运行 4 秒验证样片。'})
        else:
            progress({'status': 'complete', 'message': '文件安装完成。若生成引擎已在运行，请重启它加载更新，再运行验证样片。'})
        return receipt
