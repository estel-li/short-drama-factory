from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.downloads import Downloader
from app.storage import ROOT, contained, read_json, write_json

PYTHON_VERSION = '3.13.16'
EMBED_URL = f'https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip'


def locked_wheels(folder, requirements):
    from packaging.tags import cpython_tags, compatible_tags
    from packaging.utils import canonicalize_name, parse_wheel_filename, InvalidWheelFilename
    from packaging.version import Version
    expected = {canonicalize_name(name): Version(version) for line in Path(requirements).read_text().splitlines()
                if '==' in line for name, version in [line.strip().split('==', 1)]}
    supported = list(cpython_tags((3, 13), abis=['cp313'], platforms=['win_amd64']))
    supported += list(compatible_tags((3, 13), interpreter='cp313', platforms=['win_amd64']))
    ranks = {tag:index for index,tag in reversed(list(enumerate(supported)))}
    chosen = {}
    for path in sorted(Path(folder).glob('*.whl')):
        try:name,version,_,tags = parse_wheel_filename(path.name)
        except InvalidWheelFilename:continue
        matches = [ranks[tag] for tag in tags if tag in ranks]
        if expected.get(name) != version or not matches:continue
        rank = min(matches)
        if name not in chosen or rank < chosen[name][0]:chosen[name] = (rank, path)
    missing = sorted(set(expected) - set(chosen))
    if missing:raise ValueError('缺少锁定的 Windows Python 3.13 wheel：' + ', '.join(missing))
    return [chosen[name][1] for name in expected]


def copy_agent_entrypoints(package):
    """Ship the same AI entrypoints and operator skill as the source checkout."""
    package = Path(package)
    for name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md'):
        shutil.copy2(ROOT / name, package / name)
    relative = Path('agent-skills/short-drama-factory')
    shutil.copytree(ROOT / relative, package / relative,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.tmp'))


def copy_windows_batch(source, target):
    """CMD can misparse UTF-8/LF batch files; never depend on checkout settings."""
    content = Path(source).read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    Path(target).write_bytes(content.replace(b'\n', b'\r\n'))


def build():
    dist = ROOT / 'dist'
    build = dist / ('build-' + time.strftime('%Y%m%d_%H%M%S') + '-' + uuid.uuid4().hex[:6])
    package = build / '短剧工厂'
    runtime = package / 'runtime'
    runtime.mkdir(parents=True)
    with httpx.Client(timeout=30) as client:
        signature = client.get(EMBED_URL + '.sigstore')
        signature.raise_for_status()
        published = signature.json()['messageSignature']['messageDigest']
        if published['algorithm'] != 'SHA2_256':
            raise RuntimeError('Python 上游签名摘要格式不支持。')
        checksum = base64.b64decode(published['digest']).hex()
        size = int(client.head(EMBED_URL).headers['content-length'])
    archive = ROOT / 'data/downloads' / Path(EMBED_URL).name
    Downloader().fetch(EMBED_URL, archive, size, checksum, lambda p: print('Python runtime:', p['status'], flush=True))
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            contained(runtime, name)
        source.extractall(runtime)
    (runtime / 'python313._pth').write_text('python313.zip\n.\nLib/site-packages\n..\nimport site\n', encoding='utf-8')
    wheels = dist / 'wheels-cp313'
    wheels.mkdir(parents=True, exist_ok=True)
    build_env = os.environ.copy()
    temporary = build / 'temp';temporary.mkdir()
    for key in ('TEMP','TMP','TMPDIR'):build_env[key] = str(temporary)
    build_env['PIP_CACHE_DIR'] = str(ROOT / 'data/pip-cache')
    try:
        selected = locked_wheels(wheels, ROOT / 'requirements.lock.txt')
    except ValueError:
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--only-binary=:all:', '--python-version', '3.13',
                        '--platform', 'win_amd64', '--implementation', 'cp', '--abi', 'cp313',
                        '-r', str(ROOT / 'requirements.lock.txt'), '-d', str(wheels), '--disable-pip-version-check'], check=True, env=build_env)
        selected = locked_wheels(wheels, ROOT / 'requirements.lock.txt')
    site = runtime / 'Lib/site-packages'
    site.mkdir(parents=True)
    for wheel in selected:
        with zipfile.ZipFile(wheel) as source:
            for item in source.infolist():
                relative = item.filename
                if '.data/' in relative:
                    relative = relative.split('.data/', 1)[1]
                    category, relative = relative.split('/', 1)
                    if category not in ('purelib', 'platlib'):
                        continue
                path = contained(site, relative)
                if item.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(source.read(item))
    for name in ('app', 'web', 'presets', 'manifests', 'nodes', 'launcher', 'tools', 'resources', 'docs'):
        shutil.copytree(ROOT / name, package / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.tmp'))
    from launcher.seed_resources import seed
    seed(package)
    copy_agent_entrypoints(package)
    # 用户预设可通过迁移导出；标准安装包只含内置预设。
    (package / 'presets/personal.json').unlink(missing_ok=True)
    for name in ('pipeline.py', 'server.py', 'config.default.json', 'requirements.lock.txt', '启动短剧工厂.cmd', '使用说明.md', '更新说明-2.1.md', '更新说明-2.2.md', '更新说明-2.3.md', '更新说明-2.4.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md'):
        if Path(name).suffix == '.cmd':
            copy_windows_batch(ROOT / name, package / name)
        else:
            shutil.copy2(ROOT / name, package / name)
    write_json(package / 'package.json', {'version': '3.6.0', 'python': PYTHON_VERSION, 'python_sha256': checksum,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'platform': 'Windows x64', 'models_included': False,
        'credentials_included': False})
    (package / 'README.md').write_text('# 短剧工厂便携版\n\n> **AI 操作入口：[AGENTS.md](AGENTS.md) → [视频制作 Skill](agent-skills/short-drama-factory/SKILL.md)。**\n\n解压到可写目录，双击“启动短剧工厂.cmd”。首次打开“模型与环境”：复用已有 ComfyUI，或选择从零安装。目标电脑需要可用的 NVIDIA 驱动，也可以连接远程服务。模型下载清单固定版本且可恢复。API key 和 HF token 在本机重新填写，标准包不包含模型和私人配置。详细步骤见“使用说明.md”。\n', encoding='utf-8')
    subprocess.run([str(runtime / 'python.exe'), '-c', 'import fastapi,uvicorn,av,httpx,psutil,numpy,onnxruntime; import app.api; print("portable imports passed")'], cwd=package, check=True, env=build_env)
    output = dist / ('短剧工厂-v3.6.0-Windows-x64-' + time.strftime('%Y%m%d_%H%M%S') + '.zip')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        for path in package.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                if any(name in path.parts for name in ('.secrets', 'projects', 'logs', 'data', 'config')):
                    # 顶层业务数据；第三方库中的同名目录不在此范围内。
                    if path.relative_to(package).parts[0] in ('.secrets', 'projects', 'logs', 'data', 'config'):
                        continue
                archive.write(path, str(path.relative_to(build)))
    receipt = {'archive': str(output), 'build': str(package), 'size': output.stat().st_size,
               'sha256': Downloader.checksum(output), 'python_version': PYTHON_VERSION}
    write_json(ROOT / 'logs/portable_package.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)
    return receipt


if __name__ == '__main__':
    build()
