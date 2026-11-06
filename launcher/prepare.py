"""Prepare a Windows source checkout on first double-click, then use the normal launcher."""
from __future__ import annotations

import hashlib
from importlib import metadata, util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from launcher.start import findBun, workbenchBuild


def download(url, name, checksum=None):
    target = ROOT / 'data/downloads' / name
    target.parent.mkdir(parents=True, exist_ok=True)

    def valid(path):
        if not path.is_file():
            return False
        if checksum is None:
            return True
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest() == checksum

    if not valid(target):
        print(f'正在下载 {name}……', flush=True)
        partial = target.with_name(name + '.part')
        request = urllib.request.Request(url, headers={'User-Agent': 'ShortDramaFactory-Setup'})
        with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        if not valid(partial):
            raise RuntimeError(f'{name} 下载校验失败，请重新启动以重试。')
        partial.replace(target)
    return target


def run(arguments, cwd=ROOT):
    subprocess.run([str(value) for value in arguments], cwd=cwd, check=True)


def preparePython():
    missing = []
    for line in (ROOT / 'requirements.lock.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        name, version = line.strip().split('==', 1)
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        if installed != version:
            missing.append(name)
    if not missing:
        print('Python 依赖已就绪。', flush=True)
        return
    print(f'正在安装锁定的 Python 依赖（需准备 {len(missing)} 项），请保持窗口打开……', flush=True)
    if util.find_spec('pip') is None:
        installer = download('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')
        run([sys.executable, installer, 'pip==26.3', '--disable-pip-version-check', '--no-warn-script-location'])
    run([sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', '--disable-pip-version-check',
         '--no-warn-script-location', '-r', ROOT / 'requirements.lock.txt'])


def prepareWorkbench():
    pending = ROOT / 'runtime/workbench-build.pending'
    try:
        workbench = workbenchBuild(ROOT)
        needsBuild = pending.exists()
    except RuntimeError:
        workbench = ROOT / 'workbench'
        needsBuild = True
    try:
        bun = findBun(ROOT)
    except RuntimeError:
        bun = None
    manifest = workbench / 'package.json'
    # Source installs use the lockfile's package manager; portable packages already contain Bun.
    version = json.loads(manifest.read_text(encoding='utf-8'))['packageManager'].removeprefix('bun@') if manifest.is_file() else None
    if needsBuild and not version:
        raise RuntimeError('工作台构建或源码缺失，请完整解压便携包，或重新获取完整源码。')
    if bun and needsBuild:
        actual = subprocess.check_output([bun, '--version'], text=True).strip()
        if actual != version:
            bun = None
    if not bun:
        if not version:
            raise RuntimeError('便携包缺少 Bun，请完整解压便携包。')
        archiveName = 'bun-windows-x64-baseline.zip'
        base = f'https://github.com/oven-sh/bun/releases/download/bun-v{version}'
        checksums = download(base + '/SHASUMS256.txt', f'bun-{version}-SHASUMS256.txt')
        checksum = next((line.split()[0] for line in checksums.read_text().splitlines()
                         if line.split() and line.split()[-1].lstrip('*') == archiveName), None)
        if not checksum or len(checksum) != 64:
            raise RuntimeError('Bun 官方校验清单无效，请检查下载连接后重试。')
        archive = download(base + '/' + archiveName, f'bun-{version}-windows-x64-baseline.zip', checksum)
        target = ROOT / 'runtime/bun.exe'
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source:
            with source.open('bun-windows-x64-baseline/bun.exe') as incoming, target.with_suffix('.exe.part').open('wb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        target.with_suffix('.exe.part').replace(target)
        bun = str(target)
    # Build scripts invoke bun by name; only change this launcher's child environment.
    os.environ['PATH'] = str(Path(bun).parent) + os.pathsep + os.environ.get('PATH', '')
    if needsBuild:
        print('首次启动：安装工作台依赖并构建页面，可能需要数分钟……', flush=True)
        pending.parent.mkdir(parents=True, exist_ok=True)
        pending.write_text('building', encoding='utf-8')
        # Vite and dependency scripts have node shebangs; use Bun even without system Node.js.
        run([bun, '--bun', 'install', '--frozen-lockfile'], cwd=workbench)
        run([bun, '--bun', 'run', 'build:server'], cwd=workbench)
        workbenchBuild(ROOT)
        pending.unlink()
    else:
        print('画布工作台已就绪，复用现有构建。', flush=True)


def main():
    temporary = ROOT / 'data/setup-temp'
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ.update(TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary),
                      PIP_CACHE_DIR=str(ROOT / 'data/pip-cache'), PYTHONIOENCODING='utf-8')
    preparePython()
    if '--serve-only' not in sys.argv[1:]:
        prepareWorkbench()
    run([sys.executable, '-X', 'utf8', ROOT / 'launcher/start.py', *sys.argv[1:]])


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f'启动未完成：{error}\n修复后再次双击即可重试；详情见 logs/startup.log。', file=sys.stderr)
        sys.exit(error.returncode if isinstance(error, subprocess.CalledProcessError) else 1)
