import ctypes
import os
import subprocess
from pathlib import Path


def run_process(args, *, cancel=None, **kwargs):
    """Reap only the child we launched when a CPU job is cancelled."""
    from .providers import Cancelled
    if cancel is None:
        return subprocess.run(args, **kwargs)
    if cancel():
        raise Cancelled('后期任务已停止，原片和已有成片已保留。')
    if kwargs.pop('capture_output', False):
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process = subprocess.Popen(args, **kwargs)
    try:
        while True:
            if cancel():
                raise Cancelled('后期任务已停止，原片和已有成片已保留。')
            try:
                stdout, stderr = process.communicate(timeout=.2)
                return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                continue
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()


class InstanceLock:
    """OS-owned lock: survives threads and is released even after a process crash."""
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open('a+b')
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise RuntimeError('此应用目录已有工作台运行，请打开现有面板。') from exc
        self.file = handle

    def release(self):
        if self.file:
            self.file.close()
            self.file = None


def alive(pid):
    if os.name == 'nt':
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False
