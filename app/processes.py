import ctypes
import os
import subprocess
from pathlib import Path


def stop_owned_comfy(config, runtime):
    """Restart only this app's idle ComfyUI, identified by its output directory."""
    import httpx
    import psutil
    from urllib.parse import urlsplit
    endpoint=urlsplit(config['comfy_url'])
    if endpoint.hostname not in ('127.0.0.1','localhost','::1'):
        raise RuntimeError('远程服务需由服务所有者重启以加载新增节点。')
    token=config.get('comfy_auth_token','')
    with httpx.Client(trust_env=False,timeout=5) as client:
        response=client.get(config['comfy_url']+'/queue',headers={'Authorization':'Bearer '+token} if token else {})
        response.raise_for_status();queue=response.json()
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise RuntimeError('ComfyUI 还有任务，请等待完成后再准备工作流。')
    output=str((Path(runtime)/'output').resolve()).replace('\\','/').casefold()
    expected=str((Path(config['comfy_dir'])/'main.py').resolve()).replace('\\','/').casefold()
    port=str(endpoint.port or 80)
    owned=[]
    for process in psutil.process_iter(['pid','cmdline']):
        args=process.info.get('cmdline') or []
        normalized=[str(a).replace('\\','/').casefold() for a in args]
        try:
            if output in normalized and (expected in normalized or 'main.py' in normalized) and '--port' in args and args[args.index('--port')+1]==port:
                owned.append(process)
        except (ValueError,IndexError):
            continue
    if not owned:
        raise RuntimeError('资源已准备，请重启自行启动的 ComfyUI 后继续；工作台无法确认该服务属于本应用。')
    for process in owned:
        try:
            process.terminate();process.wait(timeout=20)
        except psutil.NoSuchProcess:
            pass


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
