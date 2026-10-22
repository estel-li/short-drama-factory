"""Frozen plans at Worker.execute, using fake local bytes and a mocked renderer.

A hard crash can leave generated files without a committed execution checkpoint.
When those inputs differ, recovery must ask for a new plan rather than rerunning
the stale job. A clean pause can resume its existing ID and checkpoint.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import execution_guard
from app.assets import Assets
from app.config import ConfigStore
from app.content import Content, keyframe_prefix
from app.contracts import ContractError
from app.database import Database
from app.execution_plan import build_plan
from app.execution_policy import current_policy
from app.jobs import Worker
from app.projects import Projects
from app.quality import render_contract
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class ExecutionGuardTests(unittest.TestCase):
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
        self.mock('requests.sessions.Session.request', side_effect=AssertionError('No network'))
        self.mock('pipeline.Runner.run', side_effect=AssertionError('No real renderer'))
        self.mock_object(self.content, 'call', side_effect=AssertionError('No text provider'))
        self.mock_object(self.worker, 'start', side_effect=AssertionError('No worker thread'))
        self.failures = self.mock_object(self.worker, 'log_failure')
        self.model = self.root / 'comfy/models/diffusion_models/fixture.safetensors'
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b'not real weights: fixture version one')
        self.renderer = {'profiles': {'draft': {'label': 'fixture', 'workflow': 'native', 'megapixels': .4,
                                              'steps': 4, 'turbo': False}},
                         'mode': 'existing', 'comfy_dir': str(self.root / 'comfy'),
                         'comfy_url': 'http://127.0.0.1:8188', 'fl_model': self.model.name}
        self.mock_object(self.config, 'renderer_config', side_effect=lambda: copy.deepcopy(self.renderer))
        request = read_json(ROOT / 'agent-skills/short-drama-factory/assets/project-storyboard.json')
        for index, shot in enumerate(request['storyboard']['shots']):
            shot['uid'] = f'shot-{index + 1}'
        self.project = self.projects.create(request['input'], request['options'], request['storyboard'])
        self.pid = self.project.name
        self.request = {'action': 'render', 'internal_text': 'forbid', 'regenerate': False}

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

    def queue_plan(self):
        revision = self.projects.revision(self.pid)
        self.plan = build_plan(self.projects, self.assets, self.content, self.config,
                               self.pid, self.request, revision)
        self.assertTrue(self.plan['ready'], self.plan['blocked'])
        self.assertEqual(self.plan['models'][0]['availability'], 'local')
        write_json(self.project / 'execution-plans' / (self.plan['plan_id'] + '.json'),
                   {'request': self.request, 'plan': self.plan})
        payload = {'plan_id': self.plan['plan_id'], 'agent_plan': True, 'strict_render': True,
                   'internal_text': 'forbid', 'allowed_uids': self.plan['affected_uids']}
        self.jid = self.db.enqueue(self.pid, 'render', payload)
        self.job = self.db.claim(allowed_ids={self.jid})
        self.receipt_path = self.project / 'execution-plans' / ('job-' + self.jid + '.json')
        return self.job

    def publish_clip(self, uid='shot-1', data=b'generated clip fixture'):
        story = self.projects.get(self.pid)['story']
        shot = next(item for item in story['shots'] if item['uid'] == uid)
        relative = 'clips/' + uid + '.mp4'
        clip = self.project / relative
        clip.parent.mkdir(exist_ok=True)
        clip.write_bytes(data)
        state = read_json(self.project / 'state.json', {})
        state.setdefault('shots_by_uid', {})[uid] = {'status': 'done', 'clip_relative': relative,
                                                     'render_contract': render_contract(story, shot)}
        write_json(self.project / 'state.json', state)
        return clip

    def assert_blocked_before_execution(self):
        with patch.object(self.worker, '_execute', side_effect=AssertionError('Stale plan reached renderer')) as execute:
            with self.assertRaises(ContractError) as caught:
                self.worker.execute(self.job)
        self.assertEqual(caught.exception.code, 'PLAN_STALE')
        execute.assert_not_called()

    def checkpoint_generated_clip(self):
        self.queue_plan()

        def generate(job):
            self.clip = self.publish_clip()
            return 'paused'

        with patch.object(self.worker, '_execute', side_effect=generate):
            self.assertEqual(self.worker.execute(self.job), 'paused')
        self.db.update(self.jid, 'paused')
        return read_json(self.receipt_path)

    def test_valid_plan_is_accepted_and_installs_strict_policy_at_boundary(self):
        self.queue_plan()
        before = current_policy()

        def execute(job):
            self.assertEqual(job['id'], self.jid)
            self.assertEqual(current_policy().internal_text, 'forbid')
            self.assertFalse(current_policy().allow_downloads)
            return 'done'

        with patch.object(self.worker, '_execute', side_effect=execute) as boundary:
            self.assertEqual(self.worker.execute(self.job), 'done')
        boundary.assert_called_once_with(self.job)
        self.assertEqual(current_policy(), before)
        receipt = read_json(self.receipt_path)
        self.assertEqual(receipt['resume_input_fingerprint'], self.plan['input_fingerprint'])
        self.assertIsNone(self.worker.thread)

    def test_changed_settings_after_queue_blocks_before_execution(self):
        self.queue_plan()
        value = read_json(self.project / 'settings.json')
        value['seed'] += 1
        write_json(self.project / 'settings.json', value)
        self.assert_blocked_before_execution()
        self.assertFalse(self.receipt_path.exists())

    def test_changed_local_model_file_after_queue_blocks_before_execution(self):
        self.queue_plan()
        self.model.write_bytes(b'fixture replacement weights with different size')
        self.assert_blocked_before_execution()

    def test_changed_asset_bytes_after_queue_blocks_before_execution(self):
        asset = self.project / 'reference.png'
        asset.write_bytes(b'first reference bytes')
        write_json(self.project / 'assets.json', {'reference': {'file': 'reference.png', 'sha256': 'stale-manifest'}})
        self.queue_plan()
        asset.write_bytes(b'other reference bytes')
        self.assert_blocked_before_execution()

    def test_changed_predecessor_clip_after_queue_blocks_before_execution(self):
        story = self.projects.get(self.pid)['story']
        for shot in story['shots']:
            shot.update(scene='same-scene', scene_id='same-scene')
        story['shots'][1]['use_previous_last_frame'] = True
        story['shots'][1]['prompt'] = keyframe_prefix('I2VA', 107 / 24) + '\n\n' + story['shots'][1]['prompt']
        write_json(self.project / '分镜.json', story)
        predecessor = self.publish_clip()
        self.request['uids'] = ['shot-2']
        self.queue_plan()
        self.assertTrue(any(edge['source_uid'] == 'shot-1' and edge['target_uid'] == 'shot-2'
                            for edge in self.plan['dependencies']))
        predecessor.write_bytes(b'replaced predecessor ending')
        self.assert_blocked_before_execution()

    def test_clean_pause_checkpoint_allows_same_job_resume_with_generated_clip(self):
        checkpoint = self.checkpoint_generated_clip()
        self.assertNotEqual(checkpoint['resume_input_fingerprint'], self.plan['input_fingerprint'])
        self.db.requeue_job(self.jid)
        resumed = self.db.claim(allowed_ids={self.jid})
        self.assertEqual(resumed['id'], self.job['id'])
        with patch.object(self.worker, '_execute', return_value='done') as execute:
            self.assertEqual(self.worker.execute(resumed), 'done')
        execute.assert_called_once_with(resumed)
        self.assertEqual(self.db.job(self.jid)['attempts'], 2)
        self.assertEqual(self.clip.read_bytes(), b'generated clip fixture')
        self.assertFalse(read_json(self.receipt_path).get('requires_replan', False))

    def test_changed_clip_after_checkpoint_blocks_resume(self):
        self.checkpoint_generated_clip()
        self.clip.write_bytes(b'user replacement after checkpoint')
        self.assert_blocked_before_execution()

    def test_changed_model_after_checkpoint_blocks_resume(self):
        self.checkpoint_generated_clip()
        self.model.write_bytes(b'new model after checkpoint')
        self.assert_blocked_before_execution()

    def test_checkpoint_failure_keeps_original_error_and_requires_new_plan(self):
        self.queue_plan()
        original = RuntimeError('original renderer failure')
        real_build = execution_guard.build_plan
        calls = []

        def plan(*args, **kwargs):
            calls.append(True)
            if len(calls) > 1:
                raise OSError('checkpoint filesystem unavailable')
            return real_build(*args, **kwargs)

        with patch.object(execution_guard, 'build_plan', side_effect=plan), \
                patch.object(self.worker, '_execute', side_effect=original):
            with self.assertRaises(RuntimeError) as caught:
                self.worker.execute(self.job)
        self.assertIs(caught.exception, original)
        self.assertTrue(read_json(self.receipt_path)['requires_replan'])
        self.assertTrue(self.failures.called)
        self.assert_blocked_before_execution()

    def test_corrupt_checkpoint_does_not_mask_original_execution_error(self):
        self.queue_plan()
        original = RuntimeError('original generation error')

        def fail(job):
            self.receipt_path.write_text('incomplete receipt json', encoding='utf-8')
            raise original

        with patch.object(self.worker, '_execute', side_effect=fail):
            with self.assertRaises(RuntimeError) as caught:
                self.worker.execute(self.job)
        self.assertIs(caught.exception, original)
        self.assertTrue(read_json(self.receipt_path)['requires_replan'])

    def test_hard_crash_without_checkpoint_rejects_changed_generated_inputs(self):
        self.queue_plan()
        receipt = execution_guard.begin_execution(self.worker, self.job, json.loads(self.job['payload']))
        self.assertEqual(receipt, self.receipt_path)
        # Simulate process death after saving a clip: no finally/checkpoint ran.
        self.publish_clip(data=b'generated just before hard process crash')
        self.assert_blocked_before_execution()
        self.assertEqual(read_json(self.receipt_path)['resume_input_fingerprint'], self.plan['input_fingerprint'])

    def test_checkpoint_does_not_authorize_model_replaced_during_execution(self):
        self.queue_plan()

        def paused(job):
            self.publish_clip()
            self.model.write_bytes(b'unplanned model replacement during the active run')
            return 'paused'

        with patch.object(self.worker, '_execute', side_effect=paused):
            self.worker.execute(self.job)
        # Generated clips may become resume inputs; unrelated model changes may not.
        self.assert_blocked_before_execution()


if __name__ == '__main__':
    unittest.main()
