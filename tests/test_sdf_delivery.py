"""Portable final-delivery downloads and resumable batch submission; no GPU."""
import contextlib
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import quote, unquote, urlsplit


SCRIPTS = Path(__file__).resolve().parents[1] / 'agent-skills/short-drama-factory/scripts'
import sys
spec = importlib.util.spec_from_file_location('factory_api', SCRIPTS / 'factory_api.py')
factory = importlib.util.module_from_spec(spec)
sys.modules['factory_api'] = factory
spec.loader.exec_module(factory)
spec = importlib.util.spec_from_file_location('sdf_delivery_cli', SCRIPTS / 'sdf.py')
sdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdf)


class DeliveryCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = self.root / '.sdf/connection.json'
        self.calls, self.jobs, self.counts = [], {}, {}
        self.drop_project = None
        self.denied_project = None
        self.data = {'成片.mp4': b'current video fixture', '字幕.srt': b'',
                     'edits/current/review/overview.png': b'review fixture',
                     'edits/old/成片.mp4': b'old video fixture', 'clips/shot-1.mp4': b'raw clip fixture'}
        self.manifest = {'project_id': 'project-1', 'version_id': 'current', 'ready_for_delivery': True,
                         'media_verified': True, 'content_review_complete': False, 'artifacts': []}
        for name, kind, version in [('成片.mp4', 'original', 'current'), ('字幕.srt', 'subtitles', 'current'),
                                    ('edits/current/review/overview.png', 'review_page', 'current'),
                                    ('edits/old/成片.mp4', 'edit_成片.mp4', 'old'), ('clips/shot-1.mp4', 'shot_clip', None)]:
            self.manifest['artifacts'].append({'relative_path': name, 'kind': kind, 'version_id': version,
                'local_path': 'server/' + name, 'size': len(self.data[name]), 'mime': 'application/octet-stream',
                'sha256': hashlib.sha256(self.data[name]).hexdigest(),
                'api_url': '/api/v2/projects/project-1/delivery/files/' + quote(name, safe='/')})
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.forward()

            def do_POST(self):
                self.forward()

            def forward(self):
                owner.calls.append((self.command, self.path))
                path = urlsplit(self.path).path
                status, mime = 200, 'application/json'
                if path == '/api/health':
                    value = {'application_root': str(owner.root), 'protocol_version': 1, 'app_version': '4.0.0'}
                elif path == '/api/v2/projects/project-1/delivery':
                    value = owner.manifest
                elif path.startswith('/api/v2/projects/project-1/delivery/files/'):
                    name = unquote(path.split('/delivery/files/', 1)[1])
                    if name not in owner.data:
                        status, value = 404, {'code': 'ARTIFACT_NOT_FOUND', 'message': 'missing'}
                    else:
                        mime, value = 'application/octet-stream', owner.data[name]
                elif path.startswith('/api/v2/projects/') and path.endswith('/run') and self.command == 'POST':
                    pid = path.split('/')[4]
                    key = self.headers.get('Idempotency-Key')
                    self.rfile.read(int(self.headers.get('Content-Length', 0)))
                    owner.counts[pid] = owner.counts.get(pid, 0) + 1
                    if pid == owner.denied_project:
                        status, value = 409, {'code': 'PLAN_STALE', 'message': 'plan changed', 'retryable': False}
                    else:
                        value = owner.jobs.setdefault(key, {'id': pid, 'job_id': 'job-' + pid, 'request_key': key})
                        if pid == owner.drop_project:
                            owner.drop_project = None
                            self.close_connection = True
                            return
                else:
                    status, value = 404, {'code': 'NOT_FOUND', 'message': 'unknown fixture route'}
                payload = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def cli(self, *arguments):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = sdf.main(['--base-url', self.url, '--context', str(self.context), *arguments])
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_delivery_downloads_current_evidence_and_empty_subtitle_without_history(self):
        target = self.root / 'delivery'
        code, output = self.cli('deliver', 'project-1', '--verify', '--output', str(target))
        self.assertEqual(code, 0, output)
        self.assertEqual((target / '成片.mp4').read_bytes(), self.data['成片.mp4'])
        self.assertEqual((target / '字幕.srt').read_bytes(), b'')
        self.assertTrue((target / 'edits/current/review/overview.png').is_file())
        self.assertFalse((target / 'edits/old/成片.mp4').exists())
        self.assertFalse((target / 'clips/shot-1.mp4').exists())
        saved = json.loads((target / 'delivery.json').read_text(encoding='utf-8'))
        self.assertEqual(len(saved['downloads']), 3)
        self.assertFalse(saved['content_review_complete'])

    def test_include_shots_is_explicit_and_verify_failure_still_saves_evidence(self):
        self.manifest['ready_for_delivery'] = False
        self.manifest['media_verified'] = False
        target = self.root / 'review'
        code, output = self.cli('deliver', 'project-1', '--verify', '--include-shots', '--output', str(target))
        self.assertEqual(code, 2, output)
        self.assertTrue((target / 'clips/shot-1.mp4').is_file())
        self.assertTrue((target / 'delivery.json').is_file())
        self.assertFalse(output[-1]['ready_for_delivery'])

    def test_changed_download_hash_is_rejected_and_failure_report_saved(self):
        self.data['成片.mp4'] = b'X' * len(self.data['成片.mp4'])
        target = self.root / 'changed'
        code, output = self.cli('deliver', 'project-1', '--output', str(target))
        self.assertEqual(code, 1, output)
        self.assertFalse((target / '成片.mp4').exists())
        saved = json.loads((target / 'delivery.json').read_text(encoding='utf-8'))
        self.assertFalse(saved['download_complete'])
        self.assertTrue(saved['download_failures'])
        self.assertEqual(saved['download_failures'][0]['code'], 'delivery_hash_mismatch')

    def test_paths_and_server_urls_cannot_escape_delivery_scope(self):
        for field, bad in [('relative_path', '../escape.mp4'), ('relative_path', 'C:/escape.mp4'),
                           ('relative_path', 'delivery.json'), ('api_url', '/api/exports/private')]:
            with self.subTest(field=field, bad=bad):
                original = copy.deepcopy(self.manifest)
                self.manifest['artifacts'][0][field] = bad
                target = self.root / ('unsafe-' + str(len(self.calls)))
                code, output = self.cli('deliver', 'project-1', '--output', str(target))
                self.assertEqual(code, 1, output)
                self.assertFalse(target.exists())
                self.manifest = original

    def test_existing_output_directory_is_preserved(self):
        target = self.root / 'existing'
        target.mkdir()
        (target / 'personal.txt').write_text('keep')
        code, output = self.cli('deliver', 'project-1', '--output', str(target))
        self.assertEqual(code, 1, output)
        self.assertEqual((target / 'personal.txt').read_text(), 'keep')

    def test_batch_retries_only_unknown_submissions_and_reuses_confirmed_keys(self):
        path = self.root / 'batch.json'
        items = [{'project_id': pid, 'plan_id': 'a' * 64} for pid in ('one', 'two', 'denied')]
        path.write_text(json.dumps(items), encoding='utf-8')
        self.drop_project, self.denied_project = 'two', 'denied'
        code, output = self.cli('batch', '--json', str(path), '--request-key', 'batch-1')
        self.assertEqual(code, 2, output)
        self.assertEqual(len(self.jobs), 2)
        self.assertEqual(self.counts, {'one': 1, 'two': 1, 'denied': 1})
        code, output = self.cli('batch', '--json', str(path), '--request-key', 'batch-1', '--retry-unknown')
        self.assertEqual(code, 2, output)
        self.assertEqual(len(self.jobs), 2)
        self.assertEqual(self.counts, {'one': 1, 'two': 2, 'denied': 1})
        self.assertEqual(output[-1]['confirmed'], 2)
        self.assertEqual(output[-1]['failed'], 1)
        items[0]['plan_id'] = 'b' * 64
        path.write_text(json.dumps(items), encoding='utf-8')
        before = copy.deepcopy(self.counts)
        self.assertEqual(self.cli('batch', '--json', str(path), '--request-key', 'batch-1')[0], 1)
        self.assertEqual(before, self.counts)


if __name__ == '__main__':
    unittest.main()
