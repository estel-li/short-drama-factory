"""Fetch pinned, text-only upstream skill sources for review; never execute upstream files."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
REPOS = ['MiniMax-AI/MiniMax-H3', 'zenstory-ai/drama-skills',
         'gainubi/storyboard-video-skill', 'aicontentskills/ai-video-storyboard-skill']


async def fetch_repo(client, repo):
    base = 'https://api.github.com/repos/' + repo
    response = await client.get(base)
    response.raise_for_status()
    meta = response.json()
    response = await client.get(base + '/commits/' + meta['default_branch'])
    response.raise_for_status()
    revision = response.json()['sha']
    response = await client.get(base + '/git/trees/' + revision, params={'recursive': '1'})
    response.raise_for_status()
    paths = [x['path'] for x in response.json()['tree'] if x['type'] == 'blob' and x.get('size', 0) < 500_000
             and (x['path'].lower().endswith(('.md', '.txt')) or Path(x['path']).name.upper().startswith(('LICENSE', 'COPYING')))]
    if repo == 'MiniMax-AI/MiniMax-H3':
        paths = [p for p in paths if p.startswith('skills/') or '/' not in p]
    folder = ROOT / 'data/skill-research' / repo.replace('/', '--')
    files = {}
    semaphore = asyncio.Semaphore(5)
    async def download(path):
        async with semaphore:
            url = f'https://raw.githubusercontent.com/{repo}/{revision}/{path}'
            result = await client.get(url)
            result.raise_for_status()
            content = result.content
            content.decode('utf-8-sig')
            target = folder / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            files[path] = {'url': url, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
    await asyncio.gather(*(download(path) for path in paths))
    index = {'repo': repo, 'revision': revision, 'license': meta.get('license'), 'files': files}
    (folder / 'source.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'repo': repo, 'revision': revision, 'license': (meta.get('license') or {}).get('spdx_id'),
                      'files': len(files), 'skill_paths': [p for p in paths if p.endswith('SKILL.md')],
                      'license_paths': [p for p in paths if Path(p).name.upper().startswith(('LICENSE', 'COPYING'))]}, ensure_ascii=False), flush=True)


async def main():
    async with httpx.AsyncClient(timeout=40, follow_redirects=True, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'DramaFactory-SkillResearch'}) as client:
        results = await asyncio.gather(*(fetch_repo(client, repo) for repo in REPOS), return_exceptions=True)
        failures = [repr(result) for result in results if isinstance(result, Exception)]
        if failures:
            raise RuntimeError('\n'.join(failures))


if __name__ == '__main__':
    asyncio.run(main())
