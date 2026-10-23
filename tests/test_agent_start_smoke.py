"""Actual serve.py and a separately copied stdlib CLI, using isolated stores.

Only loopback HTTP is used. The fake engine records requests and rejects every
request; neither a real engine, a provider, nor user application data is used.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, ProxyHandler, Request

from app.config import ConfigStore
from app.database import Database
from app.version import VERSION


SOURCE = Path(__file__).resolve().parents[1]


class ServeOnlyStartupTests(unittest.TestCase):
    def test_fresh_service_and_portable_cli_leave_old_queue_untouched(self):
        (SOURCE / 'data').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='agent-start-', dir=SOURCE / 'data')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        application = root / 'isolated-application'
        application.mkdir()
        # Copy code/resources only. In particular, do not copy config, secrets,
        # projects, databases, engines, runtime environments, or model files.
        for directory in ('app', 'launcher', 'resources', 'presets', 'web', 'manifests', 'workflows'):
            shutil.copytree(SOURCE / directory, application / directory,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for source in SOURCE.glob('*.py'):
            shutil.copy2(source, application / source.name)
        shutil.copy2(SOURCE / 'config.default.json', application / 'config.default.json')

        requests = []

        class UnavailableEngine(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append((self.command, self.path))
                self.send_response(503)
                self.send_header('Content-Length', '0')
                self.end_headers()

            do_POST = do_GET
            do_PUT = do_GET
            do_PATCH = do_GET
            do_DELETE = do_GET

        engine = ThreadingHTTPServer(('127.0.0.1', 0), UnavailableEngine)
        engine_thread = threading.Thread(target=engine.serve_forever, daemon=True)
        engine_thread.start()

        def close_engine():
            engine.shutdown()
            engine.server_close()
            engine_thread.join(timeout=5)

        self.addCleanup(close_engine)
        config = ConfigStore(application)
        configuration = config.get()
        endpoint = f'http://127.0.0.1:{engine.server_port}'
        configuration['environment']['comfy_url'] = endpoint
        configuration['environment']['mode'] = 'existing'
        configuration['environment']['comfy_dir'] = ''
        configuration['environment']['python'] = ''
        configuration['proxy'] = ''
        for provider in configuration['providers']:
            provider['base_url'] = endpoint
        config.save(configuration)
        db = Database(application / 'data/factory.sqlite3')
        # An invalid project/kind makes an accidental old-queue recovery fail
        # locally, even if serve-only regresses; no render request can be made.
        old_job = db.enqueue('smoke-old-project', 'smoke-never-execute', {'sentinel': 'untouched'})
        interrupted_job = db.enqueue('__environment', 'smoke-never-execute', {})
        db.update(interrupted_job, status='running', message='previous process ended')
        with db.connect() as connection:
            old_row = dict(connection.execute('SELECT * FROM jobs WHERE id=?', (old_job,)).fetchone())
            old_events = [tuple(row) for row in connection.execute('SELECT * FROM events WHERE job_id=?', (old_job,))]

        with socket.socket() as port_socket:
            port_socket.bind(('127.0.0.1', 0))
            port = port_socket.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = {key: value for key, value in os.environ.items()
               if key.upper() not in {'PYTHONPATH', 'DRAMA_FACTORY_URL', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'}}
        env.update(FACTORY_SERVE_ONLY='1', PYTHONIOENCODING='utf-8', NO_PROXY='127.0.0.1,localhost')
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        log_path = root / 'server.log'
        log = log_path.open('wb')
        self.addCleanup(log.close)
        process = subprocess.Popen([sys.executable, str(application / 'launcher/serve.py'), '--port', str(port)],
                                   cwd=application, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, creationflags=creationflags)

        def stop_service():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

        self.addCleanup(stop_service)
        opener = build_opener(ProxyHandler({}))

        def get(path):
            with opener.open(base + path, timeout=5) as response:
                return json.load(response)

        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                self.fail('serve.py exited before readiness: ' + log_path.read_text(encoding='utf-8'))
            try:
                health = get('/api/health')
                break
            except (OSError, URLError):
                if time.monotonic() >= deadline:
                    self.fail('serve.py did not become ready: ' + log_path.read_text(encoding='utf-8'))
                time.sleep(0.05)
        self.assertEqual(health['version'], VERSION)
        self.assertEqual(Path(health['application_root']).resolve(), application.resolve())
        self.assertEqual(health['protocol_version'], 1)
        self.assertFalse(health['worker_running'])
        self.assertEqual(health['queue_mode'], 'stopped')
        self.assertFalse(health['comfy'])

        portable = root / 'independent-ai-client'
        portable.mkdir()
        for name in ('sdf.py', 'factory_api.py'):
            shutil.copy2(SOURCE / 'agent-skills/short-drama-factory/scripts' / name, portable / name)
        context = portable / '.sdf/connection.json'

        def cli(*arguments, expected=0):
            result = subprocess.run([sys.executable, str(portable / 'sdf.py'), '--context', str(context), *arguments],
                                    cwd=portable, env=env, stdin=subprocess.DEVNULL,
                                    capture_output=True, encoding='utf-8', timeout=20,
                                    creationflags=creationflags)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr + '\n' +
                             log_path.read_text(encoding='utf-8'))
            self.assertEqual(result.stderr, '')
            records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            self.assertTrue(records, result.stdout)
            self.assertTrue(all(isinstance(item, dict) for item in records))
            return records[-1]

        connected = cli('connect', '--app', str(application), '--url', base)
        self.assertTrue(connected['connected'])
        self.assertEqual(connected['app_version'], VERSION)
        self.assertEqual(json.loads(context.read_text(encoding='utf-8'))['base_url'], base)
        doctor = cli('doctor')
        self.assertTrue(doctor['read_only'])
        self.assertFalse(doctor['ready'])
        self.assertEqual([item['code'] for item in doctor['checks']], ['API_CONNECTED', 'ENGINE_UNAVAILABLE'])
        self.assertTrue(cli('capabilities')['features']['serve_only'])

        draft_file = portable / 'draft.json'
        shutil.copy2(SOURCE / 'agent-skills/short-drama-factory/assets/agent-storyboard.json', draft_file)
        first = cli('project', 'create', '--json', str(draft_file), '--request-key', 'smoke-create')
        second = cli('project', 'create', '--json', str(draft_file), '--request-key', 'smoke-create')
        self.assertEqual(second, first)
        self.assertIsNone(first['job_id'])
        # A completed CLI receipt is served locally. Also replay its exact body
        # over HTTP to prove server idempotency, and reject changed same-key data.
        receipt = json.loads((context.parent / 'requests/smoke-create.json').read_text(encoding='utf-8'))
        request_headers = {'Content-Type': 'application/json', 'Idempotency-Key': 'smoke-create'}
        replay = Request(base + '/api/v2/projects', data=json.dumps(receipt['body']).encode(),
                         headers=request_headers, method='POST')
        with opener.open(replay, timeout=5) as response:
            self.assertEqual(response.status, 201)
            self.assertEqual(json.load(response), first)
        changed = {**receipt['body'], 'input': 'different creation under the same key'}
        conflict = Request(base + '/api/v2/projects', data=json.dumps(changed).encode(),
                           headers=request_headers, method='POST')
        with self.assertRaises(HTTPError) as conflicted:
            opener.open(conflict, timeout=5)
        self.assertEqual(conflicted.exception.code, 409)
        self.assertEqual(json.load(conflicted.exception)['code'], 'IDEMPOTENCY_CONFLICT')
        project = cli('project', 'get', first['id'])
        self.assertEqual(project['revision'], first['revision'])
        self.assertFalse(project['settings']['auto_reference'])
        operation = cli('operation', 'get', 'smoke-create')
        self.assertEqual(operation['server_operation']['status'], 'completed')
        self.assertEqual(operation['server_operation']['result'], first)
        self.assertEqual(operation['local_status'], 'completed')
        exact = cli('job', 'get', old_job)
        self.assertEqual(exact['id'], old_job)
        self.assertEqual(exact['status'], 'queued')
        self.assertEqual(exact['attempts'], 0)
        self.assertFalse(exact['terminal'])
        self.assertNotIn('payload', exact)
        interrupted = cli('job', 'get', interrupted_job)
        self.assertEqual(interrupted['id'], interrupted_job)
        self.assertEqual(interrupted['status'], 'paused')
        self.assertEqual(interrupted['attempts'], 0)
        self.assertTrue(interrupted['terminal'])
        self.assertEqual(interrupted['failure']['code'], 'WORKER_INTERRUPTED')

        with self.assertRaises(HTTPError) as unknown:
            get('/api/jobs/not-an-existing-job')
        self.assertEqual(unknown.exception.code, 404)
        self.assertEqual(json.load(unknown.exception)['code'], 'JOB_NOT_FOUND')
        invalid = Request(base + '/api/v2/projects', data=b'{"start":true}', method='POST',
                          headers={'Content-Type': 'application/json', 'Idempotency-Key': 'smoke-invalid'})
        with self.assertRaises(HTTPError) as rejected:
            opener.open(invalid, timeout=5)
        self.assertEqual(rejected.exception.code, 422)
        self.assertEqual(json.load(rejected.exception)['code'], 'VALIDATION_ERROR')
        schema = get('/openapi.json')
        self.assertIn('/api/v2/projects', schema['paths'])
        self.assertIn('/api/jobs/{jid}', schema['paths'])
        self.assertEqual(schema['info']['version'], VERSION)

        # Re-read the actual database and live process after all HTTP/CLI calls;
        # successful connection/draft creation must not authorize old work.
        self.assertIsNone(process.poll())
        final_health = get('/api/health')
        self.assertFalse(final_health['worker_running'])
        self.assertEqual(final_health['queue_mode'], 'stopped')
        with db.connect() as connection:
            self.assertEqual(dict(connection.execute('SELECT * FROM jobs WHERE id=?', (old_job,)).fetchone()), old_row)
            self.assertEqual([tuple(row) for row in connection.execute('SELECT * FROM events WHERE job_id=?', (old_job,))], old_events)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 2)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM projects').fetchone()[0], 1)
        self.assertGreater(len(requests), 0)
        self.assertEqual(set(requests), {('GET', '/system_stats')})
        self.assertFalse(any(application.rglob('*.mp4')))
        self.assertFalse(any(application.rglob('*.safetensors')))


if __name__ == '__main__':
    unittest.main()
