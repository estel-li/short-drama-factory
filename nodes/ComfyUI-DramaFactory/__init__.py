"""Local tensor-only conditioning cache for staged H3 generation."""

import json
import os
import asyncio
import hashlib
import threading
import uuid
from pathlib import Path

import safetensors.torch
import torch
import folder_paths
import comfy.nested_tensor
from aiohttp import web
from server import PromptServer


def enable_windows_read_fallback():
    """Keep ComfyUI's own mmap/copy path available when aimdo's Windows IO fails."""
    import os
    import logging
    import functools
    import comfy.memory_management
    if os.name != 'nt' or os.environ.get('DRAMA_SAFE_FILE_READ') != '1':
        return
    module = comfy.memory_management
    original = module.read_tensor_file_slice_into
    if getattr(original, '_drama_compatible', False):
        return
    failed = False

    @functools.wraps(original)
    def compatible_read(*args, **kwargs):
        nonlocal failed
        if failed:
            return False
        try:
            return original(*args, **kwargs)
        except RuntimeError as exc:
            if 'hostbuf_file_reader_read failed' not in str(exc):
                raise
            failed = True
            logging.warning('DramaFactory: Windows file-to-device read failed; using ComfyUI native mmap/copy fallback for this process.')
            return False
    compatible_read._drama_compatible = True
    module.read_tensor_file_slice_into = compatible_read


enable_windows_read_fallback()

MODEL_INDEX_LOCK = threading.Lock()


def model_file_info(category, filename):
    if category not in ('diffusion_models', 'text_encoders', 'vae', 'loras') or filename not in folder_paths.get_filename_list(category):
        raise ValueError('Unknown model file.')
    path = Path(folder_paths.get_full_path(category, filename))
    stat = path.stat()
    index_path = Path(os.environ['DRAMA_FACTORY_CACHE_DIR']) / 'model_index.json' if os.environ.get('DRAMA_FACTORY_CACHE_DIR') else Path(folder_paths.get_user_directory()) / 'default/drama_model_index.json'
    with MODEL_INDEX_LOCK:
        index = json.loads(index_path.read_text()) if index_path.exists() else {}
        record = index.get(str(path), {})
        if record.get('size') != stat.st_size or record.get('mtime_ns') != stat.st_mtime_ns:
            checksum = hashlib.sha256()
            with path.open('rb') as source:
                while block := source.read(4 * 1024 * 1024):
                    checksum.update(block)
            record = {'category': category, 'name': filename, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': checksum.hexdigest()}
            index[str(path)] = record
            index_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = index_path.with_name(index_path.name + '.' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(json.dumps(index), encoding='utf-8')
            temporary.replace(index_path)
    return {k: record[k] for k in ('category', 'name', 'size', 'sha256')}


@PromptServer.instance.routes.get('/drama/model-info')
async def drama_model_info(request):
    try:
        value = await asyncio.to_thread(model_file_info, request.query.get('category'), request.query.get('filename'))
        return web.json_response(value)
    except ValueError:
        return web.json_response({'error': 'Unknown model file.'}, status=400)


@PromptServer.instance.routes.get('/drama/capabilities')
async def drama_capabilities(request):
    return web.json_response({'cache_protocol': 2})


@PromptServer.instance.routes.get('/drama/cache')
async def drama_cache_status(request):
    category = request.query.get('category')
    filename = request.query.get('filename', '')
    try:
        if category == 'conditioning' and filename.startswith('drama/'):
            path = cache_path(filename)
        elif category == 'latent':
            path = latent_path(filename)
        else:
            return web.json_response({'error': 'Unsupported cache category.'}, status=400)
        return web.json_response({'exists': path.is_file(), 'size': path.stat().st_size if path.is_file() else 0})
    except ValueError:
        return web.json_response({'error': 'Invalid cache path.'}, status=400)


def cache_path(name):
    root = Path(os.environ['DRAMA_FACTORY_CACHE_DIR']) / 'conditioning' if os.environ.get('DRAMA_FACTORY_CACHE_DIR') else Path(folder_paths.models_dir) / 'embeddings'
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or target.suffix != '.safetensors':
        raise ValueError('Conditioning cache must be a safetensors file inside the configured cache directory.')
    return target


class DramaSaveConditioning:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'conditioning': ('CONDITIONING',), 'filename': ('STRING', {'default': 'drama/shot.safetensors'})}}

    RETURN_TYPES = ('STRING',)
    FUNCTION = 'save'
    CATEGORY = '短剧工厂/内存优化'
    OUTPUT_NODE = True

    def save(self, conditioning, filename):
        tensors = {}

        def pack(value):
            if isinstance(value, torch.Tensor):
                key = f't{len(tensors)}'
                tensors[key] = value.detach().to('cpu', copy=True).contiguous()
                return {'tensor': key}
            if isinstance(value, dict):
                return {'dict': [[key, pack(item)] for key, item in value.items()]}
            if isinstance(value, (tuple, list)):
                return {'tuple' if isinstance(value, tuple) else 'list': [pack(item) for item in value]}
            if value is None or isinstance(value, (str, int, float, bool)):
                return {'value': value}
            raise TypeError(f'Unsupported conditioning value: {type(value).__name__}')

        tree = pack(conditioning)
        path = cache_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        safetensors.torch.save_file(tensors, str(temp), metadata={'drama_conditioning': json.dumps(tree)})
        temp.replace(path)
        return {'ui': {'conditioning_files': [{'filename': filename}]}, 'result': (filename,)}


