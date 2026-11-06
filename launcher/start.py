"""Start the canvas workbench and its local production API."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent.parent


def health(url, path='/api/health', headers=None):
    try:
        # /api/health also probes ComfyUI (up to 2 seconds); allow response overhead.
        request = urllib.request.Request(url + path, headers=headers or {})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=5) as response:
            value = json.loads(response.read(65536).decode('utf-8'))
            return value if isinstance(value, dict) else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def check_owner(value, root):
    if not str(value.get('version', '')).startswith(('2.', '3.', '4.', '5.')) or not value.get('application_root'):
        raise RuntimeError('端口已被其他服务占用，请使用 --port 指定空闲端口。')
    if Path(value['application_root']).resolve() != root.resolve():
        raise RuntimeError('端口已被另一目录的工作台占用，请使用 --port 指定空闲端口。')


def launch(root=ROOT, port=8765, no_browser=True, serve_only=True):
    root = Path(root).resolve()
    if not 1 <= port <= 65535:
        raise ValueError('端口必须在 1～65535 之间。')
    url = f'http://127.0.0.1:{port}'
    value = health(url)
    if value is None:
        with socket.socket() as connection:
            connection.settimeout(2)
            if connection.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('端口已被占用，请使用 --port 指定空闲端口。')
        python = root / 'runtime/python.exe'
        if not python.is_file():
            python = root / '.venv/Scripts/python.exe'
        if not python.is_file():
            raise RuntimeError('缺少应用 Python，请使用完整便携包或先安装 .venv 依赖。')
        logs = root / 'logs'; logs.mkdir(exist_ok=True)
        temporary = root / 'data/panel-temp'; temporary.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(FACTORY_PORT=str(port), PYTHONIOENCODING='utf-8', HF_HUB_DISABLE_TELEMETRY='1')
        env['FACTORY_SERVE_ONLY'] = '1' if serve_only else '0'
        for name in ('TEMP', 'TMP', 'TMPDIR'):
            env[name] = str(temporary)
        with (logs/'panel.stdout.log').open('ab') as stdout, (logs/'panel.stderr.log').open('ab') as stderr:
            process = subprocess.Popen([str(python), '-u', str(root/'launcher/serve.py')], cwd=root,
                                       env=env, stdout=stdout, stderr=stderr,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('启动失败，请查看 logs/panel.stderr.log。')
            value = health(url)
            if value is not None:
                break
            time.sleep(.5)
        if value is None:
            raise RuntimeError('启动尚未完成，请查看 logs/panel.stderr.log，稍后重试。')
    check_owner(value, root)
    return value


def findBun(root):
    root = Path(root)
    for candidate in (root / 'runtime/bun.exe', root / 'runtime/bun/bun.exe',
                      root / 'runtime/bun/node_modules/bun/bin/bun.exe'):
        if candidate.is_file():
            return str(candidate)
    executable = shutil.which('bun')
    if executable:
        return executable
    raise RuntimeError('未找到 Bun。请使用包含 Bun 的新版便携包，或安装 Bun 后按 docs/windowsWorkbench.md 构建工作台。')


def workbenchBuild(root):
    workbench = Path(root) / 'workbench'
    required = ('server/index.js', 'web/index.html', 'nodes/h3FactoryNode.umd.js',
                'providers/media/comfyUi.ts', 'bundledPlugins/skills/factoryWorkflow/SKILL.md')
    if any(not (workbench / 'build' / item).is_file() for item in required):
        raise RuntimeError('新工作台尚未完整构建。请在 workbench 目录依次执行 bun install --frozen-lockfile 和 bun run build:server，然后重新启动。')
    return workbench


def launchWorkbench(root=ROOT, port=None, workbenchPort=3001, noBrowser=False):
    root = Path(root).resolve()
    if not 1 <= workbenchPort <= 65535 or (port is not None and not 1 <= port <= 65535):
        raise ValueError('端口必须在 1～65535 之间。')
    workbench = workbenchBuild(root)
    bun = findBun(root)
    settingsPath = workbench / 'data/settings.json'
    settings = json.loads(settingsPath.read_text(encoding='utf-8')) if settingsPath.is_file() else {}
    saved = settings.get('settings', {}) if isinstance(settings, dict) else None
    if not isinstance(saved, dict):
        raise RuntimeError('工作台设置格式无效，请检查 workbench/data/settings.json。')
    connection = saved.get('localModels', {})
    if not isinstance(connection, dict):
        raise RuntimeError('工作台工厂连接配置格式无效，请在设置中修正。')
    applicationRoot = connection.get('applicationRoot', os.environ.get('SDF_APPLICATION_ROOT') or str(root))
    if not isinstance(applicationRoot, str) or not applicationRoot.strip():
        raise RuntimeError('工作台已保存的工厂目录为空，请在工厂连接设置中填写本应用的完整目录。')
    if Path(applicationRoot).resolve() != root:
        raise RuntimeError('工作台已配置为连接另一目录的工厂，请先在设置中核对工厂目录；启动器不会覆盖现有连接。')
    configuredUrl = connection.get('factoryUrl', os.environ.get('SDF_BASE_URL'))
    if configuredUrl is not None and (not isinstance(configuredUrl, str) or not configuredUrl.strip()):
        raise RuntimeError('工作台已保存的工厂地址无效，请检查工厂连接设置。')
    factoryUrl = configuredUrl or f'http://127.0.0.1:{port or 8770}'
    address = urlsplit(factoryUrl)
    if (address.scheme != 'http' or address.hostname not in ('127.0.0.1', 'localhost')
            or address.username or address.password or address.query or address.fragment or address.path not in ('', '/')):
        raise RuntimeError('一键启动需要本机 HTTP 工厂地址，请在工作台设置中使用 http://127.0.0.1:端口。')
    backendPort = address.port or 80
    if not 1 <= backendPort <= 65535:
        raise ValueError('工厂端口必须在 1～65535 之间。')
    if port is not None and port != backendPort:
        raise RuntimeError('--port 与工作台已保存的工厂端口不一致，请先在设置中修改连接，避免启动后仍连接旧端口。')
    if backendPort == workbenchPort:
        raise ValueError('工厂 API 与画布工作台需要使用不同端口。')
    factoryUrl = f'http://{address.hostname}' + (f':{backendPort}' if backendPort != 80 else '')
    url = f'http://127.0.0.1:{workbenchPort}'
    headers = {'Origin': url, 'x-toonflow-workspace': '1'}

    def readWorkbench():
        value = health(url, '/api/launcher/status', headers)
        return value.get('data') if value and value.get('code') == 200 else None

    def verifyWorkbench(value):
        if (not isinstance(value, dict) or value.get('application') != 'shortDramaFactoryWorkbench'
                or not value.get('workbenchRoot') or Path(value['workbenchRoot']).resolve() != workbench
                or not value.get('dataDirectory') or Path(value['dataDirectory']).resolve() != workbench / 'data'):
            raise RuntimeError('工作台端口属于其他实例，请使用 --workbench-port 指定空闲端口。')
        if (not value.get('applicationRoot') or Path(value['applicationRoot']).resolve() != root
                or value.get('factoryUrl', '').rstrip('/') != factoryUrl):
            raise RuntimeError('已运行工作台的工厂连接与启动目标不一致，请关闭旧工作台服务后重试。')

    value = readWorkbench()
    if value is not None:
        verifyWorkbench(value)
    else:
        with socket.socket() as connectionSocket:
            connectionSocket.settimeout(2)
            if connectionSocket.connect_ex(('127.0.0.1', workbenchPort)) == 0:
                raise RuntimeError('工作台端口已被占用或运行的是旧版服务，请关闭该服务后重试，或使用 --workbench-port 指定空闲端口。')

    print(f'正在检查生产 API：http://127.0.0.1:{backendPort}', flush=True)
    backend = launch(root, port=backendPort, no_browser=True, serve_only=True)
    if value is None:
        env = os.environ.copy()
        env.update(TOONFLOW_SERVER_HOST='127.0.0.1', TOONFLOW_SERVER_PORT=str(workbenchPort),
                   TOONFLOW_DATA_DIR=str(workbench / 'data'), SDF_BASE_URL=factoryUrl,
                   SDF_APPLICATION_ROOT=str(root), NODE_ENV='production')
        logs = root / 'logs'
        logs.mkdir(exist_ok=True)
        print(f'正在启动画布工作台：{url}', flush=True)
        with (logs / 'workbench.stdout.log').open('ab') as stdout, (logs / 'workbench.stderr.log').open('ab') as stderr:
            process = subprocess.Popen([bun, str(workbench / 'build/server/index.js')], cwd=workbench,
                                       env=env, stdout=stdout, stderr=stderr,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('画布工作台启动失败，请查看 logs/workbench.stderr.log；生产 API 已保留运行。')
            value = readWorkbench()
            if value is not None:
                break
            time.sleep(.5)
        if value is None:
            raise RuntimeError('画布工作台启动尚未完成，请查看 logs/workbench.stderr.log，稍后重试。')
        verifyWorkbench(value)
    if not noBrowser:
        webbrowser.open(url)
    return {'url': url, 'factoryUrl': factoryUrl, 'backend': backend}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动短剧工厂画布工作台与生产 API')
    parser.add_argument('--port', '-Port', type=int, help='生产 API 端口；画布默认沿用已保存连接，未配置时为 8770；仅 API 模式默认为 8765')
    parser.add_argument('--workbench-port', type=int, default=3001, help='画布工作台端口，默认 3001')
    parser.add_argument('--no-browser', '-NoBrowser', action='store_true')
    parser.add_argument('--serve-only', action='store_true', help='仅启动 API；不恢复旧任务或打开浏览器')
    args = parser.parse_args()
    try:
        if args.serve_only:
            port = args.port if args.port is not None else 8765
            launch(port=port, no_browser=args.no_browser, serve_only=args.serve_only)
            print(f'短剧工厂 API 已就绪：http://127.0.0.1:{port}')
        else:
            result = launchWorkbench(port=args.port, workbenchPort=args.workbench_port, noBrowser=args.no_browser)
            print(f'短剧工厂画布工作台已就绪：{result["url"]}\n生产 API：{result["factoryUrl"]}')
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')
