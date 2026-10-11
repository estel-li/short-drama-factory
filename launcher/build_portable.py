from __future__ import annotations

import base64
import hashlib
import json
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
    subprocess.run([sys.executable, '-m', 'pip', 'download', '--only-binary=:all:', '--python-version', '3.13',
                    '--platform', 'win_amd64', '--implementation', 'cp', '--abi', 'cp313',
                    '-r', str(ROOT / 'requirements.lock.txt'), '-d', str(wheels)], check=True)
    site = runtime / 'Lib/site-packages'
    site.mkdir(parents=True)
    allowed = {line.strip().split('==')[0].lower().replace('-', '_') for line in (ROOT / 'requirements.lock.txt').read_text().splitlines() if '==' in line}
    for wheel in wheels.glob('*.whl'):
        if wheel.name.split('-')[0].lower() not in allowed:
            continue
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
    # 用户预设可通过迁移导出；标准安装包只含内置预设。
    (package / 'presets/personal.json').unlink(missing_ok=True)
    for name in ('pipeline.py', 'server.py', 'config.default.json', 'requirements.lock.txt', 'launch.ps1', '启动短剧工厂.cmd', '使用说明.md', '更新说明-2.1.md', '更新说明-2.2.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md'):
        shutil.copy2(ROOT / name, package / name)
    write_json(package / 'package.json', {'version': '2.2.0', 'python': PYTHON_VERSION, 'python_sha256': checksum,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'platform': 'Windows x64', 'models_included': False,
        'credentials_included': False})
    (package / 'README.md').write_text('# 短剧工厂便携版\n\n解压到可写目录，双击“启动短剧工厂.cmd”。首次打开“模型与环境”：复用已有 ComfyUI，或选择从零安装。目标电脑需要可用的 NVIDIA 驱动，也可以连接远程服务。模型下载清单固定版本且可恢复。API key 和 HF token 在本机重新填写，标准包不包含模型和私人配置。详细步骤见“使用说明.md”。\n', encoding='utf-8')
    subprocess.run([str(runtime / 'python.exe'), '-c', 'import fastapi,uvicorn,av,httpx,psutil; import app.api; print("portable imports passed")'], cwd=package, check=True)
    output = dist / ('短剧工厂-Windows-x64-' + time.strftime('%Y%m%d_%H%M%S') + '.zip')
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
