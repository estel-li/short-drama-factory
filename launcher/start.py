"""Start the local panel with the bundled Python, without PowerShell."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent


def health(url):
    try:
        # /api/health also probes ComfyUI (up to 2 seconds); allow response overhead.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url + '/api/health', timeout=5) as response:
            value = json.loads(response.read(65536).decode('utf-8'))
            return value if isinstance(value, dict) else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def check_owner(value, root):
    if not str(value.get('version', '')).startswith(('2.', '3.')) or not value.get('application_root'):
        raise RuntimeError('端口已被其他服务占用，请使用 --port 指定空闲端口。')
    if Path(value['application_root']).resolve() != root.resolve():
        raise RuntimeError('端口已被另一目录的工作台占用，请使用 --port 指定空闲端口。')


def launch(root=ROOT, port=8765, no_browser=False):
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
    if not no_browser:
        webbrowser.open(url)
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动短剧工厂')
    parser.add_argument('--port', '-Port', type=int, default=8765)
    parser.add_argument('--no-browser', '-NoBrowser', action='store_true')
    args = parser.parse_args()
    try:
        launch(port=args.port, no_browser=args.no_browser)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')
    print(f'短剧工厂已就绪：http://127.0.0.1:{args.port}')
