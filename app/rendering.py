from __future__ import annotations

from pathlib import Path

import requests
import yaml

from .downloads import Downloader
from .storage import ROOT, digest, read_json, write_json

ROLES = {'fl_model': 'diffusion_models', 'ref_model': 'diffusion_models', 'text_encoder': 'text_encoders',
         'video_vae': 'vae', 'audio_vae': 'vae', 'fl_lora': 'loras', 'ref_lora': 'loras'}


def fingerprint_models(config, report, cancel):
    index_path = ROOT / 'data/model_versions.json'
    index = read_json(index_path, {})
    result = {}
    headers = {'Authorization': 'Bearer ' + config['comfy_auth_token']} if config.get('comfy_auth_token') else {}
    for role, category in ROLES.items():
        name = config[role]
        report('核对模型版本：' + name)
        if config.get('mode') == 'remote':
            response = requests.get(config['comfy_url'] + '/drama/model-info', params={'category': category, 'filename': name}, headers=headers, timeout=(20, 600))
            if not response.ok:
                raise RuntimeError('远程服务需更新随包提供的短剧缓存节点，以读取模型版本。')
            result[role] = response.json()
            continue
        try:
            response = requests.get(config['comfy_url'] + '/drama/model-info', params={'category': category, 'filename': name}, headers=headers, timeout=(3, 600))
            if response.ok:
                result[role] = response.json()
                continue
        except requests.RequestException:
            pass
        roots = [Path(config['comfy_dir']) / 'models' / category]
        extra_path = Path(config.get('extra_model_paths_file') or ROOT / 'extra_model_paths.yaml')
        if extra_path.is_file():
            for group in (yaml.safe_load(extra_path.read_text(encoding='utf-8')) or {}).values():
                if isinstance(group, dict):
                    for folder in str(group.get(category, '')).splitlines():
                        if folder.strip():
                            candidate = Path(group.get('base_path', config['comfy_dir'])) / folder.strip()
                            roots.insert(0, candidate) if group.get('is_default') else roots.append(candidate)
        paths = [folder / name for folder in roots if (folder / name).is_file()]
        if not paths:
            raise RuntimeError('无法定位已选择的模型文件：' + name)
        path = paths[0]
        stat = path.stat()
        key = str(path.resolve())
        record = index.get(key, {})
        if record.get('size') != stat.st_size or record.get('mtime_ns') != stat.st_mtime_ns:
            record = {'name': name, 'category': category, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                      'sha256': Downloader.checksum(path, cancel)}
            index[key] = record
            write_json(index_path, index)
        result[role] = {k: record[k] for k in ('name', 'category', 'size', 'sha256')}
    return result


def used_models(graph, model_version):
    fields = {'UNETLoader': ('diffusion_models', 'unet_name'), 'CLIPLoader': ('text_encoders', 'clip_name'),
              'VAELoader': ('vae', 'vae_name'), 'LoraLoaderModelOnly': ('loras', 'lora_name')}
    wanted = {(fields[node['class_type']][0], node['inputs'].get(fields[node['class_type']][1]))
              for node in graph.values() if node['class_type'] in fields}
    result = {}
    for role, record in model_version.items():
        if not isinstance(record, dict) or not record.get('category') or not record.get('name'):
            result[role] = record
        elif (record['category'], record['name']) in wanted:
            result[record['category'] + '/' + record['name']] = record
    return result


def semantic_signature(graph, bindings, references, model_version, use_all_models=False):
    import copy
    value = copy.deepcopy(graph)
    value.get('16', {}).get('inputs', {}).pop('filename_prefix', None)
    for node in value.values():
        if node['class_type'] in ('LoadImage', 'LoadVideo', 'LoadAudio'):
            for key in ('image', 'file', 'audio'):
                node['inputs'].pop(key, None)
    hashes = {}
    for kind, items in bindings.items():
        values = items if isinstance(items, list) else [items]
        hashes[kind] = [item.get('sha256') for item in values if item]
    if not hashes:
        hashes['images'] = [ref['sha256'] for ref in references]
    return digest({'graph': value, 'assets': hashes, 'models': model_version if use_all_models else used_models(graph, model_version)})
