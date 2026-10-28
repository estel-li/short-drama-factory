"""Prepare verified release assets from an existing portable build."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.version import VERSION


def checksum(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare():
    receipt = json.loads((ROOT / 'logs/portable_package.json').read_text(encoding='utf-8'))
    archive = Path(receipt['archive']).resolve()
    if not archive.is_relative_to((ROOT / 'dist').resolve()):
        raise ValueError('Portable archive must be inside dist.')
    if archive.stat().st_size != receipt['size'] or checksum(archive) != receipt['sha256']:
        raise ValueError('Portable archive differs from its build receipt.')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError('Portable archive failed its CRC check.')
        metadata = json.loads(package.read('短剧工厂/package.json'))
        if metadata['version'] != VERSION:
            raise ValueError('Portable archive version differs from the source version.')
        forbidden = {'.git', '.venv', '.secrets', '.sdf', 'config', 'data', 'models', 'projects', 'logs'}
        for name in package.namelist():
            parts = Path(name).parts
            if len(parts) > 1 and (parts[1] in forbidden or parts[1].startswith('.env') or parts[1] == 'config.json'):
                raise ValueError('Private runtime data found in portable archive: ' + name)
        for folder in ('app', 'web', 'manifests', 'nodes', 'agent-skills', 'tools'):
            for source in (ROOT / folder).rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts and source.suffix not in ('.pyc', '.pyo'):
                    relative = source.relative_to(ROOT).as_posix()
                    if package.read('短剧工厂/' + relative) != source.read_bytes():
                        raise ValueError('Portable source differs: ' + relative)
    output = ROOT / 'dist' / ('release-' + VERSION)
    output.mkdir(parents=True, exist_ok=True)
    portable = output / f'short-drama-factory-{VERSION}-windows-x64.zip'
    if portable.exists() and checksum(portable) != receipt['sha256']:
        raise ValueError('A different portable archive already exists at the release destination.')
    if not portable.exists():
        shutil.copy2(archive, portable)
    spec = importlib.util.spec_from_file_location('release_skill_installer',
        ROOT / 'agent-skills/short-drama-factory/scripts/install_skill.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    assets = [portable]
    for skill in ('short-drama-factory', 'director-style'):
        source = ROOT / 'agent-skills' / skill
        target = output / f'{skill}-skill-{VERSION}.zip'
        if not target.exists():
            installer.build_zip(source, target)
        manifest = installer.source_manifest(source)
        with zipfile.ZipFile(target) as package:
            actual = {name.removeprefix(skill + '/'): hashlib.sha256(package.read(name)).hexdigest()
                      for name in package.namelist()}
        if actual != manifest['files']:
            raise ValueError('Skill archive differs from its source: ' + skill)
        assets.append(target)
    sums = output / f'SHA256SUMS-{VERSION}.txt'
    sums.write_text(''.join(f'{checksum(path)}  {path.name}\n' for path in assets), encoding='utf-8')
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    section = changelog.split('## ' + VERSION + ' · ', 1)[1].split('\n## ', 1)[0].strip()
    title, body = section.split('\n', 1)
    notes = f'短剧工厂 **v{VERSION}** · {title}\n\n{body.strip()}\n\n'
    notes += ('## 下载与校验\n\nWindows x64 便携包内含 Python 与应用依赖；模型、ComfyUI 和认证另行配置。'
              '两个独立 Skill ZIP 可单独安装，附件摘要见 SHA256SUMS。'
              '升级前退出旧工作台并备份配置与项目，保留个人配置、凭证、模型和项目目录。\n')
    (output / 'release-notes.md').write_text(notes, encoding='utf-8')
    result = {'version': VERSION, 'title': f'v{VERSION} · {title}',
              'assets': [str(path) for path in assets + [sums]], 'notes': str(output / 'release-notes.md')}
    (output / 'release.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    prepare()
