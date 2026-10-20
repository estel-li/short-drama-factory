from __future__ import annotations

import copy
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit

from .schemas import Provider, Quality
from .image_schemas import ImageSettings
from .storage import ROOT, identifier, read_json, write_json


class ConfigStore:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.path = self.root / 'config' / 'application.json'
        self.lock = threading.RLock()
        self.root.joinpath('.secrets').mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            legacy = read_json(self.root / 'config.json', read_json(self.root / 'config.default.json', {}))
            value = {'version': 2, 'projects_dir': str(self.root / 'projects'),
                     'environment': {k: v for k, v in legacy.items() if k not in ('deepseek_url', 'deepseek_model')},
                     'providers': [Provider(id='deepseek', name='DeepSeek', kind='deepseek',
                        base_url=legacy.get('deepseek_url', 'https://api.deepseek.com'),
                        model=legacy.get('deepseek_model', 'deepseek-flash'), extra={'thinking': {'type': 'disabled'}}).model_dump(),
                        Provider(id='ollama', name='Ollama 本地', kind='ollama', base_url='http://127.0.0.1:11434/v1', local=True).model_dump(),
                        Provider(id='lmstudio', name='LM Studio 本地', kind='lmstudio', base_url='http://127.0.0.1:1234/v1', local=True).model_dump()],
                     'proxy': '', 'setup_complete': bool(legacy.get('comfy_dir'))}
            value['environment'].setdefault('mode', 'existing')
            value['environment'].setdefault('comfy_url', 'http://127.0.0.1:8188')
            write_json(self.path, value)
        value = read_json(self.path)
        if value.get('retry_policy_version') != 1:
            write_json(self.root / 'config' / 'before-retry-policy.json', value)
            for provider in value['providers']:
                if provider.get('retries', 1) == 1:
                    provider['retries'] = 3
                provider.setdefault('format_retries', 3)
            value['retry_policy_version'] = 1
            write_json(self.path, value)

    def get(self):
        return read_json(self.path)

    def public(self):
        value = self.get()
        value['image_generation'] = ImageSettings.model_validate(value.get('image_generation', {})).model_dump()
        for p in value['providers']:
            p['key_configured'] = bool(self.key(p['id']))
        return value

    def save(self, value):
        with self.lock:
            previous_images = self.get().get('image_generation', {})
            value = {k: copy.deepcopy(value[k]) for k in ('version', 'projects_dir', 'environment', 'providers', 'proxy', 'setup_complete', 'retry_policy_version', 'image_generation') if k in value}
            value['image_generation'] = ImageSettings.model_validate(value.get('image_generation', previous_images)).model_dump()
            value['retry_policy_version'] = 1
            providers = []
            for p in value['providers']:
                p.pop('key_configured', None)
                providers.append(Provider.model_validate(p).model_dump())
            ids = [p['id'] for p in providers]
            if len(ids) != len(set(pid.lower() for pid in ids)) or not providers:
                raise ValueError('提供商 id 必须唯一，至少保留一个。')
            value['providers'] = providers
            env = value['environment']
            if env.get('mode', 'existing') not in ('existing', 'fresh', 'remote'):
                raise ValueError('生成环境模式不支持。')
            endpoint = urlsplit(env.get('comfy_url', ''))
            if endpoint.scheme not in ('http', 'https') or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                raise ValueError('ComfyUI 服务地址须为不含认证、查询或片段的 HTTP(S) URL；认证信息单独保存。')
            env['comfy_url'] = env['comfy_url'].rstrip('/')
            if value.get('proxy'):
                endpoint = urlsplit(value['proxy'])
                if endpoint.scheme not in ('http', 'https') or not endpoint.hostname or endpoint.username or endpoint.password:
                    raise ValueError('代理填写完整 HTTP(S) 服务地址，认证信息不放在公开配置中。')
            profiles = value['environment'].get('profiles', {})
            if not profiles:
                raise ValueError('至少需要一个生成质量预设。')
            value['environment']['profiles'] = {identifier(name): Quality.model_validate(p).model_dump() for name, p in profiles.items()}
            value['version'] = 2
            write_json(self.path, value)
            return self.public()

    def provider(self, pid):
        for p in self.get()['providers']:
            if p['id'] == pid:
                return Provider.model_validate(p)
        raise ValueError('未配置提供商：' + pid)

    def key(self, pid):
        identifier(pid)
        env = os.environ.get('DEEPSEEK_API_KEY', '') if pid == 'deepseek' else ''
        path = self.root / '.secrets' / (pid + '.key')
        return env.strip() or (path.read_text(encoding='utf-8').strip() if path.exists() else '')

    def set_key(self, pid, value):
        if pid not in ('hf', 'comfy'):
            self.provider(pid)
        if not isinstance(value, str) or len(value) > 4000 or '\n' in value or '\r' in value:
            raise ValueError('认证信息格式不正确。')
        path = self.root / '.secrets' / (identifier(pid) + '.key')
        if value.strip():
            path.write_text(value.strip(), encoding='utf-8')
        else:
            path.unlink(missing_ok=True)

    def renderer_config(self):
        legacy = read_json(self.root / 'config.json', {})
        legacy.update(self.get()['environment'])
        legacy['proxy'] = self.get().get('proxy', '')
        legacy['runtime_root'] = str(self.root)
        from .video_workflows import BUILTIN_PROFILES
        legacy['profiles'] = {**copy.deepcopy(BUILTIN_PROFILES), **legacy.get('profiles', {})}
        return legacy
