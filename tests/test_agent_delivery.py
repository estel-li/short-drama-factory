"""Production delivery routes and copied CLI over HTTP, with CPU fixture media."""
import hashlib
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

import uvicorn

import pipeline
from app import api
from app.finishing import build
from app.storage import ROOT, digest, read_json, write_json
import tests.test_agent_api as api_fixture


class AgentDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.shared.cleanup)
        cls.video = Path(cls.shared.name) / 'fixture.mp4'
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=24',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                         '-c:v', 'libx264', '-bf', '0', '-c:a', 'aac', '-frames:v', '12', '-t', '0.5', cls.video])

    def setUp(self):
        api_fixture.AgentAPITests.setUp(self)
        body = read_json(ROOT / 'agent-skills/short-drama-factory/assets/agent-storyboard.json')
        response = self.client.post('/api/v2/projects', json=body, headers={'Idempotency-Key': 'delivery-draft'})
        self.assertEqual(response.status_code, 201, response.text)
        self.pid = response.json()['id']
        self.project = self.projects.path(self.pid)
        self.story = read_json(self.project / '分镜.json')
        source = self.project / 'source.mp4'
        shutil.copy2(self.video, source)
        # Build real post-production records and review images, not invented evidence.
        build(self.project, self.story, [source] * len(self.story['shots']), 96, 64,
              {'edit_preset': 'original', 'subtitle_alignment': 'approximate', 'subtitles': False})
        write_json(self.project / 'state.json', {'status': 'complete', 'shots_by_uid': {}})
        for target in ('requests.sessions.Session.request', 'app.speech.ensure_model', 'pipeline.Runner.run'):
            item = patch(target, side_effect=AssertionError('Delivery must remain read-only and CPU-only'))
            item.start()
            self.addCleanup(item.stop)

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.project.rglob('*') if p.is_file()}

    def test_http_manifest_preserves_fingerprint_and_downloads_only_artifacts(self):
        before = self.snapshot()
        response = self.client.get(f'/api/v2/projects/{self.pid}/delivery?verify=true')
        self.assertEqual(response.status_code, 200, response.text)
        manifest = response.json()
        fingerprint = manifest.pop('fingerprint')
        self.assertEqual(fingerprint, digest(manifest))
        self.assertTrue(manifest['ready_for_delivery'], manifest['checks'])
        self.assertFalse(manifest['content_review_complete'])
        for artifact in manifest['artifacts']:
            downloaded = self.client.get(artifact['api_url'])
            self.assertEqual(downloaded.status_code, 200, artifact['relative_path'])
            self.assertEqual(len(downloaded.content), artifact['size'])
            self.assertEqual(hashlib.sha256(downloaded.content).hexdigest(), artifact['sha256'])
        for name in ('settings.json', 'state.json', '分镜.json', 'current_edit.json', 'source.mp4', '.secrets.json'):
            denied = self.client.get(f'/api/v2/projects/{self.pid}/delivery/files/{name}')
            self.assertEqual(denied.status_code, 404, name)
            self.assertEqual(denied.json()['code'], 'ARTIFACT_NOT_FOUND')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.db.jobs(), [])

    def test_inventory_only_does_not_claim_verified_or_complete_media(self):
        manifest = self.client.get(f'/api/v2/projects/{self.pid}/delivery').json()
        self.assertFalse(manifest['media_verified'])
        self.assertFalse(manifest['ready_for_delivery'])
        self.assertEqual(manifest['checks']['media']['status'], 'not_checked')
        self.assertTrue(self.client.get('/api/capabilities').json()['features']['delivery_manifest'])

    def test_copied_cli_downloads_real_api_artifacts_and_detects_stale_story(self):
        scripts = self.root / 'standalone-skill/scripts'
        shutil.copytree(ROOT / 'agent-skills/short-drama-factory/scripts', scripts)
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen()
        address = f'http://127.0.0.1:{sock.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(api.app, log_level='error', lifespan='off'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()

        def close():
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
            self.assertFalse(thread.is_alive(), 'Owned HTTP server did not exit')
        self.addCleanup(close)
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(server.started)
        before = self.snapshot()
        target = self.root / 'delivered'
        command = [sys.executable, str(scripts / 'sdf.py'), '--base-url', address,
                   '--context', str(self.root / '.sdf/connection.json'), 'deliver', self.pid, '--verify']
        result = subprocess.run([*command, '--output', str(target)], cwd=self.root, capture_output=True,
                                encoding='utf-8', timeout=45,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads((target / 'delivery.json').read_text(encoding='utf-8'))
        self.assertTrue(receipt['download_complete'])
        self.assertTrue(receipt['ready_for_delivery'])
        self.assertFalse(receipt['content_review_complete'])
        self.assertTrue(any(item['kind'] == 'review_page' for item in receipt['downloads']))
        self.assertEqual((target / '成片.mp4').read_bytes(), (self.project / '成片.mp4').read_bytes())
        self.assertEqual(self.snapshot(), before)
        self.story['shots'][0]['summary'] += ' changed scene'
        write_json(self.project / '分镜.json', self.story)
        stale = subprocess.run(command, cwd=self.root, capture_output=True, encoding='utf-8', timeout=45,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(stale.returncode, 2, stale.stdout + stale.stderr)
        self.assertEqual(json.loads(stale.stdout)['checks']['recorded_provenance']['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
