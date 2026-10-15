"""Use ComfyUI's API so its writable directories need not be inside its install."""
from pathlib import Path
import uuid

import requests


def upload_file(path, subfolder, name, url, token=''):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    with Path(path).open('rb') as source:
        response = requests.post(url + '/upload/image', files={'image': (name, source)},
                                 data={'subfolder': subfolder, 'type': 'input', 'overwrite': 'true'},
                                 headers=headers, timeout=60)
    response.raise_for_status()
    value = response.json()
    return '/'.join(part for part in (value.get('subfolder', ''), value['name']) if part)


def download_file(item, target, url, token='', cancel=None):
    from .providers import Cancelled
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    target = Path(target)
    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.part')
    try:
        if cancel and cancel():raise Cancelled('视频下载已停止，已完成镜头保留。')
        with requests.get(url + '/view', params={key:item[key] for key in ('filename','subfolder','type') if key in item},
                          headers=headers, stream=True, timeout=60) as response:
            response.raise_for_status()
            with temporary.open('wb') as output:
                for block in response.iter_content(1024 * 1024):
                    if cancel and cancel():raise Cancelled('视频下载已停止，已完成镜头保留。')
                    output.write(block)
        if cancel and cancel():raise Cancelled('视频下载已停止，已完成镜头保留。')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
