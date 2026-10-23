#!/usr/bin/env python3
"""Install a self-contained local skill, with tracked updates and backups.

No download or assistant-specific configuration is required. The target is the
exact skill directory, not its parent. Local .sdf connection/receipt data is
neither distributed nor overwritten. Modified installed files require a manual
merge; --update never discards personal edits.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import uuid
import zipfile


CONTRACT_VERSION = 1
MARKER = '.sdf-skill-install.json'
DISTRIBUTED = ('SKILL.md', 'LICENSE', 'scripts', 'assets', 'references', 'agents')
EXCLUDED = {'.sdf', '__pycache__', '.git', MARKER}


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest(source):
    source = Path(source).expanduser().resolve()
    text = (source / 'SKILL.md').read_text(encoding='utf-8-sig')
    if not text.startswith('---') or len(text.split('---', 2)) != 3:
        raise ValueError('SKILL.md 缺少 frontmatter。')
    header = text.split('---', 2)[1]
    match = re.search(r'(?m)^  contract_version:\s*[\"\']?(\d+)[\"\']?\s*$', header)
    if not match or int(match[1]) != CONTRACT_VERSION:
        raise ValueError('技能 metadata.contract_version 必须为 1；请使用兼容技能包。')
    name_match = re.search(r'(?m)^name:\s*(short-drama-factory|director-style)\s*$', header)
    if not name_match:
        raise ValueError('源目录不是支持的短剧工厂或导演风格操作技能。')
    skill_name = name_match[1]
    required = ('scripts/sdf.py', 'scripts/factory_api.py') if skill_name == 'short-drama-factory' else ('scripts/director.py',)
    for filename in required:
        if not (source / filename).is_file():
            raise ValueError('技能包缺少自包含的客户端脚本。')
    files = {}
    for entry in DISTRIBUTED:
        root = source / entry
        if root.is_symlink():
            raise ValueError('技能发布目录不能包含符号链接。')
        paths = root.rglob('*') if root.is_dir() else (root,)
        for path in paths:
            relative = path.relative_to(source)
            if any(part in EXCLUDED for part in relative.parts) or path.suffix in ('.pyc', '.pyo'):
                continue
            if path.is_symlink():
                raise ValueError('技能发布文件不能包含符号链接。')
            if path.is_file():
                files[relative.as_posix()] = checksum(path)
    return {'version': 1, 'skill_name': skill_name, 'contract_version': CONTRACT_VERSION, 'files': dict(sorted(files.items()))}


def tracked_install(source, target, update=False):
    source, target = Path(source).expanduser().resolve(), Path(target).expanduser().resolve()
    if target == Path(target.anchor) or source == target or source in target.parents or target in source.parents:
        raise ValueError('安装目录不能是磁盘根目录，也不能与源目录互相包含。')
    manifest = source_manifest(source)
    old = None
    if target.exists():
        if not target.is_dir() or target.is_symlink():
            raise ValueError('目标必须是普通目录。')
        marker = target / MARKER
        if any(target.iterdir()):
            if not update:
                raise ValueError('目标已有内容；升级已安装技能请显式使用 --update。')
            if not marker.is_file():
                raise ValueError('目标不是本工具管理的安装；请另选目录以保留个人内容。')
            old = json.loads(marker.read_text(encoding='utf-8'))
            if old.get('version') != 1 or not isinstance(old.get('files'), dict):
                raise ValueError('安装记录无效，请保留现有目录并使用新目录安装。')
            if old.get('skill_name', 'short-drama-factory') != manifest['skill_name']:
                raise ValueError('目标属于另一种技能，请使用独立目录安装。')
            for name, digest in old['files'].items():
                candidate = (target / name).resolve()
                if not candidate.is_relative_to(target):
                    raise ValueError('安装记录含越界路径。')
                if not candidate.is_file() or checksum(candidate) != digest:
                    raise ValueError('已安装文件被个人修改或删除，请先手动合并：' + name)
            for name in manifest['files']:
                if name not in old['files'] and (target / name).exists():
                    raise ValueError('新版本文件与个人文件同名，请先手动合并：' + name)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name(target.name + '.stage-' + uuid.uuid4().hex[:12])
    backup = None
    try:
        if target.exists():
            if any(path.is_symlink() for path in target.rglob('*')):
                raise ValueError('目标包含符号链接，请使用新目录安装。')
            shutil.copytree(target, stage)
        else:
            stage.mkdir()
        if old:
            for name in old['files']:
                if name not in manifest['files']:
                    candidate = (stage / name).resolve()
                    if not candidate.is_relative_to(stage.resolve()):
                        raise ValueError('旧版本记录含越界路径。')
                    candidate.unlink()
        for name in manifest['files']:
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, destination)
            if checksum(destination) != manifest['files'][name]:
                raise ValueError('安装期间源文件发生变化，请重试。')
        (stage / MARKER).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            backup = target.with_name(target.name + '.backup-' + stamp + '-' + uuid.uuid4().hex[:6])
            target.rename(backup)
        try:
            stage.rename(target)
        except BaseException:
            if backup is not None and not target.exists():
                backup.rename(target)
            raise
    finally:
        if stage.is_dir() and stage.resolve().parent == target.parent.resolve() and stage.name.startswith(target.name + '.stage-'):
            shutil.rmtree(stage)
    return {'installed': True, 'target': str(target), 'backup': str(backup) if backup else None,
            'contract_version': CONTRACT_VERSION, 'files': len(manifest['files'])}


def build_zip(source, output):
    source, output = Path(source).expanduser().resolve(), Path(output).expanduser().resolve()
    manifest = source_manifest(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name in manifest['files']:
                    archive.write(source / name, manifest['skill_name'] + '/' + name)
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {'archive': str(output), 'sha256': checksum(output), 'files': len(manifest['files'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument('--target', help='精确安装目录，例如用户 skills/short-drama-factory')
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--zip', dest='archive', help='可选创建可携带技能 ZIP，不覆盖已有文件')
    args = parser.parse_args(argv)
    try:
        if not args.target and not args.archive:
            raise ValueError('请提供 --target 或 --zip。')
        result = {}
        if args.target:
            result.update(tracked_install(args.source, args.target, args.update))
        if args.archive:
            result.update(build_zip(args.source, args.archive))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc), 'code': 'skill_install_failed'}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
