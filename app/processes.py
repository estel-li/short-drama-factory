import ctypes
import os
import subprocess
from pathlib import Path


def owned_comfy_processes(config, runtime):
    """Identify this app's engine by its script, port and output directory."""
    import psutil
    from urllib.parse import urlsplit
    endpoint=urlsplit(config['comfy_url'])
    if config.get('mode') == 'remote' or endpoint.hostname not in ('127.0.0.1','localhost','::1'):
        raise RuntimeError('远程 ComfyUI 请在服务所在电脑停止。')
    if not config.get('comfy_dir'):
        return []
    output=str((Path(runtime)/'output').resolve()).replace('\\','/').casefold()
    expected=str((Path(config['comfy_dir'])/'main.py').resolve()).replace('\\','/').casefold()
    port=str(endpoint.port or (443 if endpoint.scheme == 'https' else 80))
    owned=[]
    for process in psutil.process_iter(['pid','cmdline']):
        args=process.info.get('cmdline') or []
        normalized=[str(a).replace('\\','/').casefold() for a in args]
        try:
            if normalized[args.index('--output-directory')+1] != output or args[args.index('--port')+1] != port:
                continue
            script_matches = expected in normalized
            if not script_matches and 'main.py' in normalized:
                script_matches = str((Path(process.cwd())/'main.py').resolve()).replace('\\','/').casefold() == expected
            if script_matches:
                owned.append(process)
        except (ValueError, IndexError, psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return owned


def stop_owned_comfy(config, runtime, *, allow_stopped=False):
    """Stop only this app's idle engine; never clear queues or kill unrelated Python."""
    import httpx
    import psutil
    from urllib.parse import urlsplit
    owned = owned_comfy_processes(config, runtime)
    if not owned:
        endpoint = urlsplit(config['comfy_url'])
        if allow_stopped:
            try:
                port = endpoint.port or (443 if endpoint.scheme == 'https' else 80)
                if not any(connection.status == psutil.CONN_LISTEN and connection.laddr.port == port
                           for connection in psutil.net_connections(kind='tcp')):
                    return False
            except (psutil.AccessDenied, OSError):
                pass
        raise RuntimeError('无法确认当前 ComfyUI 属于本工作台，请在启动它的程序中停止。')
    token=config.get('comfy_auth_token','')
    try:
        with httpx.Client(trust_env=False,timeout=5) as client:
            response=client.get(config['comfy_url']+'/queue',headers={'Authorization':'Bearer '+token} if token else {})
            response.raise_for_status();queue=response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError('无法确认 ComfyUI 队列状态，请检查服务后重试；尚未停止进程。') from error
    if not isinstance(queue, dict) or not all(isinstance(queue.get(key), list) for key in ('queue_running', 'queue_pending')):
        raise RuntimeError('ComfyUI 队列响应无效，尚未停止进程。')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('ComfyUI 还有运行或排队任务，请先完成或在生成页面停止任务，再停止引擎。')
    for process in owned:
        try:
            process.terminate();process.wait(timeout=20)
        except psutil.NoSuchProcess:
            pass
        except (psutil.TimeoutExpired, psutil.AccessDenied) as error:
            raise RuntimeError('ComfyUI 进程尚未退出或权限不足，请刷新状态后重试。') from error
    return True


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
