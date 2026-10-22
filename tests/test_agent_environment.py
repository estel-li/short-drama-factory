import hashlib
import unittest
from unittest.mock import patch

from app import api, speech
from app.contracts import ContractError
from app.storage import write_json
from tests import test_agent_api as fixtures


class AgentEnvironmentTests(unittest.TestCase):
    def setUp(self):
        fixtures.AgentAPITests.setUp(self)

    def test_config_patch_preserves_unknown_fields_and_rejects_stale_revision(self):
        value = self.config.get()
        value['future_extension'] = {'keep': 7}
        write_json(self.config.path, value)
        current = self.client.get('/api/v2/config').json()
        body = {'expected_revision': current['revision'], 'changes': {'proxy': 'http://127.0.0.1:9999'}}
        response = self.client.patch('/api/v2/config', json=body, headers={'Idempotency-Key': 'config-edit'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.config.get()['future_extension'], {'keep': 7})
        retry = self.client.patch('/api/v2/config', json=body, headers={'Idempotency-Key': 'config-edit'})
        self.assertEqual(retry.json(), response.json())
        stale = self.client.patch('/api/v2/config', json=body, headers={'Idempotency-Key': 'stale-edit'})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['code'], 'REVISION_CONFLICT')
        self.assertNotIn('_agent_receipts', self.client.get('/api/v2/config').json()['config'])

    def test_config_saved_before_response_failure_recovers_original_result(self):
        current = self.client.get('/api/v2/config').json()
        body = {'expected_revision': current['revision'], 'changes': {'proxy': 'http://127.0.0.1:9999'}}
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('response storage unavailable')):
            first = self.client.patch('/api/v2/config', json=body, headers={'Idempotency-Key': 'lost-config'})
        self.assertEqual(first.status_code, 400)
        recovered = self.client.patch('/api/v2/config', json=body, headers={'Idempotency-Key': 'lost-config'})
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(recovered.json()['revision'], self.client.get('/api/v2/config').json()['revision'])

    def test_busy_queue_prevents_configuration_changes(self):
        current = self.client.get('/api/v2/config').json()
        self.db.enqueue('other', 'render')
        result = self.client.patch('/api/v2/config', json={'expected_revision': current['revision'], 'changes': {'proxy': ''}},
                                   headers={'Idempotency-Key': 'busy-config'})
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json()['code'], 'QUEUE_BUSY')

    def test_speech_plan_read_only_and_prepare_requires_matching_confirmation(self):
        raw = b'fake-vad-bytes'
        write_json(self.root / 'manifests/quality.json', {'model': {'filename': 'vad.onnx', 'size': len(raw),
                   'sha256': hashlib.sha256(raw).hexdigest(), 'url': 'https://invalid.test/model'}})
        with patch.object(speech, 'ROOT', self.root), patch('app.downloads.Downloader.fetch') as fetch, \
                patch.object(self.worker, 'start') as start, patch.object(self.worker, 'allow_job') as allow:
            plan = self.client.get('/api/v2/environment/speech/plan').json()
            self.assertEqual(plan['download_bytes'], len(raw))
            self.assertFalse((self.root / 'data/quality').exists())
            denied = self.client.post('/api/v2/environment/speech/prepare', json={}, headers={'Idempotency-Key': 'no-confirm'})
            self.assertEqual(denied.status_code, 409)
            self.assertEqual(self.db.jobs(), [])
            body = {'download_confirmation': plan['confirmation_token']}
            accepted = self.client.post('/api/v2/environment/speech/prepare', json=body, headers={'Idempotency-Key': 'prepare-vad'})
            self.assertEqual(accepted.status_code, 202)
            repeated = self.client.post('/api/v2/environment/speech/prepare', json=body, headers={'Idempotency-Key': 'prepare-vad'})
            self.assertEqual(repeated.json(), accepted.json())
            self.assertEqual(len(self.db.jobs()), 1)
            fetch.assert_not_called()
            self.assertEqual(start.call_args.kwargs, {'recover': False})
            self.assertEqual(allow.call_args.args[0], accepted.json()['job_id'])

    def test_persisted_async_failure_retains_machine_recovery_instructions(self):
        project = self.projects.create('fixture', {})
        jid = self.db.enqueue(project.name, 'render')
        error = ContractError('PLAN_STALE', '模型改变，Bearer secret-value', status=409,
                              next_actions=['create_execution_plan'])
        self.worker.record_failure(self.db.job(jid), error)
        row = self.client.get('/api/jobs/' + jid).json()
        self.assertEqual(row['failure']['code'], 'PLAN_STALE')
        self.assertEqual(row['next_actions'], ['create_execution_plan'])
        self.assertNotIn('secret-value', str(row))
        self.db.requeue_job(jid)
        self.assertIsNone(self.client.get('/api/jobs/' + jid).json()['failure'])


if __name__ == '__main__':
    unittest.main()
