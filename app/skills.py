from __future__ import annotations

import copy
import re
from pathlib import Path

from .storage import ROOT, contained, digest, identifier, read_json, write_json


class Skills:
    def __init__(self, root=None):
        self.root = Path(root or ROOT / 'skills')

    def list(self):
        return [self.get(p.parent.name, full=False) for p in sorted(self.root.glob('*/metadata.json'))]

    def get(self, sid, full=True):
        folder = self.root / identifier(sid)
        value = read_json(folder / 'metadata.json')
        if not value:
            raise ValueError('Skill 不存在：' + sid)
        value['id'] = sid
        files = {'SKILL.md': (folder / 'SKILL.md').read_text(encoding='utf-8')}
        for relative in value.get('references', []):
            path = contained(folder, relative)
            if path.suffix not in ('.md', '.txt', '.json') or path.stat().st_size > 100_000:
                raise ValueError('Skill 参考文件格式或大小不合规。')
            files[relative] = path.read_text(encoding='utf-8')
        value['content_hash'] = digest(files)
        if full:
            value['files'] = files
        return value

    def render(self, sid, stage, variables):
        value = self.get(sid)
        if value['stage'] != stage:
            raise ValueError('Skill 与阶段不匹配。')
        selected = value.get('context_references', value.get('references', []))
        if not isinstance(selected, list) or any(path not in value['files'] or path == 'SKILL.md' for path in selected):
            raise ValueError('Skill 上下文参考必须指向包内的文本参考文件。')
        # Rich skills keep upstream text unchanged; the application adapter is read last.
        order = [*selected, 'SKILL.md'] if 'context_references' in value else ['SKILL.md', *selected]
        text = '\n\n'.join(('## 文件：' + path + '\n\n' if 'context_references' in value else '') + value['files'][path] for path in order)
        for name, item in variables.items():
            text = text.replace('{{' + name + '}}', str(item))
        unresolved = re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', text)
        if unresolved:
            raise ValueError('Skill 未提供变量：' + ', '.join(unresolved))
        if len(text) > 64_000:
            raise ValueError('Skill 内容过长，请减少参考内容。')
        snapshot = {k: v for k, v in value.items() if k != 'files'}
        snapshot['loaded_files'] = order
        snapshot['loaded_content_hash'] = digest({path: value['files'][path] for path in order})
        return text, snapshot

    def save(self, sid, metadata, files):
        identifier(sid)
        value = copy.deepcopy(metadata)
        if value.get('stage') not in ('outline', 'storyboard', 'prompt') or not value.get('name'):
            raise ValueError('Skill 必须声明名称和阶段。')
        if 'SKILL.md' not in files:
            raise ValueError('缺少 SKILL.md。')
        folder = self.root / sid
        checked = []
        for relative, content in files.items():
            path = contained(folder, relative)
            if path.suffix not in ('.md', '.txt', '.json') or not isinstance(content, str) or len(content.encode()) > 100_000:
                raise ValueError('只允许不超过 100KB 的文本参考文件。')
            checked.append((path, content))
        value['id'] = sid
        value['references'] = [r for r in files if r != 'SKILL.md']
        selected = value.get('context_references')
        if selected is not None and (not isinstance(selected, list) or any(path not in value['references'] for path in selected)):
            raise ValueError('上下文参考必须属于此 Skill 的参考文件。')
        value.setdefault('version', '1.0')
        value.setdefault('variables', ['style', 'genre', 'duration', 'language', 'music'])
        for path, content in checked:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8', newline='')
        write_json(folder / 'metadata.json', value)
        return self.get(sid)
