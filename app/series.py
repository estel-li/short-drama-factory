from __future__ import annotations

import hashlib
import json
import threading
import uuid
import shutil
from pathlib import Path

from .providers import Cancelled
from .schemas import Character, Options, Outline, SeriesPlan, durations
from .storage import ROOT, contained, identifier, now, read_json, write_json


class Series:
    """A series owns a shared bible and ordered, independently recoverable projects."""
    def __init__(self, config, db, projects, content):
        self.config, self.db, self.projects, self.content = config, db, projects, content
        self.lock = threading.RLock()
        for root in {ROOT / 'projects', Path(config.get()['projects_dir'])}:
            for file in (root / '_series').glob('*/series.json'):
                self.index(file.parent, read_json(file)['title'])

    def index(self, folder, title):
        with self.db.connect() as db:
            db.execute('INSERT INTO series VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET path=excluded.path,title=excluded.title,updated_at=excluded.updated_at',
                       (folder.name, str(folder), title, now()))

    def path(self, sid):
        with self.db.connect() as db:
            row = db.execute('SELECT path FROM series WHERE id=?', (identifier(sid),)).fetchone()
        if not row or not Path(row[0]).is_dir():
            raise ValueError('剧集不存在。')
        return Path(row[0])

    def list(self):
        with self.db.connect() as db:
            ids = [row[0] for row in db.execute('SELECT id FROM series ORDER BY updated_at DESC')]
        return [{k: v for k, v in self.get(sid).items() if k in ('id', 'title', 'status', 'episode_count', 'progress', 'message')} for sid in ids]

    def get(self, sid):
        value = read_json(self.path(sid) / 'series.json')
        jobs = self.db.jobs(10000)
        latest = {}
        for job in jobs:
            latest.setdefault(job['project_id'], job)
        value['progress'] = {'complete': 0, 'error': 0, 'queued': 0, 'review': 0}
        for episode in value['episodes']:
            pid = episode.get('project_id')
            if not pid:
                episode['status'] = 'planned' if episode.get('plan') else 'unplanned'
                continue
            state = read_json(self.projects.path(pid) / 'state.json', {})
            job = latest.get(pid, {})
            job_status = job.get('status')
            episode.update(status=job_status if job_status in ('queued', 'running', 'paused', 'error') else state.get('status', 'new'),
                           message=job.get('message') if job_status == 'paused' else state.get('message', ''), total_shots=state.get('total_shots', 0))
            episode['final'] = (self.projects.path(pid) / '成片.mp4').is_file()
            if episode['final']: value['progress']['complete'] += 1
            elif episode['status'] in ('error', 'queued', 'review'): value['progress'][episode['status']] += 1
        planner = latest.get('__series_' + sid, {})
        value['planner_status'] = planner.get('status', '')
        value['planner_message'] = planner.get('message', '')
        return value

    def create(self, body):
        options = Options.model_validate(body.get('options', {}))
        durations(options)
        mode = body.get('mode', 'auto')
        if mode not in ('auto', 'manual'):
            raise ValueError('分集模式须为 auto 或 manual。')
        text = body.get('input', '')
        if not isinstance(text, str) or len(text) > 50000 or (mode == 'auto' and not text.strip()):
            raise ValueError('自动分集需要整剧故事，最多五万字。')
        title = body.get('title', '').strip() or '新短剧'
        if len(title) > 200:
            raise ValueError('剧名最多 200 字。')
        fail_policy = body.get('fail_policy', 'continue')
        if fail_policy not in ('continue', 'stop'):
            raise ValueError('失败策略须为继续其他集或暂停本批。')
        start = body.get('start', 'draft')
        if start not in ('draft', 'plan', 'all'):
            raise ValueError('选择保存草稿、批量文字规划或全自动成片。')
        shared = [Character.model_validate(c).model_dump() for c in body.get('characters', [])]
        if len({c['id'] for c in shared}) != len(shared):
            raise ValueError('共享角色 id 重复。')
        count = 0
        if mode == 'auto':
            try:
                raw_count = body.get('episode_count', 3)
                count = int(raw_count)
                if count != float(raw_count) or not 1 <= count <= 100:
                    raise ValueError()
            except (ValueError, TypeError, OverflowError):
                raise ValueError('自动分集数量须为 1～100 的整数。')
        entries = body.get('episodes', []) if mode == 'manual' else [{} for _ in range(count)]
        if not 1 <= len(entries) <= 100:
            raise ValueError('一次支持 1～100 集。')
        episodes = []
        for number, entry in enumerate(entries, 1):
            if not isinstance(entry, dict): raise ValueError('每集须为包含 input 的对象。')
            episode_input = entry.get('input', '')
            if mode == 'manual' and (not isinstance(episode_input, str) or not episode_input.strip() or len(episode_input) > 50000):
                raise ValueError(f'第 {number} 集内容不能为空，最多五万字。')
            episode_options = Options.model_validate({**options.model_dump(), **entry.get('options', {})})
            if episode_options.input_mode == 'storyboard':
                raise ValueError('批量分集从灵感、大纲或剧本开始；已有分镜可在单集项目中导入。')
            durations(episode_options)
            episodes.append({'number': number, 'title': str(entry.get('title') or f'第 {number} 集')[:200], 'input': episode_input,
                             'options': episode_options.model_dump(), 'project_id': None})
        sid = 'series-' + uuid.uuid4().hex[:16]
        folder = Path(self.config.get()['projects_dir']) / '_series' / sid
        folder.mkdir(parents=True)
        value = {'id': sid, 'title': title, 'mode': mode, 'input': text, 'episode_count': len(episodes),
                 'options': options.model_dump(), 'characters': shared, 'scenes': [], 'props': [], 'episodes': episodes,
                 'status': 'draft', 'fail_policy': fail_policy, 'created_at': now()}
        write_json(folder / 'series.json', value)
        self.index(folder, title)
        if mode == 'manual': self.materialize(sid)
        return sid, start

    def materialize(self, sid):
        with self.lock:
            folder = self.path(sid)
            value = read_json(folder / 'series.json')
            for episode in value['episodes']:
                if episode.get('project_id'): continue
                options = dict(episode['options'])
                plan = episode.get('plan')
                if plan:
                    text = plan['premise'] + '\n' + json.dumps(plan['beats'], ensure_ascii=False) + '\n结尾：' + plan['ending']
                    options['input_mode'] = 'outline'
                else: text = episode['input']
                project = self.projects.create(text, options)
                episode['project_id'] = project.name
                context = {'series_id': sid, 'series_title': value['title'], 'planning_mode': value['mode'], 'number': episode['number'], 'total': value['episode_count'],
                           'plan': plan or {'title': episode['title'], 'premise': text},
                           'characters': value['characters'], 'scenes': value['scenes'], 'props': value['props'],
                           'previous_plans': [e.get('plan', {'title': e['title'], 'premise': e['input'][:3000]}) for e in value['episodes'][:episode['number']-1]][-2:]}
                write_json(project / 'episode.json', context)
                if plan:
                    outline = Outline.model_validate(plan).model_dump()
                    write_json(project / 'outline.json', outline)
                    self.projects.version(project, 'series-episode-outline', outline, {'series_id': sid})
                self.db.index(project, value['title'] + ' · ' + episode['title'])
                write_json(folder / 'series.json', value)
            value['status'] = 'planned'
            write_json(folder / 'series.json', value)
        return value

    def plan(self, sid, status, cancel):
        folder = self.path(sid)
        value = read_json(folder / 'series.json')
        if value['mode'] == 'manual' or all(e.get('plan') for e in value['episodes']):
            return self.materialize(sid)
        options = Options.model_validate(value['options'])
        completed = sum(bool(e.get('plan')) for e in value['episodes'])
        for start in range(completed, value['episode_count'], 6):
            if cancel(): raise Cancelled('分集规划已停止，已完成计划保留。')
            count = min(6, value['episode_count'] - start)
            numbers = list(range(start + 1, start + count + 1))
            data = {'task': 'series_plan', 'input': value['input'], 'title': value['title'], 'episode_count': value['episode_count'],
                    'required_numbers': numbers, 'seconds_per_episode': options.total_seconds,
                    'shared_characters': value['characters'], 'shared_scenes': value['scenes'], 'shared_props': value['props'],
                    'previous_episodes': [e['plan'] for e in value['episodes'][:start]],
                    'instructions': '将同一个整剧故事发展成连续多集，只输出 required_numbers。不得复制同一剧情多次。每集有独立事件、推进、结尾或悬念；最后一集收束用户结局，不能提前结束全剧。首批定义整部剧全部共享角色外观和声音，后续保持这些 id 与设定；按每集时长控制剧情量。不要生成分镜或视频提示词。'}
            def validate(raw):
                plan = SeriesPlan.model_validate(raw).model_dump()
                if [e['number'] for e in plan['episodes']] != numbers:
                    raise ValueError('分集编号必须按顺序等于 ' + str(numbers))
                if value['characters'] and {c['id']: c for c in plan['characters']} != {c['id']: c for c in value['characters']}:
                    raise ValueError('后续分集规划须保持整剧共享角色完整且完全一致。')
                return plan
            status(f'正在规划第 {numbers[0]}～{numbers[-1]} 集 / 共 {value["episode_count"]} 集。')
            plan, snapshot = self.content.call(folder, 'outline', options, data, SeriesPlan.model_json_schema(), validate, status, cancel)
            value['characters'], value['scenes'], value['props'] = plan['characters'], plan['scenes'], plan['props']
            for episode, generated in zip(value['episodes'][start:start+count], plan['episodes']):
                episode.update(plan=generated, title=generated['title'])
            value.update(status='planning', completed_plans=start+count)
            write_json(folder / 'series.json', value)
            self.projects.version(folder, 'series-plan-batch', plan, snapshot)
        return self.materialize(sid)

    def enqueue_batch(self, sid, numbers=None, kind='all', batch_id=None):
        if kind not in ('all', 'plan'):
            raise ValueError('批量任务支持文字规划或全自动成片。')
        value = read_json(self.path(sid) / 'series.json')
        chosen = set(numbers or [e['number'] for e in value['episodes']])
        if not chosen or chosen - {e['number'] for e in value['episodes']}:
            raise ValueError('请选择存在的集数。')
        entries = []
        for episode in value['episodes']:
            if episode['number'] not in chosen: continue
            if not episode.get('project_id'): raise ValueError('请先完成整剧分集规划。')
            entries.append((episode['project_id'], kind, {'series_id': sid, 'episode_number': episode['number'],
                            'execution_mode': 'auto', 'fail_policy': value['fail_policy']}))
        return self.db.enqueue_many(entries, batch_id or uuid.uuid4().hex)

    def stop(self, sid):
        self.path(sid)
        pids = self.db.cancel_series(sid)
        self.mark_paused(pids)
        for pid in pids:
            if not pid.startswith('__series_'): (self.projects.path(pid) / '.stop').touch()
        return {'message': '已停止本剧排队任务；运行中的文字请求将停止，视频在当前镜头完成后停止。', 'projects': pids}

    def mark_paused(self, pids):
        latest = {}
        for job in self.db.jobs(10000): latest.setdefault(job['project_id'],job)
        for pid in pids:
            if pid.startswith('__series_') or latest.get(pid,{}).get('status') != 'paused': continue
            project = self.projects.path(pid)
            state = read_json(project / 'state.json', {})
            state.update(status='paused',message='本批已暂停，已完成成果保留；可选择此集继续。',updated_at=now())
            write_json(project / 'state.json',state)

    def inherit_references(self, project):
        context = read_json(project / 'episode.json', {})
        if not context or context['number'] < 2:
            return
        series = read_json(self.path(context['series_id']) / 'series.json')
        assets = read_json(project / 'assets.json', {})
        present = {a.get('character') for a in assets.values() if a.get('type') == 'image'}
        shared = {c['id']: c for c in context.get('characters', [])}
        for episode in series['episodes'][:context['number'] - 1]:
            source = self.projects.path(episode['project_id'])
            candidates = [(a.get('character'), a.get('file')) for a in read_json(source / 'assets.json', {}).values() if a.get('type') == 'image']
            candidates += [(cid, a.get('local_file')) for cid, a in read_json(source / 'references.json', {}).items() if isinstance(a, dict)]
            for cid, relative in candidates:
                if cid not in shared or cid in present or not relative:
                    continue
                origin = contained(source, relative)
                if not origin.is_file() or origin.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
                    continue
                checksum = hashlib.sha256(origin.read_bytes()).hexdigest()
                aid = 'series-' + identifier(cid) + '-' + checksum[:12]
                filename = 'assets/' + aid + origin.suffix.lower()
                target = contained(project, filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origin, target)
                assets[aid] = {'id': aid, 'type': 'image', 'name': shared[cid]['name'] + f'（第 {episode["number"]} 集共享）',
                               'character': cid, 'file': filename, 'sha256': checksum, 'source': 'series-inherited',
                               'source_episode': episode['number'], 'created_at': now()}
                present.add(cid)
        write_json(project / 'assets.json', assets)
