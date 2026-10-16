from __future__ import annotations

import hashlib
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .providers import Cancelled
from .storage import now, read_json, write_json


class Downloader:
    def __init__(self, proxy='', retries=2):
        self.proxy, self.retries = proxy, retries

    @staticmethod
    def checksum(path, cancel=None):
        value = hashlib.sha256()
        with Path(path).open('rb') as source:
            while block := source.read(4 * 1024 * 1024):
                if cancel and cancel():
                    raise Cancelled('校验已停止。')
                value.update(block)
        return value.hexdigest()

    @staticmethod
    def verification_status(target, size, checksum):
        """Read a file's unchanged checksum receipt without hashing large models."""
        target = Path(target)
        if not target.is_file() or target.stat().st_size != size:
            return 'invalid'
        stat = target.stat()
        try:
            receipt = read_json(target.with_name(target.name + '.verified.json'), {})
        except (OSError, ValueError):
            return 'unknown'
        if not isinstance(receipt, dict) or receipt.get('size') != size or receipt.get('mtime_ns') != stat.st_mtime_ns:
            return 'unknown'
        actual = receipt.get('sha256')
        if not isinstance(actual, str) or not re.fullmatch(r'[0-9a-f]{64}', actual):
            return 'unknown'
        return 'verified' if checksum and actual == checksum else 'invalid'

    def verified(self, target, size, checksum, cancel=None):
        target = Path(target)
        if not target.is_file() or target.stat().st_size != size:
            return False
        receipt_path = target.with_name(target.name + '.verified.json')
        stat = target.stat()
        if self.verification_status(target, size, checksum) == 'verified':
            return True
        actual = self.checksum(target, cancel)
        # Do not persist a receipt if the file changed while it was being read.
        after = target.stat()
        if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
            return False
        write_json(receipt_path, {'sha256': actual, 'size': size, 'mtime_ns': stat.st_mtime_ns})
        return bool(checksum and actual == checksum)

    def fetch(self, url, target, size, checksum, progress=lambda value: None, cancel=None, token=''):
        target = Path(target).resolve()
        if urlsplit(url).scheme not in ('http', 'https') or not isinstance(size, int) or size <= 0 or not re.fullmatch(r'[0-9a-f]{64}', checksum or ''):
            raise ValueError('下载必须声明 HTTP(S) 来源、文件大小及 SHA256。')
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.verified(target, size, checksum, cancel):
            progress({'status': 'reused', 'file': target.name, 'bytes': size, 'total': size})
            return target
        if shutil.disk_usage(target.parent).free < size - (target.with_name(target.name + '.part').stat().st_size if target.with_name(target.name + '.part').exists() else 0):
            raise RuntimeError('目标磁盘剩余空间不足。')
        partial = target.with_name(target.name + '.part')
        metadata = partial.with_name(partial.name + '.json')
        expected = {'url': url, 'size': size, 'sha256': checksum}
        if partial.exists() and read_json(metadata, {}) != expected:
            partial.rename(partial.with_name(partial.name + '.old-' + str(time.time_ns())))
        write_json(metadata, expected)
        for attempt in range(self.retries + 1):
            if cancel and cancel():
                raise Cancelled('下载已停止，临时文件会用于恢复。')
            offset = partial.stat().st_size if partial.exists() else 0
            if offset > size:
                partial.rename(partial.with_name(partial.name + '.oversized-' + str(time.time_ns())))
                offset = 0
            try:
                if offset < size:
                    headers = {'Range': 'bytes=' + str(offset) + '-'} if offset else {}
                    if token:
                        headers['Authorization'] = 'Bearer ' + token
                    with httpx.Client(timeout=httpx.Timeout(30, connect=20), proxy=self.proxy or None, follow_redirects=True) as client:
                        with client.stream('GET', url, headers=headers) as response:
                            if response.status_code in (401, 403):
                                raise RuntimeError('下载认证失败，受限模型需要 HF token 或账号授权。')
                            if response.status_code == 404:
                                raise RuntimeError('固定版本的下载文件不存在，请检查安装清单。')
                            response.raise_for_status()
                            if offset and response.status_code == 206:
                                match = re.match(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('content-range', ''))
                                if not match or int(match[1]) != offset or int(match[3]) != size:
                                    raise RuntimeError('服务器返回了不匹配的断点范围。')
                            elif offset:
                                offset = 0
                            with partial.open('ab' if offset else 'wb') as output:
                                written = offset
                                last = 0.0
                                for block in response.iter_bytes(256 * 1024):
                                    if cancel and cancel():
                                        raise Cancelled('下载已停止，临时文件会用于恢复。')
                                    output.write(block)
                                    written += len(block)
                                    if written > size:
                                        raise RuntimeError('下载内容超出清单中的文件大小。')
                                    if time.monotonic() - last >= 1:
                                        progress({'status': 'downloading', 'file': target.name, 'bytes': written, 'total': size, 'attempt': attempt + 1, 'resumed_from': offset})
                                        last = time.monotonic()
                if partial.stat().st_size != size:
                    raise httpx.ReadError('Incomplete file')
                progress({'status': 'verifying', 'file': target.name, 'bytes': size, 'total': size})
                if self.checksum(partial, cancel) != checksum:
                    partial.rename(partial.with_name(partial.name + '.corrupt-' + str(time.time_ns())))
                    raise httpx.ReadError('Checksum mismatch')
                if target.exists():
                    target.rename(target.with_name(target.name + '.before-repair-' + str(time.time_ns())))
                partial.replace(target)
                metadata.unlink(missing_ok=True)
                self.verified(target, size, checksum, cancel)
                progress({'status': 'complete', 'file': target.name, 'bytes': size, 'total': size, 'completed_at': now()})
                return target
            except httpx.HTTPError as exc:
                if attempt == self.retries:
                    raise RuntimeError('下载中断或文件校验失败。点击恢复会继续使用已下载的临时文件。') from None
                progress({'status': 'retrying', 'file': target.name, 'attempt': attempt + 1, 'total_attempts': self.retries + 1})
            except OSError as exc:
                raise RuntimeError('无法写入下载文件，请检查目标目录权限和磁盘空间。') from exc
        raise RuntimeError('下载未完成。')
