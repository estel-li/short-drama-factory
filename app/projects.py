from __future__ import annotations

import copy
import json
import shutil
import time
import uuid
from pathlib import Path

from .schemas import Options, Story, durations
from .continuity import validate_links
from .quality import POST_FIELDS, render_contract, render_contract_matches, shot_dependencies, story_report
from .storage import ROOT, digest, identifier, now, read_json, write_json


class Projects:
    def __init__(self, config, db):
        self.config, self.db = config, db
        self.refresh()

    def refresh(self):
        roots = {ROOT / 'projects', Path(self.config.get()['projects_dir'])}
        for root in roots:
            try:
                root.mkdir(parents=True, exist_ok=True)
                folders = list(root.iterdir())
            except OSError:
                continue  # An offline project disk must not prevent the workbench from opening.
            for folder in folders:
                if folder.is_dir() and (folder / 'settings.json').exists():
                    try:
                        story = read_json(folder / '分镜.json', {})
                        title = self.title(folder, story)
                    except (OSError, ValueError, AttributeError):
                        title = folder.name
                    self.db.index(folder, title, touch=False)

    def title(self, project, story=None):
        story = story if story is not None else read_json(project / '分镜.json', {})
        if story.get('title'):
            return story['title']
        episode = read_json(project / 'episode.json', {})
        if episode.get('plan', {}).get('title'):
            return episode.get('series_title', '') + ' · ' + episode['plan']['title']
        outline = read_json(project / 'outline.json', {})
        if outline.get('title') and outline['title'] not in ('用户提供的大纲', '用户提供的剧本'):
            return outline['title']
        source = project / '大纲.txt'
        first = next((line.strip() for line in source.read_text(encoding='utf-8').splitlines() if line.strip()), '') if source.is_file() else ''
        return first[:70] or '新的故事'

    def path(self, pid):
        identifier(pid)
        with self.db.connect() as db:
            row = db.execute('SELECT path FROM projects WHERE id=?', (pid,)).fetchone()
        if not row or not Path(row[0]).is_dir():
            raise ValueError('项目不存在。')
        return Path(row[0])

    def list(self):
        with self.db.connect() as db:
            rows = [dict(x) for x in db.execute('SELECT * FROM projects ORDER BY updated_at DESC')]
            busy_ids = {row[0] for row in db.execute("SELECT DISTINCT project_id FROM jobs WHERE status IN ('queued','running')")}
        for row in rows:
            row['busy'] = row['id'] in busy_ids
            path = Path(row.pop('path'))
            try:
                if not path.is_dir():
                    raise OSError('项目目录不可用，请连接原磁盘或恢复目录后刷新。')
                row['state'] = read_json(path / 'state.json', {})
                row['episode'] = read_json(path / 'episode.json', {})
                if not isinstance(row['state'], dict) or not isinstance(row['episode'], dict):
                    raise ValueError('项目记录格式错误。')
            except (OSError, ValueError):
                row.update(unavailable=True, state={'status':'unavailable','message':'项目目录或记录暂时无法读取。请连接原磁盘或恢复文件后刷新，其他项目仍可使用。'}, episode={})
        return rows

    def options(self, project):
        raw = read_json(project / 'settings.json', {})
        fields = set(Options.model_fields)
        return Options.model_validate({k: v for k, v in raw.items() if k in fields})

    def get(self, pid):
        project = self.path(pid)
        from .templates import listing
        return {'id': pid, 'title': self.title(project), 'settings': self.options(project).model_dump(),
                'busy': self.db.busy(pid),
                'episode': read_json(project / 'episode.json', {}),
                'state': read_json(project / 'state.json', {}),
                'outline': (project / '大纲.txt').read_text(encoding='utf-8') if (project / '大纲.txt').exists() else '',
                'outline_result': read_json(project / 'outline.json'),
                'story': self.normalize(pid, read_json(project / '分镜.json')) if (project / '分镜.json').exists() else None,
                'assets': read_json(project / 'assets.json', {}),
                'references': read_json(project / 'references.json', {}),
                'prompt_templates':listing(project),
                'finishing_settings':read_json(project / 'finishing-settings.json'),
                'versions': read_json(project / 'versions.json', []),
                'final': (project / '成片.mp4').exists(), 'subtitled': (project / '成片_字幕版.mp4').exists()}

    def create(self, text, options, storyboard=None):
        options = Options.model_validate(options)
        if not isinstance(text, str) or len(text) > 50000 or (not text.strip() and options.input_mode != 'storyboard'):
            raise ValueError('输入不能为空，最多五万字。')
        durations(options)
        if options.profile not in self.config.renderer_config().get('profiles', {}):
            raise ValueError('未知生成质量预设。')
        pid = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]
        project = Path(self.config.get()['projects_dir']) / pid
        story = None
        if options.input_mode == 'storyboard':
            if storyboard is None:
                try:
                    storyboard = json.loads(text)
                except ValueError as exc:
                    raise ValueError('已有分镜模式需要合法的分镜 JSON。') from exc
            story = self.normalize(pid, storyboard)
        project.mkdir(parents=True)
        (project / '大纲.txt').write_text(text, encoding='utf-8')
        write_json(project / 'settings.json', options.model_dump())
        write_json(project / 'state.json', {'status': 'new', 'shots': {}, 'message': '项目已创建。', 'stages': {}})
        self.db.index(project, self.title(project))
        if story is not None:
            self.save_story(pid, story)
        return project

    def normalize(self, pid, value):
        story = Story.model_validate(value).model_dump()
        for index, shot in enumerate(story['shots'], 1):
            shot['id'] = index
            shot['uid'] = shot['uid'] or uuid.uuid5(uuid.NAMESPACE_URL, pid + '/shot/' + str(index)).hex[:20]
            shot.setdefault('seed_offset', index)
        Story.model_validate(story)
        validate_links(story['shots'])
        return story

    def assert_idle(self, pid):
        if self.db.busy(pid):
            raise ValueError('项目正在排队或执行，请先停止任务。')

    def version(self, project, stage, value, snapshot=None):
        versions = read_json(project / 'versions.json', [])
        vid = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
        write_json(project / 'versions' / (vid + '.json'), {'stage': stage, 'value': value, 'snapshot': snapshot or {}})
        versions.append({'id': vid, 'stage': stage, 'created_at': now(), 'hash': digest(value)})
        write_json(project / 'versions.json', versions)
        return vid

    def save_story(self, pid, value, generated=False, snapshot=None):
        if not generated:
            self.assert_idle(pid)
        project = self.path(pid)
        story = self.normalize(pid, value)
        old = read_json(project / '分镜.json')
        old_normalized = self.normalize(pid, old) if old else None
        if old and old_normalized != story:
            self.version(project, 'storyboard-before-edit', old)
        old_by_uid = {s['uid']: s for s in old_normalized['shots']} if old else {}
        old_cast = {c['id']: c for c in (old or {}).get('characters', [])}
        new_cast = {c['id']: c for c in story.get('characters', [])}
        changed_cast = {cid for cid in old_cast.keys() | new_cast.keys() if old_cast.get(cid) != new_cast.get(cid)} if old else set()
        changed = []
        for shot in story['shots']:
            before = old_by_uid.get(shot['uid'])
            if before:
                left, right = copy.deepcopy(before), copy.deepcopy(shot)
                for field in ('id', 'locked'):
                    left.pop(field, None)
                    right.pop(field, None)
                identity_changed = (bool(set(shot['characters']) & changed_cast)
                                    or shot_dependencies(old_normalized, before) != shot_dependencies(story, shot))
                if left != right or identity_changed:
                    native_left={k:v for k,v in left.items() if k not in POST_FIELDS}
                    native_right={k:v for k,v in right.items() if k not in POST_FIELDS}
                    native_change=native_left!=native_right or identity_changed
                    if before.get('locked') and shot.get('locked') and native_change:
                        raise ValueError('请先解锁镜头，再编辑其内容、素材或种子。')
                    if native_change:changed.append(shot['uid'])
                    # 明确编辑了提示词时保留；修改剧情时使旧提示词失效。
                    semantic_left, semantic_right = copy.deepcopy(native_left), copy.deepcopy(native_right)
                    for field in ('seed', 'seed_offset'):
                        semantic_left.pop(field, None)
                        semantic_right.pop(field, None)
                    if before.get('prompt') == shot.get('prompt') and (semantic_left != semantic_right or identity_changed):
                        shot['prompt'] = ''
                        shot.pop('prompt_snapshot', None)
                        shot.pop('prompt_manual', None)
                    elif before.get('prompt') != shot.get('prompt') and shot.get('prompt'):
                        shot['prompt_manual'] = True
                        shot.pop('prompt_snapshot', None)
            elif shot.get('prompt') and not shot.get('prompt_snapshot'):
                shot['prompt_manual'] = True
        write_json(project / '分镜.json', story)
        write_json(project / '出片预检.json', story_report(story, self.options(project)))
        if old_normalized != story:
            for path in project.glob('成片*.mp4'):
                history = project / 'takes' / ('final_' + uuid.uuid4().hex[:8])
                history.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), history / path.name)
            (project / '字幕.srt').unlink(missing_ok=True)
        self.version(project, 'storyboard' if not generated else 'generated-storyboard', story, snapshot)
        state = read_json(project / 'state.json', {})
        # Freeze the old definitions into legacy receipts before an edit can replace them.
        # Otherwise a subsequent save could clear changed_shots and accept an old scene again.
        if old_normalized:
            for before in old_normalized['shots']:
                for collection, key in (('shots', str(before['id'])), ('shots_by_uid', before['uid'])):
                    record = state.get(collection, {}).get(key, {})
                    contract = record.get('render_contract')
                    if isinstance(contract, str) and not contract.startswith('v2:') and render_contract_matches(contract, old_normalized, before):
                        record['render_contract'] = render_contract(old_normalized, before)
        if old and not state.get('shots_by_uid'):
            state['shots_by_uid'] = {s['uid']: state.get('shots', {}).get(str(s['id']), {}) for s in self.normalize(pid, old)['shots']}
            refs = read_json(project / 'references.json', {})
            origins = {s['id']: s['uid'] for s in self.normalize(pid, old)['shots']}
            for asset in refs.values():
                if isinstance(asset, dict) and asset.get('shot_id') in origins:
                    asset.setdefault('shot_uid', origins[asset['shot_id']])
            if refs:
                write_json(project / 'references.json', refs)
        if state.get('shots_by_uid'):
            state['shots'] = {str(s['id']): state['shots_by_uid'].get(s['uid'], {}) for s in story['shots']}
        state.update(status='ready', total_shots=len(story['shots']), message='分镜已保存。', changed_shots=changed, updated_at=now())
        state.setdefault('stages', {})['storyboard'] = {'status': 'done', 'hash': digest(story)}
        if changed:
            state['stages'].pop('prompt', None)
        write_json(project / 'state.json', state)
        self.db.index(project, story['title'])
        return story

    def save_options(self, pid, value):
        self.assert_idle(pid)
        options = Options.model_validate(value)
        durations(options)
        project = self.path(pid)
        before = read_json(project / 'settings.json')
        self.version(project, 'settings', before)
        write_json(project / 'settings.json', options.model_dump())
        if before != options.model_dump():
            self.archive_final(project)
            state = read_json(project / 'state.json', {})
            state.update(status='ready' if (project / '分镜.json').exists() else 'new', message='项目设置已保存，继续后会更新受影响的镜头。', updated_at=now())
            write_json(project / 'state.json', state)
        return options.model_dump()

    def archive_final(self, project):
        outputs = list(project.glob('成片*.mp4'))
        if outputs:
            history = project / 'takes' / ('final_' + uuid.uuid4().hex[:8])
            history.mkdir(parents=True, exist_ok=True)
            for path in outputs:
                shutil.move(str(path), history / path.name)
        (project / '字幕.srt').unlink(missing_ok=True)
