import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.storage import ROOT, read_json, write_json

packages = {'torch': '2.9.1', 'torchvision': '0.24.1', 'torchaudio': '2.9.1'}
wheels = []
for name, version in packages.items():
    page = requests.get('https://download.pytorch.org/whl/cu130/' + name + '/', timeout=30)
    page.raise_for_status()
    links = [html.unescape(link) for link in re.findall(r'href="([^"]+)"', page.text)]
    found = [url for url in links if f'/{name}-{version}+cu130-cp313-cp313-win_amd64.whl#sha256=' in unquote(url)]
    if len(found) != 1:
        raise RuntimeError('无法唯一定位固定的官方 PyTorch wheel：' + name)
    url, fragment = found[0].split('#')
    checksum = fragment.split('=')[1]
    response = requests.head(url, allow_redirects=True, timeout=30)
    response.raise_for_status()
    wheels.append({'package': name, 'version': version + '+cu130', 'url': url,
                   'name': unquote(Path(urlsplit(url).path).name), 'size': int(response.headers['content-length']), 'sha256': checksum})
manifest = read_json(ROOT / 'manifests/h3-5060ti-16g.json')
for name, version in {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'accelerate': '1.12.0',
                      'numpy': '2.3.5', 'safetensors': '0.7.0', 'huggingface-hub': '0.36.0'}.items():
    response = requests.get(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30)
    response.raise_for_status()
    candidates = [f for f in response.json()['urls'] if f['filename'].endswith('.whl') and
                  (f['filename'].endswith('py3-none-any.whl') or 'win_amd64' in f['filename'] and
                   ('-cp313-cp313-' in f['filename'] or '-abi3-' in f['filename']))]
    if len(candidates) != 1:
        raise RuntimeError('无法唯一确定 Windows Python 3.13 运行依赖：' + name)
    artifact = candidates[0]
    wheels.append({'package': name, 'version': version, 'url': artifact['url'], 'name': artifact['filename'],
                   'size': artifact['size'], 'sha256': artifact['digests']['sha256']})
manifest['runtime_wheels'] = wheels
manifest['startup'] = {'fast_disk': True, 'disable_dynamic_vram': False}
write_json(ROOT / 'manifests/h3-5060ti-16g.json', manifest)
print([(w['package'], w['version'], w['size']) for w in wheels])
