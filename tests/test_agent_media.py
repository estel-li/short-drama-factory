"""Durable media HTTP operations without worker threads, GPU, providers or downloads."""
import base64
from concurrent.futures import ThreadPoolExecutor
import io
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from PIL import Image

from app import api
from app.agent_media import install_media_routes
from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.contracts import ContractError
from app.database import Database
from app.execution_policy import current_policy
from app.jobs import Worker
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class AgentMediaTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/jobs.sqlite3')
        self.mock('app.projects.ROOT', self.root)
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.content = Content(self.config, Skills(), self.projects)
        self.worker = Worker(self.db, self.config, self.projects, self.content, self.assets)
        self.start = self.mock_object(self.worker, 'start')
        self.allow = self.mock_object(self.worker, 'allow_job')
        self.mock_object(self.worker.images, 'request', side_effect=AssertionError('No ComfyUI network'))
        self.mock_object(self.worker.images.environment, 'plan', side_effect=AssertionError('No environment work at submission'))
        self.mock_object(self.content, 'call', side_effect=AssertionError('No provider calls'))
        self.mock('requests.sessions.Session.request', side_effect=AssertionError('No network'))
        app = FastAPI()
        app.add_exception_handler(RequestValidationError, api.request_validation_error)
        app.add_exception_handler(ContractError, api.contract_error)
        app.add_exception_handler(ValueError, api.value_error)
        app.add_exception_handler(RuntimeError, api.value_error)
        self.services = SimpleNamespace(config=self.config, db=self.db, projects=self.projects,
                                        assets=self.assets, content=self.content, worker=self.worker)
        install_media_routes(app, lambda: self.services)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.image_body = {'request': {'prompt': 'A blue cup on a windowsill.'}}

    def mock(self, target, *args, **kwargs):
        item = patch(target, *args, **kwargs)
        result = item.start()
        self.addCleanup(item.stop)
        return result

    def mock_object(self, target, name, *args, **kwargs):
        item = patch.object(target, name, *args, **kwargs)
        result = item.start()
        self.addCleanup(item.stop)
        return result

    @staticmethod
    def png(color='blue'):
        stream = io.BytesIO()
        Image.new('RGB', (32, 32), color).save(stream, format='PNG')
        return base64.b64encode(stream.getvalue()).decode()

    @staticmethod
    def audio():
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(16000)
            sound.writeframes(b'\0\0' * 16000)
        return base64.b64encode(stream.getvalue()).decode()

    def post(self, route='/api/v2/images', body=None, key='request'):
        return self.client.post(route, json=self.image_body if body is None else body,
                                headers={'Idempotency-Key': key})

    def project(self):
        body = read_json(ROOT / 'agent-skills/short-drama-factory/assets/project-storyboard.json')
        return self.projects.create(body['input'], body['options'], body['storyboard']).name

    def test_image_defaults_to_external_prompt_and_forbids_implicit_downloads(self):
        response = self.post()
        self.assertEqual(response.status_code, 202, response.text)
        result = response.json()
        image = self.worker.images.get(result['id'])
        self.assertFalse(image['request']['optimize'])
        self.assertEqual(self.worker.images.optimize(result['id'], lambda message: None, lambda: False),
                         self.image_body['request']['prompt'])
        self.assertEqual(image['job_id'], result['job_id'])
        self.assertEqual(image['operation_id'], result['operation_id'])
        job = self.db.job(result['job_id'])
        payload = json.loads(job['payload'])
        self.assertEqual(payload['internal_text'], 'forbid')
        self.assertFalse(payload['allow_downloads'])
        self.assertNotIn('agent_plan', payload)

        def execute(unused):
            self.assertEqual(current_policy().internal_text, 'forbid')
            self.assertFalse(current_policy().allow_downloads)
            return 'done'

        with patch.object(self.worker, '_execute', side_effect=execute):
            self.assertEqual(self.worker.execute(job), 'done')
        self.start.assert_called_once_with(recover=False)
        self.allow.assert_called_once_with(result['job_id'])
        self.assertIsNone(self.worker.thread)

    def test_image_replay_conflict_and_terminal_no_restart(self):
        first = self.post()
        self.assertEqual(first.status_code, 202, first.text)
        self.assertEqual(self.post().json(), first.json())
        changed = self.post(body={'request': {'prompt': 'Different image'}})
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(changed.json()['code'], 'IDEMPOTENCY_CONFLICT')
        self.assertEqual(len(self.db.jobs()), 1)
        self.assertEqual(len(self.worker.images.listing()), 1)
        self.db.update(first.json()['job_id'], 'done')
        self.start.reset_mock()
        self.allow.reset_mock()
        self.assertEqual(self.post().json(), first.json())
        self.start.assert_not_called()
        self.allow.assert_not_called()

    def test_concurrent_same_request_creates_one_image_and_job(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(executor.map(lambda _: self.post(), range(4)))
        self.assertTrue(all(response.status_code == 202 for response in responses))
        self.assertTrue(all(response.json() == responses[0].json() for response in responses))
        self.assertEqual(len(self.db.jobs()), 1)
        self.assertEqual(len(self.worker.images.listing()), 1)

    def test_published_image_before_enqueue_crash_keeps_id_and_seed(self):
        with patch.object(self.db, 'enqueue_operation', side_effect=RuntimeError('crash after image publication')):
            failed = self.post()
        self.assertGreaterEqual(failed.status_code, 400)
        prior = self.worker.images.listing()[0]
        self.assertEqual(self.db.operation('request')['status'], 'pending')
        with patch.object(self.worker.images, 'image_request', side_effect=AssertionError('Must recover original seed/config')):
            recovered = self.post()
        self.assertEqual(recovered.status_code, 202, recovered.text)
        self.assertEqual(recovered.json()['id'], prior['id'])
        self.assertEqual(self.worker.images.get(prior['id'])['request']['seed'], prior['request']['seed'])
        self.assertEqual(len(self.worker.images.listing()), 1)
        self.assertEqual(len(self.db.jobs()), 1)

    def test_durable_job_before_image_metadata_crash_is_repaired(self):
        with patch.object(self.worker.images, 'update', side_effect=RuntimeError('image metadata unavailable')):
            failed = self.post()
        self.assertGreaterEqual(failed.status_code, 400)
        receipt = self.db.operation('request')
        self.assertEqual(receipt['status'], 'completed')
        iid, jid = receipt['result']['id'], receipt['result']['job_id']
        self.assertNotIn('job_id', self.worker.images.get(iid))
        self.start.assert_not_called()
        recovered = self.post()
        self.assertEqual(recovered.status_code, 202, recovered.text)
        self.assertEqual(self.worker.images.get(iid)['job_id'], jid)
        self.assertEqual(len(self.db.jobs()), 1)
        self.allow.assert_called_once_with(jid)

    def test_dispatch_failure_replay_authorizes_original_job(self):
        self.start.side_effect = RuntimeError('startup unavailable')
        failed = self.post()
        self.assertGreaterEqual(failed.status_code, 400)
        jid = self.db.operation('request')['result']['job_id']
        self.start.side_effect = None
        self.start.reset_mock()
        self.allow.reset_mock()
        recovered = self.post()
        self.assertEqual(recovered.status_code, 202, recovered.text)
        self.assertEqual(recovered.json()['job_id'], jid)
        self.start.assert_called_once_with(recover=False)
        self.allow.assert_called_once_with(jid)

    def test_text_optimization_requires_explicit_policy_or_finished_prompt(self):
        for index, body in enumerate(({'request': {'prompt': 'idea', 'optimize': True}},
                                       {'request': {'prompt': 'idea'}, 'optimize_only': True})):
            rejected = self.post(body=body, key='rejected-' + str(index))
            self.assertEqual(rejected.status_code, 409, rejected.text)
            self.assertEqual(rejected.json()['code'], 'TEXT_GENERATION_FORBIDDEN')
        self.assertEqual(self.db.jobs(), [])
        ready = self.post(body={'request': {'prompt': 'idea', 'optimize': True, 'optimized_prompt': 'finished external prompt'}}, key='external')
        self.assertEqual(ready.status_code, 202, ready.text)
        allowed = self.post(body={'request': {'prompt': 'idea'}, 'optimize_only': True, 'internal_text': 'allowed'}, key='allowed')
        self.assertEqual(allowed.status_code, 202, allowed.text)
        self.assertEqual(self.db.job(allowed.json()['job_id'])['kind'], 'image-optimize')
        self.assertTrue(self.worker.images.get(allowed.json()['id'])['request']['optimize'])

    def test_model_specific_and_partial_sampling_defaults_are_preserved(self):
        for index, sampling in enumerate((None, {'steps': 30})):
            request = {'prompt': 'bookstore', 'image_model': 'sdxl-base'}
            if sampling is not None:
                request['sampling'] = sampling
            response = self.post(body={'request': request}, key='sdxl-' + str(index))
            self.assertEqual(response.status_code, 202, response.text)
            actual = self.worker.images.get(response.json()['id'])['request']['sampling']
            self.assertEqual(actual['steps'], 28 if sampling is None else 30)
            self.assertEqual(actual['cfg'], 7)

    def test_omitted_image_model_uses_configured_model_and_sampling(self):
        config = self.config.get()
        config['image_generation'] = {'image_model': 'sdxl-base', 'sampling': {'steps': 31, 'cfg': 8}}
        self.config.save(config)
        response = self.post()
        self.assertEqual(response.status_code, 202, response.text)
        request = self.worker.images.get(response.json()['id'])['request']
        self.assertEqual(request['image_model'], 'sdxl-base')
        self.assertEqual(request['sampling']['steps'], 31)
        self.assertEqual(request['sampling']['cfg'], 8)
        self.assertFalse(request['optimize'])

    def test_explicit_sampling_differs_from_model_defaults_for_request_identity(self):
        body = {'request': {'prompt': 'bookstore', 'image_model': 'sdxl-base'}}
        first = self.post(body=body)
        self.assertEqual(first.status_code, 202, first.text)
        explicit = self.post(body={'request': {**body['request'], 'sampling': {'cfg': 1}}})
        self.assertEqual(explicit.status_code, 409, explicit.text)
        self.assertEqual(explicit.json()['code'], 'IDEMPOTENCY_CONFLICT')
        self.assertEqual(len(self.db.jobs()), 1)

    def test_media_routes_are_registered_on_the_real_application(self):
        client = TestClient(api.app, base_url='http://127.0.0.1')
        try:
            schema = client.get('/openapi.json').json()
        finally:
            client.close()
        for path in ('/api/v2/images', '/api/v2/image-inputs', '/api/v2/projects/{pid}/assets'):
            self.assertIn(path, schema['paths'])
            self.assertIn('post', schema['paths'][path])
        self.assertFalse(schema['components']['schemas']['AgentImageRequest']['properties']['optimize']['default'])

    def test_reference_input_crash_and_replay_reuse_content_hash(self):
        body = {'name': 'Reference', 'data': self.png()}
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('receipt unavailable')):
            failed = self.post('/api/v2/image-inputs', body)
        self.assertGreaterEqual(failed.status_code, 400)
        files = list(self.worker.images.inputs.root.glob('*.png'))
        self.assertEqual(len(files), 1)
        recovered = self.post('/api/v2/image-inputs', body)
        self.assertEqual(recovered.status_code, 201, recovered.text)
        self.assertEqual(recovered.json()['id'], files[0].stem)
        self.assertEqual(self.post('/api/v2/image-inputs', body).json(), recovered.json())
        self.assertEqual(len(list(self.worker.images.inputs.root.glob('*.png'))), 1)
        conflict = self.post('/api/v2/image-inputs', {**body, 'data': self.png('red')})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.db.jobs(), [])

    def test_image_asset_crash_recovery_does_not_duplicate_or_bind_shots(self):
        pid = self.project()
        folder = self.projects.path(pid)
        story_before = read_json(folder / '分镜.json')
        revision_before = self.projects.revision(pid)
        body = {'type': 'image', 'name': 'cup reference', 'data': self.png()}
        route = f'/api/v2/projects/{pid}/assets'
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('receipt unavailable')):
            failed = self.post(route, body)
        self.assertGreaterEqual(failed.status_code, 400)
        assets = read_json(folder / 'assets.json')
        self.assertEqual(len(assets), 1)
        aid, original = next(iter(assets.items()))
        # Reconciliation of an already-written asset is valid even after another
        # job makes the project busy; it does not modify the imported asset again.
        self.db.enqueue(pid, 'render')
        recovered = self.post(route, body)
        self.assertEqual(recovered.status_code, 201, recovered.text)
        self.assertEqual(recovered.json()['id'], aid)
        self.assertEqual(read_json(folder / 'assets.json'), {aid: original})
        self.assertEqual(read_json(folder / '分镜.json'), story_before)
        self.assertNotEqual(recovered.json()['revision'], revision_before)
        self.assertEqual(len(list((folder / 'assets').glob('*'))), 1)
        self.assertEqual(self.post(route, body).json(), recovered.json())

    def test_audio_asset_crash_recovery_preserves_metadata_and_source(self):
        pid = self.project()
        route = f'/api/v2/projects/{pid}/assets'
        body = {'type': 'audio', 'name': 'source.wav', 'data': self.audio()}
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('receipt unavailable')):
            failed = self.post(route, body)
        self.assertGreaterEqual(failed.status_code, 400)
        first = next(iter(read_json(self.projects.path(pid) / 'assets.json').values()))
        recovered = self.post(route, body)
        self.assertEqual(recovered.status_code, 201, recovered.text)
        self.assertEqual(recovered.json()['id'], first['id'])
        self.assertEqual(recovered.json()['sha256'], first['sha256'])
        self.assertEqual(recovered.json()['upload_sha256'], first['upload_sha256'])
        self.assertAlmostEqual(recovered.json()['duration'], 1, places=2)
        self.assertEqual(len(list((self.projects.path(pid) / 'assets').glob('*'))), 1)

    def test_video_asset_recovery_reuses_normalized_file_without_reencoding(self):
        import pipeline
        original = self.root / 'input.mp4'
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=24',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                         '-c:v', 'libx264', '-c:a', 'aac', '-frames:v', '48', '-t', '2', original])
        raw = original.read_bytes()
        pid = self.project()
        route = f'/api/v2/projects/{pid}/assets'
        body = {'type': 'video', 'name': 'original.mp4', 'data': base64.b64encode(raw).decode()}
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('receipt unavailable')):
            failed = self.post(route, body)
        self.assertGreaterEqual(failed.status_code, 400)
        value = next(iter(read_json(self.projects.path(pid) / 'assets.json').values()))
        normalized = self.projects.path(pid) / value['file']
        mtime = normalized.stat().st_mtime_ns
        self.assertTrue(normalized.name.endswith('_24fps.mp4'))
        self.assertEqual(value['upload_sha256'], hashlib.sha256(raw).hexdigest())
        with patch('pipeline.ffmpeg', side_effect=AssertionError('Must not normalize a committed asset again')):
            recovered = self.post(route, body)
        self.assertEqual(recovered.status_code, 201, recovered.text)
        self.assertEqual(recovered.json()['id'], value['id'])
        self.assertEqual(normalized.stat().st_mtime_ns, mtime)

    def test_pending_asset_recovery_rejects_tampered_file_and_conflicting_reservation(self):
        pid = self.project()
        folder = self.projects.path(pid)
        body = {'type': 'image', 'name': 'reference', 'data': self.png()}
        route = f'/api/v2/projects/{pid}/assets'
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('receipt unavailable')):
            self.post(route, body)
        value = next(iter(read_json(folder / 'assets.json').values()))
        with self.assertRaises(ContractError) as caught:
            self.assets.add_image(pid, self.png('red'), asset_id=value['id'], operation_id=value['operation_id'])
        self.assertEqual(caught.exception.code, 'ASSET_RESERVATION_CONFLICT')
        (folder / value['file']).write_bytes(b'tampered asset')
        response = self.post(route, body)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()['code'], 'ASSET_CHANGED')

    def test_routes_require_request_keys_and_typed_bounded_inputs(self):
        cases = [('/api/v2/images', self.image_body), ('/api/v2/image-inputs', {'data': self.png()}),
                 ('/api/v2/projects/missing/assets', {'data': self.png(), 'type': 'image'})]
        for route, body in cases:
            with self.subTest(route=route):
                response = self.client.post(route, json=body)
                self.assertEqual(response.status_code, 422, response.text)
        unknown = self.post(body={**self.image_body, 'download_confirmation': 'not accepted'})
        self.assertEqual(unknown.status_code, 422)
        unknown_inner = self.post(body={'request': {'prompt': 'idea', 'unknown': True}})
        self.assertEqual(unknown_inner.status_code, 422)
        invalid = self.post('/api/v2/image-inputs', {'data': '%%%badbase64'}, key='bad-input')
        self.assertEqual(invalid.status_code, 400)
        schema = self.client.get('/openapi.json').json()['components']['schemas']
        self.assertEqual(schema['ImageInputUpload']['properties']['data']['maxLength'], 11_000_000)
        self.assertEqual(schema['AssetUpload']['properties']['data']['maxLength'], 11_000_000)
        self.assertEqual(self.db.jobs(), [])


if __name__ == '__main__':
    unittest.main()
