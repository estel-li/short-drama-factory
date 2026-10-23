#!/usr/bin/env python3
"""Portable entry to the selected factory's director-style CLI (stdlib only)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, help='Installed factory directory')
    parser.add_argument('arguments', nargs=argparse.REMAINDER, help='Use -- before sdf.py arguments')
    args = parser.parse_args()
    script = Path(args.app).expanduser().resolve() / 'agent-skills/short-drama-factory/scripts/sdf.py'
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    if not script.is_file():
        print(json.dumps({'code': 'FACTORY_CLI_NOT_FOUND', 'message': '指定应用缺少任务 CLI，请安装短剧工厂 4.1 或更新版本。'}, ensure_ascii=False))
        return 1
    return subprocess.run([sys.executable, str(script), *(arguments or ['--help'])],
                          stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).returncode


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
