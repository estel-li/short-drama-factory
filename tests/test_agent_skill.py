"""Exercise the distributed AI client against real API handlers in an isolated store.

No cloud provider or GPU is used. Only the renderer boundary is replaced.
"""
import contextlib
import base64
import copy
import importlib.util
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import api
from app.assets import Assets
from app.config import ConfigStore
from app.content import Content, prompt_valid
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.quality import prompt_cast_valid
from app.schemas import Options, durations
from app.skills import Skills
from app.storage import ROOT, read_json, write_json

SKILL = ROOT / 'agent-skills/short-drama-factory'
spec = importlib.util.spec_from_file_location('factory_skill_client', SKILL / 'scripts/factory_api.py')
client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_module)


class AgentSkillTests(unittest.TestCase):
    def setUp(self):
        import pipeline
        renderer_config = patch.object(pipeline, 'CONFIG', dict(pipeline.CONFIG))
        renderer_config.start()
        self.addCleanup(renderer_config.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/queue.sqlite3')
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.content = Content(self.config, Skills(), self.projects)
        self.worker = Worker(self.db, self.config, self.projects, self.content, self.assets)
        for name, value in (('config', self.config), ('db', self.db), ('projects', self.projects),
                            ('worker', self.worker), ('assets', self.assets)):
            p = patch.object(api, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.api = TestClient(api.app, base_url='http://127.0.0.1')
        self.addCleanup(self.api.close)
        self.calls = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def log_message(self, *args):
                pass

            def forward(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                fixture.calls.append((self.command, self.path))
                if self.path == '/api/lost-response':
                    # A write might have committed before connection loss.
                    self.close_connection = True
                    return
                if self.path == '/api/redirect':
                    self.send_response(302)
                    self.send_header('Location', 'https://example.com/unwanted')
                    self.end_headers()
                    return
                response = fixture.api.request(self.command, self.path, content=body,
                                               headers={'Content-Type': 'application/json'})
                self.send_response(response.status_code)
                self.send_header('Content-Type', response.headers.get('content-type', 'application/octet-stream'))
                self.send_header('Content-Length', str(len(response.content)))
                self.end_headers()
                self.wfile.write(response.content)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.client = client_module.Client(f'http://127.0.0.1:{self.server.server_port}')

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def create(self):
        request = read_json(SKILL / 'assets/project-storyboard.json')
        return self.client.request('POST', '/api/projects', request)['id']

    def test_external_storyboard_can_plan_and_reach_renderer_without_llm(self):
        pid = self.create()
        self.assertEqual(self.db.jobs(), [])  # start:false is intentional
        story = self.client.request('GET', f'/api/project/{pid}')['story']
        for shot in story['shots']:
            self.assertTrue(shot['prompt_manual'])
            prompt_valid(shot['prompt'], 'T2VA', {}, shot['dialogue'], strict_keyframes=True)
        self.assertTrue(self.client.request('GET', f'/api/projects/{pid}/preflight')['ready'])
        self.assertEqual(self.client.request('POST', '/api/duration-plan',
                         read_json(SKILL / 'assets/project-storyboard.json')['options'])['frames'], [107, 107])
        with patch.object(self.content, 'call', side_effect=AssertionError('Unexpected paid LLM call')):
            jid = self.client.request('POST', f'/api/projects/{pid}/stage/plan', {})['job_id']
            job = self.db.claim()
            self.assertEqual(job['id'], jid)
            self.assertEqual(self.worker.execute(job), 'done')
            self.db.update(jid, 'done')
            # A done planning job is not proof of a final video.
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(client_module.watch(self.client, pid, jid), 0)
            self.assertFalse(json.loads(output.getvalue())['final'])
            self.client.request('POST', f'/api/projects/{pid}/stage/render', {'limit': 1})
            job = self.db.claim()
            with patch('pipeline.Runner') as runner, patch('app.jobs.fingerprint_models', return_value={}):
                runner.return_value.state = {}
                self.assertEqual(self.worker.execute(job), 'done')
                runner.return_value.run.assert_called_once_with(limit=1)
                self.assertEqual(runner.call_args.args[0], self.projects.path(pid))
            self.db.update(job['id'], 'done')
        final_story = self.client.request('GET', f'/api/project/{pid}')['story']
        self.assertEqual(story, final_story)

    def test_outline_template_and_existing_settings_are_valid(self):
        request = read_json(SKILL / 'assets/project-outline.json')
        self.assertEqual(durations(Options.model_validate(request['options']))['count'], 6)
        pid = self.client.request('POST', '/api/projects', request)['id']
        project = self.client.request('GET', f'/api/project/{pid}')
        settings = project['settings']
        settings['profile'] = 'dialogue'
        self.client.request('POST', f'/api/projects/{pid}/settings', settings)
        saved = self.client.request('GET', f'/api/project/{pid}')['settings']
        self.assertEqual(saved['stages'], request['options']['stages'])
        self.assertEqual(saved['profile'], 'dialogue')

    def test_edit_preserves_uids_and_asset_binding_resolves(self):
        pid = self.create()
        image = self.root / '首帧.png'
        Image.new('RGB', (16, 16), 'blue').save(image)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = client_module.main(['--base-url', self.client.base, 'asset', '--project', pid,
                                       '--file', str(image), '--kind', 'image'])
        self.assertEqual(code, 0)
        aid = json.loads(stdout.getvalue())['id']
        story = self.client.request('GET', f'/api/project/{pid}')['story']
        uid = story['shots'][0]['uid']
        story['shots'][0].update(mode='I2VA', bindings={'first_frame': aid}, prompt='')
        validated = self.client.request('POST', f'/api/projects/{pid}/validate-story', {'story': story})
        self.client.request('POST', '/api/story', {'id': pid, 'story': validated})
        saved = self.client.request('GET', f'/api/project/{pid}')['story']
        self.assertEqual(saved['shots'][0]['uid'], uid)
        resolved = self.assets.resolve(self.projects.path(pid), saved['shots'][0], saved)
        self.assertEqual(resolved['first_frame']['id'], aid)

    def test_watch_active_review_error_unknown_and_mismatched_jobs(self):
        pid = self.create()
        jid = self.client.request('POST', f'/api/projects/{pid}/stage/plan', {})['job_id']
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client_module.watch(self.client, pid, jid, seconds=.05), 3)
            self.assertEqual(self.db.jobs()[0]['status'], 'queued')
            for status in ('review', 'paused', 'error'):
                self.db.update(jid, status)
                self.assertEqual(client_module.watch(self.client, pid, jid), 2)
            self.assertEqual(client_module.watch(self.client, pid, 'missing'), 4)
            other = self.create()
            with self.assertRaises(client_module.APIError):
                client_module.watch(self.client, other, jid)
        self.assertFalse(any(method == 'POST' and path.endswith('/api/stop') for method, path in self.calls))

    def test_download_unicode_and_never_overwrite(self):
        pid = self.create()
        expected = '已保存的字幕内容'.encode('utf-8')
        (self.projects.path(pid) / '字幕.srt').write_bytes(expected)
        target = self.root / 'download/字幕.srt'
        result = self.client.download(f'/media/{pid}/字幕.srt', target)
        self.assertEqual(result['size'], len(expected))
        self.assertEqual(target.read_bytes(), expected)
        with self.assertRaises(FileExistsError):
            self.client.download(f'/media/{pid}/字幕.srt', target)
        self.assertEqual(target.read_bytes(), expected)

    def test_write_connection_loss_does_not_retry_and_redirect_is_rejected(self):
        with self.assertRaises(client_module.APIError):
            self.client.request('POST', '/api/lost-response', {})
        self.assertEqual(self.calls.count(('POST', '/api/lost-response')), 1)
        with self.assertRaises(client_module.APIError):
            self.client.request('GET', '/api/redirect')
        for url in ('https://example.com', 'http://localhost@evil.example', 'http://localhost:8765/path'):
            with self.assertRaises(client_module.APIError):
                client_module.Client(url)
        with self.assertRaises(client_module.APIError):
            self.client.request('GET', '//example.com/api/health')

    def test_utf8_bom_json_and_error_body_do_not_echo_payload(self):
        path = self.root / '请求.json'
        path.write_text('{"input":"中文"}', encoding='utf-8-sig')
        self.assertEqual(client_module.load_body(path), {'input': '中文'})
        with self.assertRaises(client_module.APIError) as error:
            self.client.request('POST', '/api/projects', {'input': '', 'options': {'private_token': 'never-echo-me'}})
        self.assertNotIn('never-echo-me', str(error.exception))

    def test_diagnose_is_read_only_and_uses_recorded_frames_after_edit(self):
        pid = self.create()
        story = self.client.request('GET', f'/api/project/{pid}')['story']
        uid = story['shots'][0]['uid']
        record = {'status': 'done', 'media': {'frames': 107}, 'sampling_prompt_id': 'sample-1',
                  'timings': {'sampling': {'seconds': 214, 'prompt_id': 'sample-1'}}}
        path = self.projects.path(pid) / 'state.json'
        write_json(path, {'shots_by_uid': {uid: record}, 'shots': {'1': record}})
        story['shots'][0]['duration'] = 8
        self.client.request('POST', '/api/story', {'id': pid, 'story': story})
        before = path.read_bytes()
        start = len(self.calls)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = client_module.main(['--base-url', self.client.base, 'diagnose', '--project', pid])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(all(method == 'GET' for method, _ in self.calls[start:]))
        self.assertEqual(path.read_bytes(), before)
        row = report['shots'][0]
        self.assertEqual((row['planned_frames'], row['recorded_frames'], row['recorded_seconds_per_frame']), (192, 107, 2))
        self.assertTrue(row['changed_since_render'])
        self.assertIn('missing_prompt', [i['kind'] for i in report['issues']])
        self.assertIsNone(report['shots'][1]['recorded_seconds_per_frame'])
        self.assertEqual(self.db.jobs(), [])

    def test_diagnose_does_not_mix_old_position_or_unfinished_sampling(self):
        pid = self.create()
        project = self.projects.get(pid)
        uid = project['story']['shots'][0]['uid']
        record = {'status': 'done', 'media': {'frames': 107}, 'sampling_prompt_id': 'new',
                  'timings': {'sampling': {'seconds': 214, 'prompt_id': 'old'}}}
        project['state'] = {'shots_by_uid': {uid: record}, 'shots': {'2': record}}
        report = client_module.project_diagnostics(project, [], {})
        self.assertTrue(all(row['recorded_seconds_per_frame'] is None for row in report['shots']))
        self.assertIsNone(report['shots'][1]['record_status'])
        record['timings']['sampling']['prompt_id'] = 'new'
        record['status'] = 'queued'
        self.assertIsNone(client_module.project_diagnostics(project, [], {})['shots'][0]['recorded_seconds_per_frame'])

    def test_scene_identity_mistag_can_be_repaired_via_api_without_fake_character(self):
        pid = self.create()
        image = io.BytesIO()
        Image.new('RGB', (16, 16), 'blue').save(image, format='PNG')
        upload = {'type': 'image', 'name': 'scene.png', 'data': base64.b64encode(image.getvalue()).decode('ascii')}
        wrong = self.client.request('POST', f'/api/projects/{pid}/assets', {**upload, 'character': 'hall'})
        story = self.client.request('GET', f'/api/project/{pid}')['story']
        shot = story['shots'][0]
        shot.update(mode='Ref2VA', bindings={'images': [wrong['id']]},
                    prompt='subject_definitions:\nEmpty room in <Picture 1>.\nsummary:\nA quiet room.\n'
                           'retention_analysis:\nKeep the room layout.\ndetailed_description:\n'
                           '[Shot 1] 0.0-4.46s. Curtains move gently.\noverall_soundscape:\nSoft wind.\nnon_diegetic_music:\nN/A')
        self.client.request('POST', '/api/story', {'id': pid, 'story': story})
        report = client_module.diagnose(self.client, pid)
        self.assertIn('asset_character_not_in_shot', [i['kind'] for i in report['issues']])
        correct = self.client.request('POST', f'/api/projects/{pid}/assets', upload)
        story = self.client.request('GET', f'/api/project/{pid}')['story']
        story['shots'][0]['bindings']['images'] = [correct['id']]
        checked = self.client.request('POST', f'/api/projects/{pid}/validate-story', {'story': story})
        self.client.request('POST', '/api/story', {'id': pid, 'story': checked})
        saved = self.projects.get(pid)['story']
        self.assertEqual(saved['characters'], [])
        self.assertEqual(saved['shots'][0]['uid'], shot['uid'])
        self.assertEqual(client_module.diagnose(self.client, pid)['issues'][0]['kind'], 'missing_prompt')
        bindings = self.assets.resolve(self.projects.path(pid), saved['shots'][0], saved)
        prompt_cast_valid('', saved, saved['shots'][0], bindings, 'Ref2VA')
        self.assertFalse(bindings['images'][0].get('character'))

    def test_inserted_shot_retains_existing_uid_seed_and_records(self):
        pid = self.create()
        story = self.projects.get(pid)['story']
        original = copy.deepcopy(story['shots'])
        records = {s['uid']: {'status': 'done', 'media': {'frames': 107}} for s in original}
        write_json(self.projects.path(pid) / 'state.json', {'shots_by_uid': records})
        inserted = copy.deepcopy(original[0])
        inserted.update(uid='new-scene-unique', seed=234567, seed_offset=99)
        story['shots'].insert(1, inserted)
        self.client.request('POST', '/api/story', {'id': pid, 'story': story})
        saved = self.projects.get(pid)
        self.assertEqual([s['uid'] for s in saved['story']['shots']], [original[0]['uid'], inserted['uid'], original[1]['uid']])
        self.assertEqual(saved['story']['shots'][2]['seed_offset'], original[1]['seed_offset'])
        self.assertEqual(saved['state']['shots']['3'], records[original[1]['uid']])
        self.assertEqual(saved['state']['shots']['2'], {})


if __name__ == '__main__':
    unittest.main()