class DramaLoadConditioning:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'filename': ('STRING', {'default': 'drama/shot.safetensors'})}}

    RETURN_TYPES = ('CONDITIONING',)
    FUNCTION = 'load'
    CATEGORY = '短剧工厂/内存优化'

    def load(self, filename):
        path = cache_path(filename)
        with safetensors.safe_open(str(path), framework='pt', device='cpu') as handle:
            tree = json.loads(handle.metadata()['drama_conditioning'])

            def unpack(value):
                if 'tensor' in value:
                    return handle.get_tensor(value['tensor'])
                if 'dict' in value:
                    return {key: unpack(item) for key, item in value['dict']}
                if 'tuple' in value:
                    return tuple(unpack(item) for item in value['tuple'])
                if 'list' in value:
                    return [unpack(item) for item in value['list']]
                return value['value']

            return (unpack(tree),)

    @classmethod
    def IS_CHANGED(cls, filename):
        return cache_path(filename).stat().st_mtime_ns


def latent_path(filename):
    root = Path(os.environ['DRAMA_FACTORY_CACHE_DIR']) / 'latents' if os.environ.get('DRAMA_FACTORY_CACHE_DIR') else Path(folder_paths.get_output_directory()) / 'drama_latents'
    path = (root / filename).resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix != '.safetensors':
        raise ValueError('Invalid latent cache filename.')
    return path


class DramaSaveLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'samples': ('LATENT',), 'filename': ('STRING', {'default': 'drama/shot.safetensors'})}}

    RETURN_TYPES = ('STRING',)
    FUNCTION = 'save'
    CATEGORY = '短剧工厂/内存优化'
    OUTPUT_NODE = True

    def save(self, samples, filename):
        video, audio = samples['samples'].unbind()
        target = latent_path(filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix('.tmp')
        safetensors.torch.save_file({'video': video.detach().to('cpu', copy=True).contiguous(),
                                    'audio': audio.detach().to('cpu', copy=True).contiguous()}, str(temp))
        temp.replace(target)
        return {'ui': {'latent_files': [{'filename': filename}]}, 'result': (filename,)}


class DramaLoadLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'filename': ('STRING', {'default': 'drama/shot.safetensors'})}}

    RETURN_TYPES = ('LATENT',)
    FUNCTION = 'load'
    CATEGORY = '短剧工厂/内存优化'

    def load(self, filename):
        tensors = safetensors.torch.load_file(str(latent_path(filename)))
        return ({'samples': comfy.nested_tensor.NestedTensor((tensors['video'], tensors['audio']))},)

    @classmethod
    def IS_CHANGED(cls, filename):
        return latent_path(filename).stat().st_mtime_ns


NODE_CLASS_MAPPINGS = {'DramaSaveConditioning': DramaSaveConditioning, 'DramaLoadConditioning': DramaLoadConditioning,
                       'DramaSaveLatent': DramaSaveLatent, 'DramaLoadLatent': DramaLoadLatent}
NODE_DISPLAY_NAME_MAPPINGS = {'DramaSaveConditioning': '短剧 · 保存H3条件（释放编码器）', 'DramaLoadConditioning': '短剧 · 加载H3条件',
                              'DramaSaveLatent': '短剧 · 保存音画潜空间', 'DramaLoadLatent': '短剧 · 加载音画潜空间'}
