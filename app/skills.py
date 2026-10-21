from __future__ import annotations

import copy
import re
from pathlib import Path

from .storage import ROOT, contained, digest, identifier, read_json, write_json


MAX_SKILL_TEXT = 64_000
MAX_SKILL_FILE_BYTES = 100_000
FRONT_MATTER = re.compile(r'\A---\s*\r?\n.*?\r?\n---\s*\r?\n', re.S)


def strip_front_matter(text):
    """The YAML front matter addresses humans and the skill manager; a model call does not need it."""
    return FRONT_MATTER.sub('', text, count=1)


class Skills:
    def __init__(self, root=None):
        self.root = Path(root or ROOT / 'skills')

    def list(self):
        values = []
        for path in sorted(self.root.glob('*/metadata.json')):
            try:
                values.append(self.get(path.parent.name, full=False))
            except (ValueError, OSError):
                # One unreadable package must not take down the whole list or the manager UI.
                continue
        return values

    def get(self, sid, full=True):
        folder = self.root / identifier(sid)
        value = read_json(folder / 'metadata.json')
        if not value:
            raise ValueError('Skill 不存在：' + sid)
        value['id'] = sid
        try:
            files = {'SKILL.md': (folder / 'SKILL.md').read_text(encoding='utf-8')}
            for relative in value.get('references', []):
                path = contained(folder, relative)
                if path.suffix not in ('.md', '.txt', '.json') or path.stat().st_size > MAX_SKILL_FILE_BYTES:
                    raise ValueError('Skill 参考文件格式或大小不合规：' + str(relative))
                files[relative] = path.read_text(encoding='utf-8')
        except OSError as exc:
            raise ValueError('Skill 文件缺失或不可读：' + sid + '（' + str(exc) + '）') from exc
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
        body = dict(value['files'])
        body['SKILL.md'] = strip_front_matter(body['SKILL.md'])
        text = '\n\n'.join(('## 文件：' + path + '\n\n' if 'context_references' in value else '') + body[path] for path in order)
        # Single pass: a value is never re-expanded, so user text containing {{name}} stays literal.
        placeholders = set(re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', text))
        missing = sorted(placeholders - set(variables))
        if missing:
            raise ValueError('Skill 未提供变量：' + ', '.join(missing))
        for name in placeholders:
            text = text.replace('{{' + name + '}}', str(variables[name]))
        if len(text) > MAX_SKILL_TEXT:
            raise ValueError('Skill 内容过长，请减少参考内容。')
        snapshot = {k: v for k, v in value.items() if k != 'files'}
        snapshot['loaded_files'] = order
        snapshot['loaded_content_hash'] = digest({path: body[path] for path in order})
        return text, snapshot

    def save(self, sid, metadata, files):
        identifier(sid)
        value = copy.deepcopy(metadata)
        if value.get('stage') not in ('outline', 'storyboard', 'prompt', 'image_prompt') or not value.get('name'):
            raise ValueError('Skill 必须声明名称和阶段。')
        if 'SKILL.md' not in files:
            raise ValueError('缺少 SKILL.md。')
        folder = self.root / sid
        checked = []
        for relative, content in files.items():
            path = contained(folder, relative)
            if path.suffix not in ('.md', '.txt', '.json') or not isinstance(content, str) or len(content.encode()) > MAX_SKILL_FILE_BYTES:
                raise ValueError('只允许不超过 100KB 的文本参考文件。')
            checked.append((path, content))
        value['id'] = sid
        value['references'] = [r for r in files if r != 'SKILL.md']
        selected = value.get('context_references')
        if selected is not None and (not isinstance(selected, list) or any(path not in value['references'] for path in selected)):
            raise ValueError('上下文参考必须属于此 Skill 的参考文件。')
        value.setdefault('version', '1.0')
        value.setdefault('variables', ['style', 'genre', 'duration', 'language', 'music'])
        # Reject packages that could be saved but never rendered. The check mirrors render() exactly:
        # front matter is stripped from SKILL.md and context references are placed before it.
        stripped = {relative: (strip_front_matter(content) if relative == 'SKILL.md' else content)
                    for relative, content in files.items()}
        rich = 'context_references' in value
        order = [*value['references'], 'SKILL.md'] if rich else ['SKILL.md', *value['references']]
        joined = '\n\n'.join(
            ('## 文件：' + relative + '\n\n' if rich else '') + stripped[relative] for relative in order
        )
        if len(joined) > MAX_SKILL_TEXT:
            raise ValueError(f'Skill 渲染后超过 {MAX_SKILL_TEXT} 字符，请减少参考内容。')
        for path, content in checked:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8', newline='')
        write_json(folder / 'metadata.json', value)
        return self.get(sid)
