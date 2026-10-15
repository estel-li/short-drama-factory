from __future__ import annotations

import copy
import hashlib
import json
import shutil
import time
import uuid
import zipfile
from pathlib import Path

from .schemas import Options, Provider
from .storage import ROOT, contained, identifier, read_json, write_json

TEXT_SUFFIXES = {'.json', '.txt', '.md', '.srt', '.ass'}
MEDIA_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm', '.wav', '.mp3', '.flac', '.m4a', '.ogg', '.mov'}
PROJECT_FILES = {'大纲.txt', 'outline.json', '分镜.json', 'settings.json', 'state.json', 'assets.json', 'references.json', 'versions.json',
                 'renderer_snapshot.json', '媒体验收.json', '成片.mp4', '成片_字幕版.mp4', '字幕.srt', '字幕.ass', 'episode.json',
                 'finishing-settings.json', 'current_edit.json', '出片预检.json'}
PROJECT_FOLDERS = {'assets', 'clips', 'versions', 'requests', 'prompts', 'takes', 'edits', 'source_cache', 'prompt_templates'}


class Transfer:
    def __init__(self, config, projects, skills):
        self.config, self.projects, self.skills = config, projects, skills
        self.root = config.root

    def secrets(self):
        ids = [p['id'] for p in self.config.get()['providers']] + ['hf', 'comfy']
        return [value for pid in ids if (value := self.config.key(pid))]

    def redact(self, value):
        text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        for secret in self.secrets():
            text = text.replace(secret, '[REDACTED]')
        return json.loads(text) if not isinstance(value, str) else text

    def write_media(self, archive, name, path):
        secrets = [value.encode() for value in self.secrets()]
        overlap = max([len(value) for value in secrets] or [1]) - 1
        checksum = hashlib.sha256(); tail = b''
        with path.open('rb') as source, archive.open(name, 'w', force_zip64=True) as target:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                combined = tail + chunk
                if any(value in combined for value in secrets):
                    raise ValueError('素材包含私密认证信息，无法导出：' + path.name)
                tail = combined[-overlap:] if overlap else b''
                checksum.update(chunk); target.write(chunk)
        return checksum.hexdigest()

    def export(self, pids=None, include_videos=False):
        pids = pids or []
        packages = [{k: v for k, v in self.skills.get(s['id']).items() if k != 'content_hash'} for s in self.skills.list()]
        manifest = {'kind': 'drama-factory-transfer', 'version': 2, 'skills': self.redact(packages),
                    'providers': self.redact(self.config.get()['providers']),
                    'presets': self.redact(read_json(self.root / 'presets/personal.json', {})), 'projects': {}, 'files': {}}
        folder = self.root / 'data/exports'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / ('迁移包_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6] + '.zip')
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for pid in pids:
                self.projects.assert_idle(pid)
                project = self.projects.path(pid)
                state = copy.deepcopy(read_json(project / 'state.json', {}))
                for collection in ('shots', 'shots_by_uid'):
                    for record in state.get(collection, {}).values():
                        if record.get('clip'):
                            clip = Path(record['clip'])
                            if clip.is_relative_to(project):
                                record['clip_relative'] = str(clip.relative_to(project)).replace('\\', '/')
                        record.pop('clip', None)
                        for name in ('prompt_id', 'sampling_prompt_id', 'encoding_prompt_id'):
                            record.pop(name, None)
                        if not include_videos:
                            record['status'] = 'new'
                state.pop('output', None)
                state.pop('job_id', None)
                state['status'] = 'complete' if include_videos and (project / '成片.mp4').exists() else 'ready'
                manifest['projects'][pid] = {'title': read_json(project / '分镜.json', {}).get('title', pid)}
                refs = copy.deepcopy(read_json(project / 'references.json', {}))
                virtual = {}
                for cid, asset in list(refs.items()):
                    if isinstance(asset, str):
                        asset = refs[cid] = {'image': asset, 'shot_id': 0}
                    if not asset.get('local_file') and asset.get('image'):
                        source = contained(Path(self.config.renderer_config()['comfy_dir']) / 'input', asset['image'])
                        if not source.is_file():
                            raise ValueError('旧版参考只保存在原 ComfyUI input 中，请连接原环境后再导出：' + str(cid))
                        relative = 'assets/legacy_ref_' + identifier(cid) + source.suffix.lower()
                        virtual[relative] = source.read_bytes()
                        asset.update(local_file=relative, sha256=hashlib.sha256(virtual[relative]).hexdigest())
                for path in project.rglob('*'):
                    if not path.is_file():
                        continue
                    relative = path.relative_to(project)
                    if not path.resolve().is_relative_to(project.resolve()):
                        raise ValueError('项目包含指向外部目录的文件，请先复制素材到项目内。')
                    if not (len(relative.parts) == 1 and path.name in PROJECT_FILES or relative.parts[0] in PROJECT_FOLDERS):
                        continue
                    if path.suffix.lower() not in TEXT_SUFFIXES | MEDIA_SUFFIXES or not include_videos and relative.parts[0] != 'assets' and path.suffix.lower() in ('.mp4', '.webm', '.mov'):
                        continue
                    if not include_videos and (relative.parts[0] in ('edits', 'source_cache') or path.name in ('current_edit.json', '媒体验收.json')):
                        continue
                    if relative.parts[0] == 'edits':
                        if len(relative.parts) < 3 or not (project / 'edits' / relative.parts[1] / 'completed.json').is_file():continue
                        if relative.parts[2] != 'review' and path.name not in ('recipe.json','completed.json','媒体验收.json','成片.mp4','成片_字幕版.mp4','字幕.ass','字幕.srt'):continue
                    name = 'projects/' + pid + '/' + str(relative).replace('\\', '/')
                    if path.suffix.lower() in MEDIA_SUFFIXES:
                        manifest['files'][name] = self.write_media(archive, name, path)
                        continue
                    if path.stat().st_size > 12_000_000:
                        raise ValueError('项目文本记录超过 12MB，请拆分后再迁移：' + path.name)
                    content = path.read_bytes()
                    if path.suffix in TEXT_SUFFIXES:
                        content = self.redact(content.decode('utf-8-sig')).encode('utf-8')
                    if path.name == 'state.json' and len(relative.parts) == 1:
                        content = json.dumps(self.redact(state), ensure_ascii=False, indent=2).encode()
                    if path.name == 'references.json' and len(relative.parts) == 1:
                        content = json.dumps(self.redact(refs), ensure_ascii=False, indent=2).encode()
                    if any(secret.encode() in content for secret in self.secrets()):
                        raise ValueError('素材包含私密认证信息，无法导出：' + str(relative))
                    archive.writestr(name, content)
                    manifest['files'][name] = hashlib.sha256(content).hexdigest()
                for relative, content in virtual.items():
                    name = 'projects/' + pid + '/' + relative
                    archive.writestr(name, content)
                    manifest['files'][name] = hashlib.sha256(content).hexdigest()
            archive.writestr('transfer.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        return target

    def import_package(self, source):
        stage = self.root / 'data/imports' / uuid.uuid4().hex
        stage.mkdir(parents=True)
        with zipfile.ZipFile(source) as archive:
            if sum(item.file_size for item in archive.infolist()) > 4 * 1024**3 or len(archive.infolist()) > 50000:
                raise ValueError('迁移包过大。')
            if 'transfer.json' not in archive.namelist() or archive.getinfo('transfer.json').file_size > 12_000_000:
                raise ValueError('迁移包缺少有效清单，或清单超过 12MB。')
            manifest = json.loads(archive.read('transfer.json'))
            if manifest.get('kind') != 'drama-factory-transfer' or manifest.get('version') != 2:
                raise ValueError('不是支持的短剧工厂迁移包。')
            if len(set(archive.namelist())) != len(archive.namelist()):
                raise ValueError('迁移包存在重复文件。')
            for name, expected in manifest['files'].items():
                parts = Path(name.replace('\\', '/')).parts
                if len(parts) < 3 or parts[0] != 'projects' or identifier(parts[1]) not in manifest['projects']:
                    raise ValueError('迁移包项目路径不合法。')
                relative = Path(*parts[2:])
                if not (len(relative.parts) == 1 and relative.name in PROJECT_FILES or relative.parts[0] in PROJECT_FOLDERS):
                    raise ValueError('迁移包包含不允许的项目文件。')
                if relative.suffix.lower() not in TEXT_SUFFIXES | MEDIA_SUFFIXES:
                    raise ValueError('迁移包文件类型不允许。')
                target = contained(stage, name)
                if relative.suffix.lower() in TEXT_SUFFIXES and archive.getinfo(name).file_size > 12_000_000:
                    raise ValueError('项目文本记录超过 12MB：' + relative.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                checksum = hashlib.sha256()
                with archive.open(name) as incoming, target.open('wb') as output:
                    for chunk in iter(lambda: incoming.read(1024 * 1024), b''):
                        checksum.update(chunk); output.write(chunk)
                if checksum.hexdigest() != expected:
                    raise ValueError('迁移包文件校验失败：' + relative.name)
        # 在写入用户目录前校验项目和所有 skill 内容。
        for pid in manifest['projects']:
            folder = stage / 'projects' / identifier(pid)
            Options.model_validate(read_json(folder / 'settings.json'))
            self.projects.normalize(pid, read_json(folder / '分镜.json')) if (folder / '分镜.json').exists() else None
            if (folder / 'finishing-settings.json').exists():
                from .finishing_settings import validate_settings
                validate_settings(read_json(folder / 'finishing-settings.json'), read_json(folder / '分镜.json'))
            state = read_json(folder / 'state.json', {})
            for collection in ('shots', 'shots_by_uid'):
                for record in state.get(collection, {}).values():
                    if record.get('clip_relative'):
                        contained(folder, record['clip_relative'])
        from .skills import Skills
        validation = Skills(stage / 'validated-skills')
        for value in manifest.get('skills', []):
            validation.save(identifier(value['id']), {k: v for k, v in value.items() if k != 'files'}, value['files'])
        for provider in manifest.get('providers', []):
            Provider.model_validate(provider)
        for key, preset in manifest.get('presets', {}).items():
            identifier(key)
            Options.model_validate(preset['options'])
        imported_skills, skill_mapping = [], {}
        for value in manifest.get('skills', []):
            sid = identifier(value['id'])
            if (self.skills.root / sid).exists():
                if self.skills.get(sid)['files'] == value['files']:
                    skill_mapping[value['id']] = sid
                    continue
                sid = 'import-' + uuid.uuid4().hex[:12]
            metadata = {k: v for k, v in value.items() if k != 'files'}
            self.skills.save(sid, metadata, value['files'])
            skill_mapping[value['id']] = sid
            imported_skills.append(sid)
        config = self.config.get()
        provider_mapping = {}
        existing = {p['id']: p for p in config['providers']}
        for provider in manifest.get('providers', []):
            provider = Provider.model_validate(provider).model_dump()
            original = provider['id']
            if original in existing and any(provider[k] != existing[original][k] for k in ('kind', 'base_url', 'model')):
                provider['id'] = 'import-' + uuid.uuid4().hex[:12]
            elif original not in existing and self.config.key(original):
                provider['id'] = 'import-' + uuid.uuid4().hex[:12]
            provider_mapping[original] = provider['id']
            if provider['id'] not in existing:
                provider['capabilities'] = {}
                config['providers'].append(provider)
        self.config.save(config)
        imported = []
        for old_id in manifest['projects']:
            root = Path(self.config.get()['projects_dir']).resolve()
            pid = old_id
            if (root / pid).exists():
                pid = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]
            target = contained(root, pid)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = contained(stage, 'projects/' + old_id)
            shutil.copytree(source, target)
            settings = read_json(target / 'settings.json')
            for choice in settings.get('stages', {}).values():
                choice['skill'] = skill_mapping.get(choice.get('skill'), choice.get('skill', ''))
                choice['provider'] = provider_mapping.get(choice.get('provider'), choice.get('provider', 'deepseek'))
            write_json(target / 'settings.json', settings)
            state = read_json(target / 'state.json', {})
            for collection in ('shots', 'shots_by_uid'):
                for record in state.get(collection, {}).values():
                    if record.get('clip_relative'):
                        clip = contained(target, record['clip_relative'])
                        record['clip'] = str(clip)
                        if not clip.exists():
                            record['status'] = 'new'
            write_json(target / 'state.json', state)
            self.projects.db.index(target, manifest['projects'][old_id]['title'])
            imported.append(pid)
        personal = read_json(self.root / 'presets/personal.json', {})
        for key, preset in manifest.get('presets', {}).items():
            Options.model_validate(preset['options'])
            for choice in preset['options'].get('stages', {}).values():
                choice['skill'] = skill_mapping.get(choice.get('skill'), choice.get('skill', ''))
                choice['provider'] = provider_mapping.get(choice.get('provider'), choice.get('provider', 'deepseek'))
            personal[identifier(key) if key not in personal else 'import-' + uuid.uuid4().hex[:12]] = preset
        write_json(self.root / 'presets/personal.json', personal)
        return {'projects': imported, 'skills': imported_skills}
