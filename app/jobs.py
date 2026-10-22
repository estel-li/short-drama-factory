from __future__ import annotations

import json
import os
import threading
import traceback

from .providers import Cancelled, ProviderError
from .content import prompt_settings_hash
from .quality import story_report
from .environment import Installer
from .rendering import fingerprint_models
from .processes import InstanceLock
from .series import Series
from .image_studio import ImageStudio
from .skills import Skills
from .storage import ROOT, digest, now, read_json, write_json


class Worker:
    def __init__(self, db, config, projects, content, assets):
        self.db, self.config, self.projects, self.content, self.assets = db, config, projects, content, assets
        self.wake, self.shutdown = threading.Event(), threading.Event()
        self.thread = None
        self.active = None
        self.execution_lock = threading.RLock()
        self.installer = Installer(config)
        self.series = Series(config, db, projects, content)
        self.images = ImageStudio(config, db, projects, assets, getattr(content, 'skills', None) or Skills())
        from .video_environment import VideoWorkflowEnvironment
        self.video_environment = VideoWorkflowEnvironment(config)
        self.instance_lock = InstanceLock(db.path.with_suffix('.worker.lock'))

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.instance_lock.acquire()
        self.db.recover()
        self.thread = threading.Thread(target=self.loop, name='factory-worker', daemon=True)
        self.thread.start()

    def enqueue(self, pid, kind='all', payload=None):
        if pid in ('__image_environment', '__video_environment'):
            pass
        elif pid.startswith('__image_'):
            self.images.path(pid.removeprefix('__image_'))
        elif pid.startswith('__series_'):
            self.series.path(pid.removeprefix('__series_'))
        elif pid != '__environment':
            self.projects.path(pid)
        jid = self.db.enqueue(pid, kind, payload)
        self.wake.set()
        return jid

    def stop(self, pid):
        self.db.cancel(pid)
        if pid == '__video_environment':
            return
        if pid.startswith('__image_'):
            if pid != '__image_environment':
                self.images.update(pid.removeprefix('__image_'), status='paused', message='已请求停止图片任务。')
            return
        (self.projects.path(pid) / '.stop').touch()

    def interrupt_owned(self, pid):
        import pipeline
        if not self.active or self.active['project_id'] != pid:
            return {'interrupted': False}
        if self.active.get('kind') not in ('all', 'render', 'image-generate', 'image-optimize', 'image-references'):
            return {'interrupted': False}
        payload = json.loads(self.active.get('payload', '{}'))
        iid = payload.get('image_id')
        if not iid and not pid.startswith('__'):
            state = read_json(self.projects.path(pid) / 'state.json', {})
            if state.get('current_stage') == 'reference_images':
                iid = state.get('image_id')
        if iid:
            self.images.interrupt(iid)
            return {'interrupted': True}
        if self.active.get('kind') not in ('all', 'render'):
            return {'interrupted': False}
        state = read_json(self.projects.path(pid) / 'state.json', {})
        owned = {record[field] for record in state.get('shots', {}).values() for field in ('prompt_id', 'sampling_prompt_id', 'encoding_prompt_id') if record.get(field)}
        queue = pipeline.api('/queue')
        pending = [item[1] for item in queue.get('queue_pending', []) if item[1] in owned]
        if pending:
            pipeline.api('/queue', {'delete': pending})
        current = any(item[1] in owned for item in queue.get('queue_running', []))
        if current:
            pipeline.api('/interrupt', {})
        return {'interrupted': current, 'removed_pending': len(pending)}

    def loop(self):
        while not self.shutdown.is_set():
            job = self.db.claim()
            if not job:
                self.wake.wait(1)
                self.wake.clear()
                continue
            self.active = job
            try:
                with self.execution_lock:
                    result = self.execute(job)
                self.db.update(job['id'], result or 'done', '任务阶段已完成。')
            except Exception as exc:
                self.record_failure(job, exc)
            finally:
                self.active = None
        self.instance_lock.release()

    def log_failure(self, exc):
        # A disconnected/full project disk or an unwritable log must not stop the queue.
        try:
            folder = self.config.root / 'logs'
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / 'worker.log').open('a', encoding='utf-8') as log:
                traceback.print_exception(type(exc), exc, exc.__traceback__, file=log)
        except Exception:
            pass

    def record_failure(self, job, exc):
        was_cancelled = isinstance(exc, Cancelled)
        try:
            was_cancelled = was_cancelled or self.db.cancelled(job['id'])
        except Exception as failure:
            self.log_failure(failure)
        status = 'paused' if was_cancelled else 'error'
        message = str(exc)[:2000] if isinstance(exc, Cancelled) or not was_cancelled else '任务已停止，成果已保留。'

        def project_state():
            if job['project_id'] == '__environment':
                write_json(self.config.root / 'data/installation_progress.json', {'status': status, 'message': message})
            elif not job['project_id'].startswith(('__series_', '__image_', '__video_')):
                path = self.projects.path(job['project_id']) / 'state.json'
                state = read_json(path, {})
                state.update(status=status, message=message, updated_at=now())
                write_json(path, state)

        def series_policy():
            payload = json.loads(job['payload'])
            if payload.get('series_id') and payload.get('fail_policy') == 'stop' and not was_cancelled:
                paused = self.db.cancel_series(payload['series_id'], queued_only=True, batch_id=payload.get('series_batch'))
                self.series.mark_paused(paused)

        # Persist the durable result first; ancillary state files fail independently.
        for save in (lambda: self.db.update(job['id'], status, message),
                     lambda: self.image_failure(job, status, message), project_state, series_policy):
            try:
                save()
            except Exception as failure:
                self.log_failure(failure)
        if not isinstance(exc, Cancelled):
            self.log_failure(exc)

    def image_failure(self, job, status, message):
        payload = json.loads(job['payload'])
        if job['project_id'] in ('__image_environment', '__video_environment'):
            path = self.config.root / ('data/video-environment-progress.json' if job['project_id']=='__video_environment' else 'data/image-environment-progress.json')
            previous = read_json(path, {})
            write_json(path, {**(previous if previous.get('job_id') == job['id'] else {}),
                              'job_id': job['id'], 'status': status, 'message': message})
        elif payload.get('image_id'):
            value = self.images.get(payload['image_id'])
            if value.get('status') != 'complete':
                self.images.update(payload['image_id'], status=status, message=message)

    def execute(self, job):
        import pipeline
        pid, jid = job['project_id'], job['id']
        if job['kind'] == 'video-prepare' and pid == '__video_environment':
            payload = json.loads(job['payload'])
            def video_report(message, **extra):
                self.db.update(jid, message=message, event={'message':message, **extra})
                write_json(self.config.root/'data/video-environment-progress.json', {'job_id':jid,'status':'running','message':message,**extra})
            self.video_environment.prepare(payload['profile'],video_report,lambda:self.db.cancelled(jid) or self.shutdown.is_set(),payload.get('download_confirmation',''))
            if self.db.cancelled(jid) or self.shutdown.is_set():raise Cancelled('视频工作流准备已暂停。')
            pipeline.CONFIG.clear();pipeline.CONFIG.update(self.config.renderer_config());pipeline.CONFIG['comfy_auth_token']=self.config.key('comfy')
            pipeline.ensure_comfy(video_report,profile=payload['profile'],
                                  cancel=lambda:self.db.cancelled(jid) or self.shutdown.is_set())
            if self.db.cancelled(jid) or self.shutdown.is_set():raise Cancelled('视频工作流准备已暂停。')
            if not self.video_environment.plan(payload['profile'])['ready']:
                raise RuntimeError('所选工作流仍缺少节点或模型，请检查 ComfyUI 启动日志。')
            write_json(self.config.root/'data/video-environment-progress.json',{'job_id':jid,'status':'done','message':'所选视频工作流已就绪。'})
            return 'done'
        if job['kind'] in ('image-prepare', 'image-generate', 'image-optimize'):
            payload = json.loads(job['payload'])
            def image_report(message, **extra):
                self.db.update(jid, message=message, event={'message': message, **extra})
                if job['kind'] == 'image-prepare':
                    write_json(self.config.root / 'data/image-environment-progress.json', {'job_id': jid, 'status': 'running', 'message': message, **extra})
                else:
                    self.images.update(payload['image_id'], message=message, **extra)
                    if not pid.startswith('__'):
                        path = self.projects.path(pid) / 'state.json'
                        state = read_json(path, {})
                        state.update(status='planning', current_stage='reference_images', image_id=payload['image_id'],
                                     message=message, job_id=jid, updated_at=now())
                        write_json(path, state)
            cancel = lambda: self.db.cancelled(jid) or self.shutdown.is_set()
            if job['kind'] == 'image-prepare':
                self.images.environment.prepare(payload.get('variant', 'auto'), image_report, cancel,
                                                payload.get('models'), payload.get('download_confirmation', ''), payload.get('image_model'))
                write_json(self.config.root / 'data/image-environment-progress.json', {'job_id': jid, 'status': 'done', 'message': '图片环境已就绪。'})
            else:
                result = self.images.generate(payload['image_id'], image_report, cancel, job['kind'] == 'image-optimize')
                if result.get('target') and result.get('project_id') and job['kind'] == 'image-generate':
                    self.images.adopt(result['project_id'], result['target'], result['id'], generated=True)
                    path = self.projects.path(pid) / 'state.json'
                    state = read_json(path, {})
                    state.update(status='ready', message='参考图已生成并采用。', current_stage='reference_images', updated_at=now())
                    write_json(path, state)
            return 'done'
        if job['kind'] == 'series-plan' and pid.startswith('__series_'):
            sid = pid.removeprefix('__series_')
            payload = json.loads(job['payload'])
            self.series.plan(sid, lambda message: self.db.update(jid, message=message, event={'message': message}),
                             lambda: self.db.cancelled(jid) or self.shutdown.is_set())
            if self.db.cancelled(jid) or self.shutdown.is_set():
                raise Cancelled('分集规划已停止。')
            if payload.get('start', 'draft') != 'draft':
                self.series.enqueue_batch(sid, kind=payload['start'], batch_id=payload.get('batch_id') or jid)
                self.wake.set()
            return 'done'
        if job['kind'] == 'install' and pid == '__environment':
            def progress(value):
                self.db.update(jid, message=value.get('message') or f'{value.get("status", "")} {value.get("file", "")} {value.get("bytes", 0)}/{value.get("total", 0)}', event=value)
                write_json(ROOT / 'data/installation_progress.json', value)
            self.installer.execute(json.loads(job['payload']), progress, lambda: self.db.cancelled(jid) or self.shutdown.is_set())
            return 'done'
        project = self.projects.path(pid)
        options = self.projects.options(project)
        payload = json.loads(job['payload'])
        if payload.get('execution_mode') == 'auto':
            options.execution_mode = 'auto'
        if payload.get('series_id') and options.auto_reference:
            self.series.inherit_references(project)
        pipeline.CONFIG.clear()
        pipeline.CONFIG.update(self.config.renderer_config())
        pipeline.CONFIG['comfy_auth_token'] = self.config.key('comfy')
        (project / '.stop').unlink(missing_ok=True)

        def cancelled():
            return self.shutdown.is_set() or self.db.cancelled(jid)

        def report(message, **changes):
            state = read_json(project / 'state.json', {})
            state.update(changes)
            state.update(message=message, updated_at=now(), job_id=jid)
            write_json(project / 'state.json', state)
            self.db.update(jid, message=message, event={'message': message, **changes})

        requested = job['kind']
        if requested == 'image-references':
            report('开始生成项目参考图。', status='planning', current_stage='reference_images')
            self.images.ensure_references(pid, report, cancelled, payload.get('targets'), payload.get('download_confirmation', ''))
            report('参考图已生成并绑定到对应分镜。', status='ready', current_stage='reference_images')
            return 'done'
        if requested in ('finish','rebuild-edit'):
            from .finishing import build, collect_clips, load_recipe
            story=self.projects.get(pid)['story']
            if requested=='rebuild-edit':
                recipe=load_recipe(project,payload['edit_id'])
                clips=[];width,height=recipe['width'],recipe['height'];settings=recipe['settings']
            else:
                recipe=None;clips=collect_clips(project,story)
                width,height=pipeline.output_canvas(pipeline.CONFIG['profiles'][options.profile],options.ratio)
                settings=options.model_dump();settings.update({k:payload[k] for k in ('edit_preset','notes','masks','review_interval') if k in payload})
            report('开始 CPU 质检与后期，原镜头不会重生成。',status='assembling',current_stage='finishing')
            output=build(project,story,clips,width,height,settings,lambda text:report(text),cancelled,recipe,proxy=self.config.renderer_config().get('proxy',''))
            report('质检与后期已完成，原片和历史版本已保留。',status='complete',current_stage='done',output=str(output))
            return 'done'
        if requested not in ('all', 'plan', 'outline', 'storyboard', 'prompt', 'render'):
            raise ValueError('未知任务类型。')
        stages = ['outline', 'storyboard', 'prompt'] if requested in ('all', 'plan', 'render') else [requested]
        for stage in stages:
            if cancelled():
                raise Cancelled('已停止，阶段成果已保存。')
            if stage == 'prompt' and options.reference_images.enabled and requested in ('all', 'plan', 'render'):
                report('正在准备项目角色和场景参考图。', status='planning', current_stage='reference_images')
                self.images.ensure_references(pid, report, cancelled)
            existing = {'outline': project / 'outline.json', 'storyboard': project / '分镜.json', 'prompt': project / '分镜.json'}[stage]
            force = requested == stage and payload.get('force', True)
            done = existing.exists()
            if stage == 'outline' and options.input_mode == 'storyboard':
                continue
            if stage == 'prompt' and done:
                done = all(s.get('prompt') for s in read_json(existing)['shots'])
                # 新版项目保存编译快照，改参数后应重编译。
                for s in read_json(existing)['shots']:
                    snap = s.get('prompt_snapshot')
                    if snap and snap.get('settings_hash') != prompt_settings_hash(options):
                        done = False
            if done and not force:
                continue
            report('正在执行 ' + stage + ' 阶段。', status='planning', current_stage=stage)
            if stage == 'outline':
                self.content.outline(project, options, report, cancelled)
                if force:
                    self.invalidate(project, ('分镜.json',), 'outline-change')
            elif stage == 'storyboard':
                self.content.storyboard(project, options, report, cancelled, reset=force)
            else:
                from .workflow_checks import workflow_report
                check = workflow_report(read_json(project / '分镜.json'), options, self.config.renderer_config(),
                    lambda shot, story: self.assets.resolve(project, shot, story, inspect_media=True), self.content.mode)
                # Stop before asking a text provider to write unusable prompts.
                blockers = [i for i in check['issues'] if i['kind'] == 'workflow' and i['severity'] == 'error']
                if blockers:
                    write_json(project / '出片预检.json', check)
                    report('工作流预检未通过：' + '\n'.join(i['message'] for i in blockers), status='review')
                    return 'review'
                if force:
                    story = read_json(project / '分镜.json')
                    for shot in story['shots']:
                        if not shot.get('locked') and (not payload.get('uids') or shot['uid'] in payload['uids']):
                            shot.pop('prompt_snapshot', None)
                            shot.pop('prompt_manual', None)
                    write_json(project / '分镜.json', story)
                self.content.prompts(project, options, report, cancelled,
                    lambda s, story: self.assets.resolve(project, s, story), uids=payload.get('uids'))
            state = read_json(project / 'state.json', {})
            state.setdefault('stages', {})[stage] = {'status': 'done', 'updated_at': now()}
            write_json(project / 'state.json', state)
            if requested == stage or (requested != 'render' and options.execution_mode == 'review' and stage in options.review_stages and not (stage == 'outline' and options.input_mode != 'idea')):
                report('阶段完成，可以编辑后继续。', status='review', current_stage=stage)
                return 'review'
        if requested == 'plan':
            report('文字规划已完成。', status='ready')
            return 'done'
        if requested in ('all', 'render'):
            if cancelled():
                raise Cancelled('已停止。')
            from .workflow_checks import workflow_report
            preflight = workflow_report(read_json(project / '分镜.json'), options, self.config.renderer_config(),
                lambda shot, story: self.assets.resolve(project, shot, story, inspect_media=True), self.content.mode)
            write_json(project / '出片预检.json', preflight)
            if not preflight['ready']:
                report('出片预检未通过：' + '\n'.join(i['message'] for i in preflight['issues'] if i['severity']=='error'), status='review')
                return 'review'
            lock = project / '.running'
            if lock.exists():
                from .processes import alive
                if alive(int(lock.read_text().strip())):
                    raise RuntimeError('此项目在另一进程中生成。')
                lock.unlink()
            runner = pipeline.Runner(project, callback=lambda state: self.db.update(jid, message=state['message'], event=state))
            image_settings = self.images.environment.settings()
            for url in {image_settings.comfy_url, f'http://127.0.0.1:{image_settings.managed_port}'}-{pipeline.CONFIG['comfy_url'], ''}:
                self.images.release_idle(url,required=True)
            if pipeline.CONFIG['profiles'][options.profile].get('workflow','native') != 'native':
                pipeline.ensure_comfy(report, profile=options.profile, cancel=cancelled)
                runner.engine_prepared = True
            runner.model_versions = fingerprint_models(pipeline.CONFIG, report, cancelled, profile=options.profile)
            write_json(project / 'renderer_snapshot.json', {'models': runner.model_versions, 'environment': {
                k: pipeline.CONFIG.get(k) for k in ('attention', 'profiles')}, 'settings': options.model_dump(), 'created_at': now()})
            def resolve(shot, story, refs):
                bindings = self.assets.resolve(project, shot, story)
                if not any(bindings.values()) and refs:
                    bindings['images'] = [{'id': 'auto-' + str(i), 'type': 'image', 'name': r['name'],
                        'comfy_file': r['image'], 'file': r.get('local_file'), 'sha256': r['sha256'], 'character':r.get('character')} for i, r in enumerate(refs, 1)]
                return self.assets.materialize(project, bindings)
            runner.binding_resolver = resolve
            # Optional workflows must honor the project mode even for manual prompts.
            if pipeline.CONFIG['profiles'][options.profile].get('workflow','native') != 'native' or any(s.get('prompt_snapshot') or s.get('use_previous_last_frame') for s in read_json(project / '分镜.json')['shots']):
                runner.prompt_compiler = lambda story, shot, bindings: self.content.prompt_shot(
                    project, story, shot, options, bindings, report, cancelled)
            class Stop:
                def is_set(self):
                    return cancelled()
            runner.stop = Stop()
            for attempt in range(options.render_retries + 1):
                try:
                    runner.run(limit=payload.get('limit'))
                    break
                except RuntimeError as exc:
                    if isinstance(exc, ProviderError) or cancelled() or attempt >= options.render_retries:
                        raise
                    report(f'生成失败，复用已完成缓存进行有限重试 {attempt + 1}/{options.render_retries}。', status='retrying')
            if runner.state.get('status') == 'paused':
                return 'paused'
        return 'done'

    def invalidate(self, project, names, reason):
        for name in names:
            value = read_json(project / name)
            if value:
                self.projects.version(project, reason, value)
                if name == '分镜.json' and any(s.get('locked') for s in value.get('shots', [])):
                    write_json(project / 'storyboard_locked.json', value)
                (project / name).unlink()
