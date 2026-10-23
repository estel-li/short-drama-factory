"""Reference evidence → authored Skill → frozen production → film review, no GPU."""
import copy
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import pipeline
import uvicorn
from app import api
from app.director_contracts import PrepareReference, PublishDirectorStyle
from app.director_media import prepare, sha256
from app.director_styles import DirectorStyles, binding, project_brief, package_files
from app.jobs import Worker
from app.storage import ROOT, read_json, write_json
import tests.test_agent_api as fixture


class DirectorStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.source = Path(cls.temp.name).resolve() / 'reference.mp4'
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=24:d=1',
                         '-f', 'lavfi', '-i', 'color=c=red:s=96x64:r=24:d=1',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=2',
                         '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-map', '2:a',
                         '-c:v', 'libx264', '-bf', '0', '-c:a', 'aac', '-t', '2', cls.source])
        cls.prepared = Path(cls.temp.name).resolve() / 'prepared'
        request = PrepareReference(source_path=str(cls.source), source_sha256=sha256(cls.source),
                                   sample_seconds=.25, max_frames=20, max_clips=1)
        prepare(cls.prepared, request, lambda message: None, lambda: False)

    def setUp(self):
        fixture.AgentAPITests.setUp(self)
        environment = patch.dict('os.environ', {'SDF_STYLE_HOME': str(self.root / 'director-library')})
        environment.start()
        self.addCleanup(environment.stop)
        self.library = DirectorStyles()
        self.aid = 'reference-fixture'
        self.folder = self.library.analysis_path(self.aid)
        shutil.copytree(self.prepared, self.folder)
        self.request = PrepareReference(source_path=str(self.source), source_sha256=sha256(self.source),
                                        sample_seconds=.25, max_frames=20, max_clips=1).model_dump()
        write_json(self.folder / 'request.json', {'request': self.request})
        self.document = {'style_id': 'blue-action', 'analysis_id': self.aid, 'name': '导演风格测试',
                         'summary': '蓝红反差与明确动作切点；这是离线测试规则，不是用户影片的分析结论。',
                         'coverage': {'frames': [{'start': 0, 'end': 2}], 'motion': [{'start': 0, 'end': 2}],
                                      'audio': [{'start': 0, 'end': 2}]},
                         'rules': [{'id': 'blue-space', 'dimension': 'visual', 'observation': '前半段画面为蓝色。',
                                    'guidance': '新故事的安静场景使用冷色空间。', 'when': '安静铺垫', 'basis': 'frames',
                                    'evidence': [{'start': 0, 'end': 1}]},
                                   {'id': 'cut-on-action', 'dimension': 'editing', 'observation': '约1秒时切换画面。',
                                    'guidance': '动作转折点使用明确切口。', 'when': '转折', 'basis': 'motion',
                                    'evidence': [{'start': .8, 'end': 1.2}]}],
                         'shot_structure': [{'id': 'reference-one', 'start': 0, 'end': 1, 'purpose': '铺垫', 'rules': ['blue-space']},
                                            {'id': 'reference-two', 'start': 1, 'end': 2, 'purpose': '转折', 'rules': ['cut-on-action']}],
                         'limitations': ['测试媒体没有人物、打斗或语义对白；不推断这些内容。']}
        for target in ('requests.sessions.Session.request', 'pipeline.Runner.run'):
            item = patch(target, side_effect=AssertionError('No provider, engine, GPU or download'))
            item.start()
            self.addCleanup(item.stop)
        for name in ('start', 'allow_job'):
            item = patch.object(self.worker, name)
            item.start()
            self.addCleanup(item.stop)

    def post(self, path, body, key):
        return self.client.post('/api/v2/' + path, json=body, headers={'Idempotency-Key': key})

    def publish(self, key='publish', document=None):
        response = self.post('director/styles', document or self.document, key)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def project(self):
        request = read_json(ROOT / 'agent-skills/short-drama-factory/assets/agent-storyboard.json')
        result = self.post('projects', request, 'create-project')
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()['id']

    def bind(self, pid, version, mode='inspired', key='bind'):
        body = {'expected_revision': self.projects.revision(pid), 'style_id': 'blue-action', 'version': version, 'mode': mode}
        result = self.post('projects/' + pid + '/director-style', body, key)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json(), body

    def test_actual_cpu_evidence_contains_decodable_frames_clips_and_audio_measurements(self):
        data = read_json(self.folder / 'evidence.json')
        self.assertEqual(data['semantic_analysis'], 'not_performed')
        self.assertTrue(data['media']['video'])
        self.assertTrue(data['media']['audio'])
        self.assertTrue(data['audio_levels'])
        self.assertTrue(any(row['kind'] == 'contact_sheet' for row in data['artifacts']))
        self.assertTrue(any(row['kind'] == 'motion_sequence' for row in data['artifacts']))
        self.assertTrue(any(.9 <= row['time'] <= 1.1 for row in data['candidate_cuts']))
        import av
        for item in data['artifacts']:
            self.assertEqual(sha256(self.folder / item['path']), item['sha256'])
            if item['kind'] == 'motion_clip':
                with av.open(str(self.folder / item['path'])) as clip:
                    self.assertTrue(list(clip.decode(video=0)))
        original = sha256(self.source)
        value = self.client.get('/api/v2/director/analyses/' + self.aid).json()
        first = value['artifacts'][0]
        response = self.client.get(first['api_url'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content), first['size'])
        self.assertEqual(self.client.get('/api/v2/director/analyses/' + self.aid + '/files/request.json').status_code, 404)
        self.assertEqual(sha256(self.source), original)

    def test_prepare_job_is_durable_replayable_and_executes_cpu_only(self):
        result = self.post('director/analyses', self.request, 'prepare')
        self.assertEqual(result.status_code, 202, result.text)
        value = result.json()
        self.assertEqual(self.post('director/analyses', self.request, 'prepare').json(), value)
        job = self.db.claim({value['job_id']})
        self.assertEqual(self.worker.execute(job), 'done')
        self.db.update(job['id'], 'done')
        prepared = self.client.get('/api/v2/director/analyses/' + value['analysis_id']).json()
        self.assertEqual(prepared['status'], 'prepared')
        self.assertEqual(prepared['job_status'], 'done')
        self.assertEqual(len(self.db.jobs()), 1)

    def test_publish_creates_self_contained_skill_and_recovers_lost_database_receipt(self):
        complete = self.db.complete_operation
        with patch.object(self.db, 'complete_operation', side_effect=OSError('fixture response failure')):
            failed = self.post('director/styles', self.document, 'lost-publish')
            self.assertGreaterEqual(failed.status_code, 400)
        result = self.publish('lost-publish')
        folder = Path(result['directory'])
        manifest, profile = package_files(folder)
        self.assertEqual(profile['version'], result['version'])
        self.assertIn('默认创作全新故事', (folder / 'SKILL.md').read_text(encoding='utf-8'))
        self.assertTrue((folder / 'references/shot-structure.json').is_file())
        self.assertTrue(any(name.startswith('evidence/clips/') for name in manifest['files']))
        self.assertNotIn(str(self.source), (folder / 'style.json').read_text(encoding='utf-8'))
        self.assertEqual(self.publish('lost-publish'), result)
        self.assertEqual(len(list((folder.parent).iterdir())), 1)

    def test_unviewed_motion_or_missing_audio_cannot_be_published_as_observed(self):
        invalid = copy.deepcopy(self.document)
        invalid['coverage']['motion'] = []
        self.assertEqual(self.post('director/styles', invalid, 'unviewed').json()['code'], 'DIRECTOR_EVIDENCE_UNVIEWED')
        invalid = copy.deepcopy(self.document)
        invalid['rules'][1]['basis'] = 'frames'
        self.assertEqual(self.post('director/styles', invalid, 'still-motion').json()['code'], 'DIRECTOR_EVIDENCE_MODALITY')
        invalid = copy.deepcopy(self.document)
        invalid['rules'][0]['evidence'] = [{'start': 0, 'end': 3}]
        self.assertEqual(self.post('director/styles', invalid, 'outside').json()['code'], 'DIRECTOR_EVIDENCE_UNVIEWED')

    def test_frozen_project_survives_library_update_and_binding_receipt_failure(self):
        first = self.publish()
        pid = self.project()
        before = self.projects.revision(pid)
        selection, body = self.bind(pid, first['version'])
        self.assertNotEqual(before, selection['revision'])
        self.assertEqual(selection['revision'], self.projects.revision(pid))
        update = copy.deepcopy(self.document)
        update['expected_version'] = first['version']
        update['rules'][0]['guidance'] = '后续新版本使用另一套指导。'
        second = self.publish('new-version', update)
        self.assertNotEqual(first['version'], second['version'])
        self.assertEqual(self.projects.revision(pid), selection['revision'])
        self.assertIn('冷色空间', project_brief(self.projects.path(pid)))
        self.assertEqual(self.post('projects/' + pid + '/director-style', body, 'bind').json(), selection)
        changed = {**body, 'expected_revision': selection['revision'], 'version': second['version']}
        with patch.object(self.db, 'complete_operation', side_effect=OSError('fixture response failure')):
            self.assertGreaterEqual(self.post('projects/' + pid + '/director-style', changed, 'lost-bind').status_code, 400)
        recovered = self.post('projects/' + pid + '/director-style', changed, 'lost-bind')
        self.assertEqual(recovered.status_code, 200, recovered.text)
        self.assertEqual(recovered.json()['revision'], self.projects.revision(pid))

    def test_explicit_remake_checks_structure_and_changed_snapshot_blocks_plan(self):
        result = self.publish()
        pid = self.project()
        selection, _ = self.bind(pid, result['version'], 'remake')
        value = self.client.get('/api/v2/projects/' + pid + '/director-style').json()
        self.assertIn('用户已明确选择结构仿拍', value['brief'])
        # Fixture has two authored shots; the count check uses the actual storyboard.
        self.assertEqual(value['check']['ready'], len(self.projects.get(pid)['story']['shots']) == 2)
        path = self.projects.path(pid) / selection['selection']['package'] / 'references/visual.md'
        path.write_text('tampered guidance', encoding='utf-8')
        plan = self.post('projects/' + pid + '/plans', {}, 'inspect-plan')
        self.assertEqual(plan.status_code, 201, plan.text)
        self.assertFalse(plan.json()['ready'])
        self.assertIn('DIRECTOR_PACKAGE_CHANGED', [item['code'] for item in plan.json()['blocked']])

    def test_install_preserves_existing_files_and_does_not_need_source_movie(self):
        result = self.publish()
        target = self.root / 'user-ai-skills/sdf-director-blue-action'
        path = 'director/styles/blue-action/versions/' + result['version'] + '/install'
        installed = self.post(path, {'target_directory': str(target)}, 'install')
        self.assertEqual(installed.status_code, 201, installed.text)
        self.assertEqual(package_files(target)[1]['version'], result['version'])
        self.assertEqual(self.post(path, {'target_directory': str(target)}, 'install').json(), installed.json())
        (target / 'personal.txt').write_text('keep')
        self.assertEqual(self.post(path, {'target_directory': str(target)}, 'other-install').status_code, 409)
        self.assertEqual((target / 'personal.txt').read_text(), 'keep')

    def test_portable_package_import_into_a_new_library_recovers_without_original_source(self):
        published = self.publish()
        incoming = self.root / 'incoming-style'
        shutil.copytree(published['directory'], incoming)
        body = {'package_directory': str(incoming), 'manifest_sha256': sha256(incoming / 'manifest.json'),
                'style_id': published['style_id'], 'version': published['version']}
        with patch.dict('os.environ', {'SDF_STYLE_HOME': str(self.root / 'new-user-library')}), \
                patch.object(DirectorStyles, 'analysis', side_effect=AssertionError('Imported Skills must not need old analysis')):
            with patch.object(self.db, 'complete_operation', side_effect=OSError('fixture receipt lost')):
                self.assertEqual(self.post('director/styles/import', body, 'import-style').status_code, 503)
            renamed = self.root / 'removed-incoming-style'
            self.assertTrue(incoming.resolve().is_relative_to(self.root.resolve()))
            self.assertTrue(renamed.resolve().is_relative_to(self.root.resolve()))
            incoming.rename(renamed)
            recovered = self.post('director/styles/import', body, 'import-style')
            self.assertEqual(recovered.status_code, 201, recovered.text)
            self.assertEqual(recovered.json()['version'], published['version'])
            self.assertTrue(DirectorStyles().get(published['style_id'])['profile']['evidence'])

    def test_review_is_bound_to_actual_final_bytes_and_never_implies_automatic_similarity(self):
        result = self.publish()
        pid = self.project()
        self.bind(pid, result['version'])
        project = self.projects.path(pid)
        shutil.copy2(self.source, project / '成片.mp4')
        write_json(project / 'state.json', {'status': 'complete'})
        before = self.client.get('/api/v2/projects/' + pid + '/delivery?verify=true').json()
        self.assertEqual(before['checks']['director_style']['status'], 'not_checked')
        review = {'expected_revision': self.projects.revision(pid), 'final_sha256': sha256(project / '成片.mp4'),
                  'assessments': [{'rule_id': rule['id'], 'status': 'passed', 'note': '离线测试查看记录',
                                   'evidence': [{'start': 0, 'end': 1}]} for rule in self.document['rules']]}
        response = self.post('projects/' + pid + '/director-style/review', review, 'review')
        self.assertEqual(response.status_code, 200, response.text)
        after = self.client.get('/api/v2/projects/' + pid + '/delivery').json()
        self.assertTrue(after['style_review_complete'])
        self.assertEqual(after['checks']['director_style']['method'], 'external_authored_review')
        (project / '成片.mp4').write_bytes(b'changed final')
        stale = self.client.get('/api/v2/projects/' + pid + '/director-style').json()
        self.assertEqual(stale['review']['status'], 'stale')

    def test_internal_creation_receives_the_frozen_director_rules(self):
        published = self.publish()
        pid = self.project()
        self.bind(pid, published['version'])
        project = self.projects.path(pid)
        with patch('app.content.LLMClient') as provider:
            provider.return_value.generate.return_value = {'text': '{"title":"new story"}', 'model': 'fixture', 'usage': {}}
            value, snapshot = self.content.call(project, 'outline', self.projects.options(project), {'task': 'outline'},
                {'type': 'object'}, lambda value: value, lambda text: None, lambda: False)
            messages = provider.return_value.generate.call_args.args[0]
        data = json.loads(messages[1]['content'])
        self.assertIn('冷色空间', data['director_guidance'])
        self.assertIn('全新故事', data['director_guidance'])
        self.assertEqual(data['director_style']['version'], published['version'])
        self.assertEqual(snapshot['director_style'], binding(project))

    def test_audio_only_reference_keeps_visual_dimensions_unavailable(self):
        audio = self.root / 'reference.wav'
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'sine=frequency=330:sample_rate=48000:duration=1', audio])
        request = PrepareReference(source_path=str(audio), source_sha256=sha256(audio), max_clips=1)
        folder = self.library.analysis_path('audio-only')
        write_json(folder / 'request.json', {'request': request.model_dump()})
        evidence = prepare(folder, request, lambda message: None, lambda: False)
        self.assertFalse(evidence['media']['video'])
        self.assertEqual(evidence['media']['audio_sample_rate'], 48000)
        self.assertTrue(evidence['audio_levels'])
        self.assertFalse(any(item['kind'] == 'frame' for item in evidence['artifacts']))
        body = copy.deepcopy(self.document)
        body.update(style_id='audio-style', analysis_id='audio-only', shot_structure=[],
                    coverage={'audio': [{'start': 0, 'end': 1}]},
                    rules=[{'id': 'steady-tone', 'dimension': 'sound', 'observation': '测试持续音', 'guidance': '需要持续背景层时参考稳定音色。',
                            'basis': 'audio', 'evidence': [{'start': 0, 'end': 1}]}])
        self.assertEqual(self.post('director/styles', body, 'audio-publish').status_code, 201)
        body['coverage']['frames'] = [{'start': 0, 'end': 1}]
        self.assertEqual(self.post('director/styles', body, 'audio-invalid').json()['code'], 'DIRECTOR_VERSION_CONFLICT')
        body['style_id'] = 'invalid-visual'
        self.assertEqual(self.post('director/styles', body, 'audio-invalid-new').json()['code'], 'DIRECTOR_COVERAGE_INVALID')

    def test_lost_review_receipt_replay_does_not_replace_a_later_review(self):
        published = self.publish()
        pid = self.project()
        self.bind(pid, published['version'])
        project = self.projects.path(pid)
        shutil.copy2(self.source, project / '成片.mp4')
        body = {'expected_revision': self.projects.revision(pid), 'final_sha256': sha256(project / '成片.mp4'),
                'assessments': [{'rule_id': rule['id'], 'status': 'passed', 'note': 'first inspection',
                                 'evidence': [{'start': 0, 'end': 1}]} for rule in self.document['rules']]}
        path = 'projects/' + pid + '/director-style/review'
        with patch.object(self.db, 'complete_operation', side_effect=OSError('fixture receipt lost')):
            self.assertEqual(self.post(path, body, 'first-review').status_code, 503)
        changed = copy.deepcopy(body)
        changed['assessments'][0]['status'] = 'failed'
        self.assertEqual(self.post(path, changed, 'later-review').status_code, 200)
        self.assertEqual(self.post(path, body, 'first-review').status_code, 200)
        self.assertEqual(self.client.get('/api/v2/projects/' + pid + '/director-style').json()['review']['status'], 'failed')

    def test_source_change_cancel_and_extra_evidence_keep_one_analysis_identity(self):
        extra = self.post('director/analyses/' + self.aid + '/clips', {'start': .5, 'end': 1.5}, 'extra-clip')
        self.assertEqual(extra.status_code, 202, extra.text)
        self.assertEqual(extra.json(), self.post('director/analyses/' + self.aid + '/clips', {'start': .5, 'end': 1.5}, 'extra-clip').json())
        job = self.db.claim({extra.json()['job_id']})
        self.assertEqual(self.worker.execute(job), 'done')
        self.db.update(job['id'], 'done')
        self.assertTrue(any(item['path'].startswith('clips/extra-') for item in self.library.analysis(self.aid)['artifacts']))
        changed = {**self.request, 'source_sha256': 'a' * 64}
        queued = self.post('director/analyses', changed, 'bad-source').json()
        job = self.db.claim({queued['job_id']})
        with self.assertRaisesRegex(ValueError, '哈希不同'):
            self.worker.execute(job)
        self.db.update(job['id'], 'error')
        queued = self.post('director/analyses', self.request, 'cancel-source').json()
        stopped = self.post('jobs/' + queued['job_id'] + '/stop', {}, 'stop-source')
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(self.db.job(queued['job_id'])['status'], 'paused')
        resumed = self.post('jobs/' + queued['job_id'] + '/resume', {}, 'resume-source')
        self.assertEqual(resumed.json()['job_id'], queued['job_id'])

    def test_quick_cut_finishing_reuses_sources_and_reports_planned_relative_rhythm(self):
        from app.finishing import build
        from app.quality import render_contract
        published = self.publish()
        pid = self.project()
        self.bind(pid, published['version'], mode='remake')
        project = self.projects.path(pid)
        story = self.projects.get(pid)['story']
        original_prompts = [shot['prompt'] for shot in story['shots']]
        originals = [render_contract(story, shot) for shot in story['shots']]
        for shot in story['shots']:
            shot['edit_ranges'] = [{'start': .5, 'end': 1}]
        saved = self.projects.save_story(pid, story)
        self.assertEqual([shot['prompt'] for shot in saved['shots']], original_prompts)
        self.assertEqual([render_contract(saved, shot) for shot in saved['shots']], originals)
        check = self.client.get('/api/v2/projects/' + pid + '/director-style').json()['check']
        self.assertTrue(check['timing']['relative_rhythm_matches'])
        self.assertEqual(check['timing']['planned_output_seconds'], [.5, .5])
        # A real CPU cut independently proves sub-generation-length output.
        source = project / 'fixture-source.mp4'
        shutil.copy2(self.source, source)
        evidence_story = {'title': 'quick cuts', 'characters': [], 'shots': [
            {'id': i + 1, 'uid': 'cut-' + str(i), 'duration': 4, 'dialogue': [],
             'edit_ranges': [{'start': .5, 'end': 1}]} for i in range(2)]}
        checksum, modified = sha256(source), source.stat().st_mtime_ns
        build(project, evidence_story, [source, source], 96, 64,
              {'edit_preset': 'original', 'subtitle_alignment': 'approximate', 'subtitles': False})
        report = read_json(project / '媒体验收.json')
        self.assertEqual(report['expected_frames'], 24)
        self.assertEqual(report['final']['frames'], 24)
        self.assertEqual((sha256(source), source.stat().st_mtime_ns), (checksum, modified))

    def test_standard_migration_keeps_complete_director_snapshot_even_without_generated_videos(self):
        import zipfile
        from app.transfer import Transfer
        published = self.publish()
        pid = self.project()
        self.bind(pid, published['version'])
        exporter = Transfer(self.config, self.projects, self.content.skills)
        archive = exporter.export([pid], include_videos=False)
        restored = self.root / 'restored'
        restored.mkdir()
        with zipfile.ZipFile(archive) as incoming:
            prefix = 'projects/' + pid + '/'
            for name in incoming.namelist():
                if name.startswith(prefix):
                    target = restored / name.removeprefix(prefix)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(incoming.read(name))
        selected = binding(restored)
        self.assertEqual(selected['version'], published['version'])
        self.assertEqual(package_files(restored / selected['package'])[1]['version'], published['version'])
        self.assertIn('冷色空间', project_brief(restored))

    def test_copied_cli_real_http_flow_prepares_publishes_binds_and_installs(self):
        portable = self.root / 'independent-cli'
        shutil.copytree(ROOT / 'agent-skills/short-drama-factory/scripts', portable)
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen()
        address = f'http://127.0.0.1:{sock.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(api.app, log_level='error', lifespan='off'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        def close():
            self.worker.shutdown.set()
            self.worker.wake.set()
            if self.worker.thread:
                self.worker.thread.join(timeout=10)
                self.assertFalse(self.worker.thread.is_alive())
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
            self.assertFalse(thread.is_alive())
        self.addCleanup(close)
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(server.started)
        def cli(*args):
            result = subprocess.run([sys.executable, '-I', str(portable / 'sdf.py'), '--base-url', address,
                                     '--context', str(portable / '.sdf/connection.json'), *args], cwd=portable,
                                    capture_output=True, encoding='utf-8', timeout=45,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return [json.loads(line) for line in result.stdout.splitlines()][-1]
        with patch.object(self.worker, 'start', Worker.start.__get__(self.worker)), \
                patch.object(self.worker, 'allow_job', Worker.allow_job.__get__(self.worker)), \
                patch('app.api.httpx.get', side_effect=api.httpx.ConnectError('isolated test engine')):
            queued = cli('style', 'prepare', '--video', str(self.source), '--max-frames', '8', '--max-clips', '1', '--request-key', 'cli-prepare')
            deadline = time.monotonic() + 20
            while self.db.job(queued['job_id'])['status'] in ('queued', 'running') and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertEqual(self.db.job(queued['job_id'])['status'], 'done', self.db.job(queued['job_id']))
            self.assertEqual(cli('style', 'analysis', queued['analysis_id'])['status'], 'prepared')
            extra = cli('style', 'clip', queued['analysis_id'], '--start', '0.4', '--end', '1.4')
            deadline = time.monotonic() + 20
            while self.db.job(extra['job_id'])['status'] in ('queued', 'running') and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertEqual(self.db.job(extra['job_id'])['status'], 'done', self.db.job(extra['job_id']))
            document = copy.deepcopy(self.document)
            document['analysis_id'] = queued['analysis_id']
            write_json(portable / 'authored.json', document)
            published = cli('style', 'publish', '--json', str(portable / 'authored.json'), '--request-key', 'cli-publish')
            self.assertEqual(cli('style', 'publish', '--json', str(portable / 'authored.json'), '--request-key', 'cli-publish'), published)
            pid = self.project()
            selected = cli('style', 'bind', '--project', pid, '--style', document['style_id'], '--version', published['version'], '--request-key', 'cli-bind')
            self.assertEqual(selected['selection']['mode'], 'inspired')
            self.assertIn('冷色空间', cli('style', 'brief', '--project', pid)['brief'])
            installed = cli('style', 'install', '--style', document['style_id'], '--version', published['version'], '--target', str(self.root / 'installed-style'))
            self.assertTrue((Path(installed['directory']) / 'SKILL.md').is_file())
            cli('style', 'clear', '--project', pid)
            self.assertEqual(binding(self.projects.path(pid)), {})


if __name__ == '__main__':
    unittest.main()
