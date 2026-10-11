"""Compatibility entry: use the independent application runtime."""
import os
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    executable = root / 'runtime/python.exe'
    if not executable.is_file():
        executable = root / '.venv/Scripts/python.exe'
    if not executable.is_file():
        raise RuntimeError('Use the Windows portable package or install the independent application runtime.')
    os.execv(str(executable), [str(executable), '-u', str(root / 'launcher/serve.py')])
