"""Portable task CLI against actual handlers, with the renderer/worker disabled."""
import contextlib
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import api
from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


SCRIPTS = ROOT / 'agent-skills/short-drama-factory/scripts'
spec = importlib.util.spec_from_file_location('factory_api', SCRIPTS / 'factory_api.py')
factory = importlib.util.module_from_spec(spec)
sys.modules['factory_api'] = factory
spec.loader.exec_module(factory)
spec = importlib.util.spec_from_file_location('sdf_tasks', SCRIPTS / 'sdf.py')
sdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdf)


class TaskCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = self.root / '.sdf/connection.json'
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/jobs.sqlite3')
        self.mock('app.projects.ROOT', self.root)
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.content = Content(self.config, Skills(), self.projects)
        self.worker = Worker(self.db, self.config, self.projects, self.content, self.assets)
        for name in ('config', 'db', 'projects', 'assets', 'content', 'worker'):
            self.mock_object(api, name, getattr(self, name))
        self.mock_object(self.worker, 'start')
        self.mock_object(self.worker, 'allow_job')
        self.mock_object(self.content, 'call', side_effect=AssertionError('No text generation'))
        self.mock('requests.sessions.Session.request', side_effect=AssertionError('No provider/engine network'))
        self.mock('pipeline.Runner.run', side_effect=AssertionError('No GPU execution'))
        self.mock('app.execution_plan._model_observations', return_value=[])
        self.api = TestClient(api.app, base_url='http://127.0.0.1')
        self.addCleanup(self.api.close)
        self.calls, self.ledger_errors = [], []
        self.drop_key = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def do_PATCH(self):
                self.forward()

            def forward(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                key = self.headers.get('Idempotency-Key')
                owner.calls.append((self.command, self.path, key))
                if self.path == '/api/health':
                    value = {'application_root': str(owner.root), 'protocol_version': 1, 'app_version': '3.9.0'}
                    status, payload = 200, json.dumps(value).encode('utf-8')
                else:
                    if self.command in ('POST', 'PATCH') and self.path != '/api/provider/key' and not self.path.endswith('/compile'):
                        ledger = owner.context.parent / 'requests' / ((key or 'missing') + '.json')
                        try:
                            record = json.loads(ledger.read_text(encoding='utf-8'))
                            if record['status'] != 'submitted' or record['body'] != json.loads(raw):
                                owner.ledger_errors.append('request not durably recorded before network')
                        except (OSError, ValueError, KeyError):
                            owner.ledger_errors.append('missing request ledger')
                    response = owner.api.request(self.command, self.path, content=raw,
                        headers={'Content-Type': 'application/json', **({'Idempotency-Key': key} if key else {})})
                    status, payload = response.status_code, response.content
                    if key and key == owner.drop_key:
                        owner.drop_key = None
                        self.close_connection = True
                        return
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.body = read_json(ROOT / 'agent-skills/short-drama-factory/assets/project-storyboard.json')
        for index, shot in enumerate(self.body['storyboard']['shots']):
            shot['uid'] = f'shot-{index + 1}'
        self.input = self.write('input.json', self.body)

    def mock(self, target, *args, **kwargs):
        item = patch(target, *args, **kwargs)
        value = item.start()
        self.addCleanup(item.stop)
        return value

    def mock_object(self, target, name, *args, **kwargs):
        item = patch.object(target, name, *args, **kwargs)
        value = item.start()
        self.addCleanup(item.stop)
        return value

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def write(self, name, body):
        path = self.root / name
        write_json(path, body)
        return str(path)

    def cli(self, *arguments):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = sdf.main(['--base-url', self.url, '--context', str(self.context), *arguments])
        values = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(self.ledger_errors, [])
        return code, values

    def create(self, key='create'):
        code, values = self.cli('project', 'create', '--json', self.input, '--request-key', key)
        self.assertEqual(code, 0, values)
        return values[-1]

    def test_create_update_and_explicit_request_conflict_are_durable(self):
        project = self.create()
        self.assertIsNone(project['job_id'])
        self.assertEqual(self.db.jobs(), [])
        self.assertEqual(self.create(), project)
        self.assertEqual(sum(path == '/api/v2/projects' for _, path, _ in self.calls), 1)
        change = self.write('change.json', {'settings': {'music': 'quiet piano'}})
        code, output = self.cli('project', 'update', project['id'], '--json', change, '--request-key', 'change')
        self.assertEqual(code, 0, output)
        updated = output[-1]
        self.assertNotEqual(updated['revision'], project['revision'])
        self.assertEqual(self.cli('project', 'update', project['id'], '--json', change, '--request-key', 'change')[-1][-1], updated)
        write_json(Path(change), {'settings': {'music': 'different'}})
        code, output = self.cli('project', 'update', project['id'], '--json', change, '--request-key', 'change')
        self.assertEqual((code, output[-1]['code']), (1, 'local_idempotency_conflict'))

    def test_lost_create_response_is_recovered_by_same_key_without_duplicate_project(self):
        self.drop_key = 'lost-create'
        code, output = self.cli('project', 'create', '--json', self.input, '--request-key', 'lost-create')
        self.assertEqual(code, 1)
        self.assertEqual(output[-1]['request_key'], 'lost-create')
        self.assertEqual(len(self.projects.list()), 1)
        self.assertEqual(read_json(self.context.parent / 'requests/lost-create.json')['status'], 'unknown')
        self.assertEqual(self.cli('project', 'create', '--json', self.input, '--request-key', 'lost-create')[0], 1)
        self.assertEqual(sum(path == '/api/v2/projects' for _, path, _ in self.calls), 1)
        code, recovered = self.cli('operation', 'retry', 'lost-create')
        self.assertEqual(code, 0, recovered)
        self.assertEqual(len(self.projects.list()), 1)
        self.assertEqual(self.cli('operation', 'get', 'lost-create')[1][-1]['server_operation']['status'], 'completed')

    def test_tampered_receipt_hash_and_arbitrary_write_routes_are_rejected(self):
        self.create()
        path = self.context.parent / 'requests/create.json'
        record = read_json(path)
        record['body']['input'] = 'tampered'
        write_json(path, record)
        before = len(self.calls)
        code, output = self.cli('operation', 'retry', 'create')
        self.assertEqual((code, output[-1]['code']), (1, 'invalid_operation_receipt'))
        self.assertEqual(len(self.calls), before)
        record.update(path='/api/provider/key', body={'id': 'deepseek', 'key': 'not-a-real-secret'}, status='unknown')
        record['request_hash'] = sdf.request_checksum(record['method'], record['path'], record['body'])
        write_json(path, record)
        code, output = self.cli('operation', 'retry', 'create')
        self.assertEqual((code, output[-1]['code']), (1, 'operation_route_not_allowed'))
        self.assertEqual(len(self.calls), before)
        self.assertEqual(self.config.key('deepseek'), '')

    def test_prompt_compile_is_read_only_and_does_not_create_mutation_ledger(self):
        project = self.create()
        sections = {'integrated_multimodal_description': '[Shot 1] 0.0-4.46s. A calm room.',
                    'overall_soundscape': 'Silence.', 'non_diegetic_music': 'N/A'}
        path = self.write('sections.json', sections)
        before = {item.name: item.read_bytes() for item in (self.context.parent / 'requests').iterdir()}
        code, output = self.cli('prompt', 'compile', '--project', project['id'], '--shot', 'shot-1', '--json', path)
        self.assertEqual(code, 0, output)
        self.assertEqual(output[-1]['uid'], 'shot-1')
        self.assertEqual(output[-1]['aligned_seconds'], 107 / 24)
        self.assertTrue(output[-1]['prompt'].startswith('integrated_multimodal_description:'))
        self.assertEqual(self.projects.revision(project['id']), project['revision'])
        self.assertEqual(before, {item.name: item.read_bytes() for item in (self.context.parent / 'requests').iterdir()})

    def test_produce_strict_plan_and_bounded_wait_never_cancel(self):
        code, output = self.cli('produce', '--json', self.input, '--request-key', 'produce', '--wait', '0.01')
        self.assertEqual(code, 3, output)
        self.assertTrue(any(value.get('event') == 'execution_plan' and value['strict'] for value in output))
        self.assertEqual(len(self.db.jobs()), 1)
        self.assertEqual(self.db.jobs()[0]['status'], 'queued')
        self.assertFalse(any(path.endswith('/stop') for _, path, _ in self.calls))
        self.assertIsNone(self.worker.thread)

    def test_blocked_produce_saves_project_and_plan_without_queueing(self):
        self.body['storyboard']['shots'][0]['prompt'] = ''
        write_json(Path(self.input), self.body)
        code, output = self.cli('produce', '--json', self.input)
        self.assertEqual((code, output[-1]['status']), (2, 'blocked'))
        self.assertTrue(output[-1]['plan_id'])
        self.assertEqual(len(self.projects.list()), 1)
        self.assertEqual(self.db.jobs(), [])

    def test_shot_regeneration_preserves_seed_and_original_uid(self):
        project = self.create()
        before = self.projects.get(project['id'])['story']['shots'][0]
        code, output = self.cli('shot', 'regenerate', project['id'], 'shot-1', '--request-key', 'regen')
        self.assertEqual(code, 0, output)
        self.assertTrue(output[-1]['preserved_seed'])
        after = self.projects.get(project['id'])['story']['shots'][0]
        self.assertEqual(after.get('seed'), before.get('seed'))
        self.assertEqual(after['uid'], before['uid'])
        job = self.db.jobs()[0]
        self.assertEqual(json.loads(job['payload'])['regenerate_uids'], ['shot-1'])
        self.assertEqual(self.cli('job', 'stop', job['id'])[0], 0)

    def test_config_patch_preserves_future_fields_and_is_recoverable(self):
        stored = self.config.get()
        stored['future_setting'] = {'preserve': True}
        write_json(self.config.path, stored)
        change = self.write('config-change.json', {'setup_complete': True})
        code, output = self.cli('config', 'get')
        self.assertEqual(code, 0, output)
        self.assertIn('revision', output[-1])
        code, output = self.cli('config', 'patch', '--json', change, '--request-key', 'config-change')
        self.assertEqual(code, 0, output)
        self.assertEqual(self.config.get()['future_setting'], {'preserve': True})
        self.assertTrue(self.config.get()['setup_complete'])
        self.assertEqual(self.cli('config', 'patch', '--json', change, '--request-key', 'config-change')[0], 0)

    def test_image_asset_and_speech_commands_use_typed_routes_without_generation(self):
        project = self.create()
        picture = self.root / 'reference.png'
        Image.new('RGB', (16, 16), 'red').save(picture)
        code, output = self.cli('asset', 'upload', '--project', project['id'], '--file', str(picture),
                                '--kind', 'image', '--request-key', 'asset')
        self.assertEqual(code, 0, output)
        aid = output[-1]['id']
        self.assertIn(aid, self.projects.get(project['id'])['assets'])
        code, output = self.cli('image', 'input', '--file', str(picture), '--request-key', 'input-image')
        self.assertEqual(code, 0, output)
        self.assertTrue(output[-1]['id'])
        request = self.write('image.json', {'prompt': 'A red ceramic cup on white background'})
        code, output = self.cli('image', 'create', '--json', request, '--request-key', 'image')
        self.assertEqual(code, 0, output)
        iid, jid = output[-1]['image_id'], output[-1]['job_id']
        self.assertEqual(self.cli('image', 'get', iid)[0], 0)
        self.assertEqual(self.cli('image', 'list')[0], 0)
        self.assertFalse(self.worker.images.get(iid)['request']['optimize'])
        self.db.update(jid, 'error', failure={'code': 'PLAN_STALE', 'message': '计划已过期',
            'retryable': False, 'details': [{'field': 'plan_id', 'message': '请重新计划'}],
            'next_actions': ['create_execution_plan']})
        code, output = self.cli('job', 'watch', jid)
        self.assertEqual((code, output[-1]['failure']['code']), (2, 'PLAN_STALE'))
        self.assertEqual(self.cli('job', 'resume', jid, '--request-key', 'resume-image')[1][-1]['job_id'], jid)
        planned = {'ready': False, 'confirmation_token': 'fixture-confirmation', 'download_bytes': 2327524}
        with patch('app.agent_environment.speech_plan', return_value=planned):
            self.assertEqual(self.cli('environment', 'speech-plan')[1][-1], planned)
            code, output = self.cli('environment', 'speech-prepare', '--confirmation', 'fixture-confirmation',
                                    '--request-key', 'speech')
        self.assertEqual(code, 0, output)
        self.assertEqual(self.db.job(output[-1]['job_id'])['kind'], 'speech-prepare')
        self.assertIsNone(self.worker.thread)

    def test_unsafe_start_and_invalid_wait_never_submit(self):
        self.body['start'] = True
        write_json(Path(self.input), self.body)
        code, output = self.cli('project', 'create', '--json', self.input)
        self.assertEqual((code, output[-1]['code']), (1, 'implicit_generation_rejected'))
        self.assertEqual(self.cli('produce', '--json', self.input, '--wait', '90')[0], 1)
        self.assertFalse(any(method in ('POST', 'PATCH') for method, _, _ in self.calls))

    def test_credentials_never_enter_argv_output_or_receipts(self):
        with patch.dict(os.environ, {'SDF_TEST_CREDENTIAL': 'never-save-this-secret'}):
            code, output = self.cli('credential', 'set', '--provider', 'deepseek', '--env', 'SDF_TEST_CREDENTIAL')
        self.assertEqual(code, 0, output)
        self.assertEqual(self.config.key('deepseek'), 'never-save-this-secret')
        self.assertNotIn('never-save-this-secret', json.dumps(output))
        self.assertFalse((self.context.parent / 'requests').exists())
        code, invalid = self.cli('credential', 'set', '--provider', 'deepseek', '--stdin', '--value', 'accidental-secret')
        self.assertEqual(code, 1)
        self.assertNotIn('accidental-secret', json.dumps(invalid))

    def test_start_calls_hidden_serve_only_launcher_and_connects(self):
        (self.root / 'launcher').mkdir(exist_ok=True)
        (self.root / 'launcher/start.py').write_text('# fixture', encoding='utf-8')
        with patch.object(sdf.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            code, output = self.cli('start', '--app', str(self.root), '--port', str(self.server.server_port))
        self.assertEqual(code, 0, output)
        self.assertIn('--serve-only', run.call_args.args[0])
        self.assertIn('--no-browser', run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs['creationflags'], getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def test_copied_cli_runs_task_outside_repository(self):
        portable = self.root / 'portable'
        portable.mkdir()
        for name in ('sdf.py', 'factory_api.py'):
            shutil.copyfile(SCRIPTS / name, portable / name)
        result = subprocess.run([sys.executable, str(portable / 'sdf.py'), '--base-url', self.url,
                                 '--context', str(self.context), 'project', 'create', '--json', self.input,
                                 '--request-key', 'portable'], cwd=portable, capture_output=True, text=True,
                                encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout.splitlines()[-1])['id'].startswith('agent_'))
        self.assertEqual(self.ledger_errors, [])


if __name__ == '__main__':
    unittest.main()
