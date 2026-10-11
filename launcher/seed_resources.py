"""Seed reviewed bundled skills; preserve existing user files."""
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.storage import ROOT, read_json


def seed(root=ROOT):
    root = Path(root)
    manifest = read_json(ROOT / 'resources/builtin_skills.json')
    if not manifest or len(manifest['ids']) < 13:
        raise RuntimeError('The complete bundled skill resources are missing.')
    for sid in manifest['ids']:
        source = ROOT / 'resources/builtin_skills' / sid
        target = root / 'skills' / sid
        if not (source / 'metadata.json').is_file():
            raise RuntimeError('Bundled skill is incomplete: ' + sid)
        if not (target / 'metadata.json').exists():
            shutil.copytree(source, target, dirs_exist_ok=True)
    target = root / 'presets/builtin.json'
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'presets/builtin.json', target)


if __name__ == '__main__':
    seed()
    print('完整预设资源已就绪。')
