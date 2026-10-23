"""Agent HTTP workflows in an isolated store; never start a worker or a provider."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import api
from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.quality import render_contract
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class AgentOperationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
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
        self.start = self.mock_object(self.worker, 'start')
        self.allow = self.mock_object(self.worker, 'allow_job')
        self.mock_object(self.content, 'call', side_effect=AssertionError('No text provider calls'))
        self.mock('requests.sessions.Session.request', side_effect=AssertionError('No network requests'))
        self.mock('pipeline.Runner.run', side_effect=AssertionError('No renderer execution'))
        self.model_observations = self.mock('app.execution_plan._model_observations', return_value=[
            {'role': 'fixture', 'name': 'fixture.safetensors', 'availability': 'unknown'}])
        self.client = TestClient(api.app, base_url='http://127.0.0.1')
        self.addCleanup(self.client.close)
        self.body = read_json(ROOT / 'agent-skills/short-drama-factory/assets/project-storyboard.json')
        self.body.pop('start', None)
        for index, shot in enumerate(self.body['storyboard']['shots']):
            shot['uid'] = f'shot-{index + 1}'

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
    def headers(key):
        return {'Idempotency-Key': key}

    def create(self, key='create', body=None):
        response = self.client.post('/api/v2/projects', json=copy.deepcopy(self.body if body is None else body),
                                    headers=self.headers(key))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def plan(self, pid, **request):
        response = self.client.post(f'/api/v2/projects/{pid}/plans', json=request)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def run_plan(self, pid, plan, key='run'):
        return self.client.post(f'/api/v2/projects/{pid}/run', json={'plan_id': plan['plan_id']},
                                headers=self.headers(key))

    def test_default_external_creation_does_not_queue_or_start(self):
        body = {'input': self.body['input'], 'storyboard': self.body['storyboard']}
        result = self.create(body=body)
        view = self.client.get('/api/v2/projects/' + result['id'])
        self.assertEqual(view.status_code, 200, view.text)
        self.assertEqual(view.json()['settings']['input_mode'], 'storyboard')
        self.assertEqual(view.json()['settings']['execution_mode'], 'auto')
        self.assertFalse(view.json()['settings']['auto_reference'])
        self.assertEqual(view.json()['revision'], result['revision'])
        self.assertIsNone(result['job_id'])
        self.assertEqual(self.db.jobs(), [])
        self.start.assert_not_called()
        self.allow.assert_not_called()
        self.assertIsNone(self.worker.thread)

    def test_orphaned_running_job_can_stop_then_resume_without_a_worker(self):
        pid = self.create()['id']
        plan = self.plan(pid)
        jid = self.run_plan(pid, plan).json()['job_id']
        self.db.claim({jid})
        self.assertIsNone(self.worker.thread)
        stopped = self.client.post('/api/v2/jobs/' + jid + '/stop', json={}, headers=self.headers('orphan-stop'))
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()['status'], 'paused')
        self.assertFalse(self.projects.get(pid)['busy'])
        resumed = self.client.post('/api/v2/jobs/' + jid + '/resume', json={}, headers=self.headers('orphan-resume'))
        self.assertEqual(resumed.status_code, 202, resumed.text)
        self.assertEqual(resumed.json()['job_id'], jid)
        self.assertEqual(self.db.job(jid)['status'], 'queued')
        self.assertEqual(len(self.db.jobs()), 1)

    def test_resume_recovers_only_the_requested_orphaned_running_job(self):
        pid = self.create()['id']
        jid = self.run_plan(pid, self.plan(pid)).json()['job_id']
        old = self.db.enqueue('other-orphan', 'render')
        self.db.claim({jid})
        self.db.claim({old})
        result = self.client.post('/api/v2/jobs/' + jid + '/resume', json={}, headers=self.headers('direct-orphan-resume'))
        self.assertEqual(result.status_code, 202, result.text)
        self.assertEqual(result.json()['job_id'], jid)
        self.assertEqual(self.db.job(jid)['status'], 'queued')
        self.assertEqual(self.db.job(old)['status'], 'running')

    def test_selected_text_plan_only_compiles_approved_shots_and_skips_outline(self):
        body = copy.deepcopy(self.body)
        body['options']['input_mode'] = 'idea'
        for shot in body['storyboard']['shots']:
            shot['prompt'] = ''
        pid = self.create(body=body)['id']
        project = self.projects.path(pid)
        # An idea project may already have a user-approved storyboard while its
        # optional outline is absent; selected prompt work must not invent one.
        write_json(project / '分镜.json', self.projects.normalize(pid, body['storyboard']))
        plan = self.plan(pid, action='plan', internal_text='allowed', uids=['shot-1'])
        self.assertTrue(plan['ready'], plan['blocked'])
        self.assertEqual(plan['affected_uids'], ['shot-1'])
        effect = next(item for item in plan['effects'] if item['kind'] == 'text')
        self.assertEqual((effect['action'], effect['scope'], effect['uids']),
                         ('compile_selected_prompts', 'selected_shots', ['shot-1']))
        jid = self.run_plan(pid, plan).json()['job_id']
        job = self.db.claim({jid})
        before = read_json(project / '分镜.json')['shots'][1]

        def compile_fixture(folder, story, shot, *args):
            shot['prompt'] = 'offline compiled ' + shot['uid']
            write_json(folder / '分镜.json', story)
            return shot['prompt']

        with patch.object(self.content, 'outline', side_effect=AssertionError('No project-wide outline work')), \
                patch.object(self.content, 'storyboard', side_effect=AssertionError('No project-wide storyboard work')), \
                patch.object(self.content, 'prompt_shot', side_effect=compile_fixture) as compile_shot:
            self.assertEqual(self.worker.execute(job), 'done')
        self.assertEqual([call.args[2]['uid'] for call in compile_shot.call_args_list], ['shot-1'])
        after = read_json(project / '分镜.json')
        self.assertEqual(after['shots'][1], before)
        self.assertEqual(after['shots'][0]['prompt'], 'offline compiled shot-1')
        self.assertFalse((project / 'outline.json').exists())

    def test_whole_text_plan_without_story_compiles_all_new_shots(self):
        body = copy.deepcopy(self.body)
        storyboard = body.pop('storyboard')
        body['options']['input_mode'] = 'idea'
        for shot in storyboard['shots']:
            shot['prompt'] = ''
        pid = self.create(body=body)['id']
        project = self.projects.path(pid)
        plan = self.plan(pid, action='plan', internal_text='allowed')
        self.assertTrue(plan['ready'], plan['blocked'])
        self.assertEqual(plan['affected_uids'], [])
        jid = self.run_plan(pid, plan).json()['job_id']
        job = self.db.claim({jid})
        with patch.object(self.content, 'outline', side_effect=lambda *args: write_json(project / 'outline.json', {'title': 'offline'})), \
                patch.object(self.content, 'storyboard', side_effect=lambda *args, **kwargs: write_json(project / '分镜.json', storyboard)), \
                patch.object(self.content, 'prompt_shot', return_value='offline') as compile_shot:
            self.assertEqual(self.worker.execute(job), 'done')
        self.assertEqual([call.args[2]['uid'] for call in compile_shot.call_args_list], ['shot-1', 'shot-2'])

    def test_text_plan_reference_preparation_uses_expanded_approved_scope(self):
        body = copy.deepcopy(self.body)
        body['options']['reference_images'] = {'enabled': True}
        for shot in body['storyboard']['shots']:
            shot['prompt'] = ''
        pid = self.create(body=body)['id']
        plan = self.plan(pid, action='plan', internal_text='allowed', uids=['shot-1'])
        self.assertTrue(plan['ready'], plan['blocked'])
        self.assertEqual(plan['requested_uids'], ['shot-1'])
        self.assertEqual(plan['affected_uids'], ['shot-1', 'shot-2'])
        effect = next(item for item in plan['effects'] if item['action'] == 'fill_or_compile_story_and_prompts')
        self.assertEqual(effect['scope'], 'project')
        self.assertEqual(effect['uids'], ['shot-1', 'shot-2'])
        jid = self.run_plan(pid, plan).json()['job_id']
        job = self.db.claim({jid})
        with patch.object(self.worker.images, 'ensure_references') as prepare, \
                patch.object(self.content, 'prompt_shot', return_value='offline') as compile_shot:
            self.assertEqual(self.worker.execute(job), 'done')
        prepare.assert_called_once()
        self.assertEqual([call.args[2]['uid'] for call in compile_shot.call_args_list], ['shot-1', 'shot-2'])

    def test_create_replay_and_conflict_preserve_one_project(self):
        result = self.create()
        self.assertEqual(self.create(), result)
        changed = copy.deepcopy(self.body)
        changed['input'] = 'different creation request'
        conflict = self.client.post('/api/v2/projects', json=changed, headers=self.headers('create'))
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()['code'], 'IDEMPOTENCY_CONFLICT')
        self.assertEqual([item['id'] for item in self.projects.list()], [result['id']])
        operation = self.client.get('/api/v2/operations/create').json()
        self.assertEqual(operation['status'], 'completed')
        self.assertEqual(operation['result'], result)
        self.assertNotIn(self.body['input'], json.dumps(operation))

    def test_create_recovers_published_folder_before_receipt_completion(self):
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('simulated crash after folder publication')):
            failed = self.client.post('/api/v2/projects', json=self.body, headers=self.headers('crash'))
        self.assertGreaterEqual(failed.status_code, 400)
        receipt = self.db.operation('crash')
        self.assertEqual(receipt['status'], 'pending')
        existing = self.projects.list()
        self.assertEqual(len(existing), 1)
        pid = existing[0]['id']
        self.assertEqual(read_json(self.projects.path(pid) / 'creation-receipt.json')['operation_id'], receipt['operation_id'])
        result = self.create('crash')
        self.assertEqual(result['id'], pid)
        self.assertEqual(result['operation_id'], receipt['operation_id'])
        self.assertEqual(len(self.projects.list()), 1)
        self.assertEqual(list((self.root / 'projects').glob('.creating-*')), [])
        self.assertEqual(self.db.jobs(), [])

    def test_patch_rejects_stale_editor_and_preserves_unknown_fields_and_uids(self):
        body = copy.deepcopy(self.body)
        body['storyboard']['external_metadata'] = {'editor': 'kept'}
        body['storyboard']['shots'][0]['unknown_extension'] = {'nested': ['retain']}
        created = self.create(body=body)
        pid, original_revision = created['id'], created['revision']
        request = {'expected_revision': original_revision,
                   'shots': [{'uid': 'shot-1', 'changes': {'summary': 'The same cup with a new composition.'}}]}
        updated = self.client.patch('/api/v2/projects/' + pid, json=request, headers=self.headers('edit-one'))
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertNotEqual(updated.json()['revision'], original_revision)
        stale = self.client.patch('/api/v2/projects/' + pid, json={**request,
                                  'shots': [{'uid': 'shot-2', 'changes': {'summary': 'stale editor text'}}]},
                                  headers=self.headers('edit-two'))
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(stale.json()['code'], 'REVISION_CONFLICT')
        story = self.client.get('/api/v2/projects/' + pid).json()['story']
        self.assertEqual(story['external_metadata'], {'editor': 'kept'})
        self.assertEqual(story['shots'][0]['unknown_extension'], {'nested': ['retain']})
        self.assertEqual([shot['uid'] for shot in story['shots']], ['shot-1', 'shot-2'])
        self.assertEqual(story['shots'][1]['summary'], self.body['storyboard']['shots'][1]['summary'])
        self.assertIn('shot-1', updated.json()['invalidated_prompts'])

    def test_patch_replay_returns_old_receipt_after_a_new_edit(self):
        created = self.create()
        pid = created['id']
        first_body = {'expected_revision': created['revision'], 'settings': {'subtitles': True}}
        first = self.client.patch('/api/v2/projects/' + pid, json=first_body, headers=self.headers('edit-first'))
        self.assertEqual(first.status_code, 200, first.text)
        second = self.client.patch('/api/v2/projects/' + pid,
                                   json={'expected_revision': first.json()['revision'], 'settings': {'music': 'N/A changed'}},
                                   headers=self.headers('edit-next'))
        self.assertEqual(second.status_code, 200, second.text)
        replay = self.client.patch('/api/v2/projects/' + pid, json=first_body, headers=self.headers('edit-first'))
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json(), first.json())
        current = self.client.get('/api/v2/projects/' + pid).json()
        self.assertEqual(current['revision'], second.json()['revision'])
        self.assertEqual(current['settings']['music'], 'N/A changed')

    def test_patch_recovers_effect_before_receipt_completion(self):
        created = self.create()
        pid = created['id']
        request = {'expected_revision': created['revision'], 'settings': {'subtitles': True}}
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('simulated receipt failure')):
            failed = self.client.patch('/api/v2/projects/' + pid, json=request, headers=self.headers('edit-crash'))
        self.assertGreaterEqual(failed.status_code, 400)
        self.assertTrue(self.projects.get(pid)['settings']['subtitles'])
        recovered = self.client.patch('/api/v2/projects/' + pid, json=request, headers=self.headers('edit-crash'))
        self.assertEqual(recovered.status_code, 200, recovered.text)
        self.assertEqual(recovered.json()['revision'], self.projects.revision(pid))
        self.assertEqual(self.db.operation('edit-crash')['status'], 'completed')

    def test_shot_patch_recovers_effect_without_duplicate_history(self):
        created = self.create()
        pid = created['id']
        request = {'expected_revision': created['revision'],
                   'shots': [{'uid': 'shot-1', 'changes': {'summary': 'A repaired shot composition.'}}]}
        with patch.object(self.db, 'complete_operation', side_effect=RuntimeError('simulated receipt failure')):
            failed = self.client.patch('/api/v2/projects/' + pid, json=request, headers=self.headers('shot-crash'))
        self.assertGreaterEqual(failed.status_code, 400)
        before_replay = self.projects.get(pid)
        recovered = self.client.patch('/api/v2/projects/' + pid, json=request, headers=self.headers('shot-crash'))
        self.assertEqual(recovered.status_code, 200, recovered.text)
        self.assertIn('shot-1', recovered.json()['invalidated_prompts'])
        after_replay = self.projects.get(pid)
        self.assertEqual(after_replay['versions'], before_replay['versions'])
        self.assertEqual(after_replay['story'], before_replay['story'])

    def test_plan_defaults_strict_and_run_is_idempotent_without_execution(self):
        pid = self.create()['id']
        plan = self.plan(pid)
        self.assertTrue(plan['strict'])
        self.assertEqual(plan['effective_internal_text'], 'forbid')
        self.assertTrue(plan['ready'], plan['blocked'])
        self.assertEqual(self.db.jobs(), [])
        self.start.assert_not_called()
        self.assertEqual(self.client.get(f'/api/v2/projects/{pid}/plans/{plan["plan_id"]}').json(), plan)
        response = self.run_plan(pid, plan)
        self.assertEqual(response.status_code, 202, response.text)
        result = response.json()
        replay = self.run_plan(pid, plan)
        self.assertEqual(replay.status_code, 202, replay.text)
        self.assertEqual(replay.json(), result)
        self.assertEqual(len(self.db.jobs()), 1)
        payload = json.loads(self.db.job(result['job_id'])['payload'])
        self.assertTrue(payload['strict_render'])
        self.assertEqual(payload['internal_text'], 'forbid')
        self.assertEqual(payload['allowed_uids'], ['shot-1', 'shot-2'])
        self.assertTrue(all(call.kwargs == {'recover': False} for call in self.start.call_args_list))
        self.allow.assert_any_call(result['job_id'])
        self.assertIsNone(self.worker.thread)

    def test_queued_run_retry_recovers_dispatch_failure(self):
        pid = self.create()['id']
        plan = self.plan(pid)
        self.start.side_effect = RuntimeError('simulated startup failure after durable enqueue')
        failed = self.run_plan(pid, plan, 'dispatch-crash')
        self.assertGreaterEqual(failed.status_code, 400)
        self.assertEqual(len(self.db.jobs()), 1)
        jid = self.db.jobs()[0]['id']
        self.start.side_effect = None
        self.start.reset_mock()
        self.allow.reset_mock()
        recovered = self.run_plan(pid, plan, 'dispatch-crash')
        self.assertEqual(recovered.status_code, 202, recovered.text)
        self.assertEqual(recovered.json()['job_id'], jid)
        self.assertEqual(len(self.db.jobs()), 1)
        self.start.assert_called_once_with(recover=False)
        self.allow.assert_called_once_with(jid)

    def test_run_replay_never_resurrects_completed_task(self):
        pid = self.create()['id']
        plan = self.plan(pid)
        original = self.run_plan(pid, plan)
        self.assertEqual(original.status_code, 202, original.text)
        jid = original.json()['job_id']
        self.db.update(jid, 'done')
        self.start.reset_mock()
        self.allow.reset_mock()
        replay = self.run_plan(pid, plan)
        self.assertEqual(replay.json(), original.json())
        self.assertEqual(self.db.job(jid)['status'], 'done')
        self.start.assert_not_called()
        self.allow.assert_not_called()

    def test_resume_retry_recovers_dispatch_failure_without_second_requeue(self):
        pid = self.create()['id']
        jid = self.db.enqueue(pid, 'render')
        self.db.update(jid, 'paused')
        self.start.side_effect = RuntimeError('simulated resume startup failure')
        failed = self.client.post('/api/v2/jobs/' + jid + '/resume', json={}, headers=self.headers('resume-crash'))
        self.assertGreaterEqual(failed.status_code, 400)
        event_cursor = self.db.job_events(jid)['next_cursor']
        self.start.side_effect = None
        self.start.reset_mock()
        self.allow.reset_mock()
        replay = self.client.post('/api/v2/jobs/' + jid + '/resume', json={}, headers=self.headers('resume-crash'))
        self.assertEqual(replay.status_code, 202, replay.text)
        self.assertEqual(replay.json()['job_id'], jid)
        self.assertEqual(self.db.job_events(jid, after=event_cursor)['items'], [])
        self.start.assert_called_once_with(recover=False)
        self.allow.assert_called_once_with(jid)

    def test_changed_asset_bytes_reject_original_plan(self):
        pid = self.create()['id']
        project = self.projects.path(pid)
        (project / 'asset.png').write_bytes(b'original bytes')
        write_json(project / 'assets.json', {'asset-one': {'file': 'asset.png', 'sha256': 'unchanged-manifest-hash'}})
        plan = self.plan(pid)
        (project / 'asset.png').write_bytes(b'updated bytes')
        rejected = self.run_plan(pid, plan)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertIn(rejected.json()['code'], ('PLAN_STALE', 'REVISION_CONFLICT'))
        self.assertEqual(self.db.jobs(), [])

    def test_changed_source_clip_bytes_reject_original_plan(self):
        pid = self.create()['id']
        project = self.projects.path(pid)
        story = self.projects.get(pid)['story']
        (project / 'clips').mkdir()
        source = project / 'clips/source.mp4'
        source.write_bytes(b'original rendered source')
        state = read_json(project / 'state.json')
        state['shots_by_uid'] = {'shot-1': {'status': 'done', 'clip_relative': 'clips/source.mp4',
                                            'render_contract': render_contract(story, story['shots'][0])}}
        write_json(project / 'state.json', state)
        plan = self.plan(pid)
        source.write_bytes(b'changed rendered source')
        rejected = self.run_plan(pid, plan)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertEqual(rejected.json()['code'], 'PLAN_STALE')
        self.assertEqual(self.db.jobs(), [])

    def test_changed_profile_rejects_original_plan(self):
        pid = self.create()['id']
        plan = self.plan(pid)
        value = self.config.get()
        value['environment']['profiles']['draft']['steps'] += 1
        self.config.save(value)
        rejected = self.run_plan(pid, plan)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertEqual(rejected.json()['code'], 'PLAN_STALE')
        self.assertEqual(self.db.jobs(), [])

    def test_missing_model_plan_blocks_without_starting_worker(self):
        pid = self.create()['id']
        self.model_observations.return_value = [{'role': 'fixture', 'name': 'missing.safetensors', 'availability': 'missing'}]
        plan = self.plan(pid)
        self.assertFalse(plan['ready'])
        self.assertIn('MODEL_FILES_MISSING', [item['code'] for item in plan['blocked']])
        response = self.run_plan(pid, plan)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()['code'], 'PLAN_BLOCKED')
        self.start.assert_not_called()
        self.assertEqual(self.db.jobs(), [])

    def test_stop_and_resume_target_original_job_without_touching_other_owner(self):
        first = self.create('create-first')['id']
        second = self.create('create-second')['id']
        jid = self.db.enqueue(first, 'render', {'strict_render': True})
        other = self.db.enqueue(second, 'render')
        stopped = self.client.post('/api/v2/jobs/' + jid + '/stop', json={}, headers=self.headers('stop-first'))
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(self.db.job(jid)['status'], 'paused')
        self.assertEqual(self.db.job(other)['status'], 'queued')
        self.assertFalse(self.db.job(other)['cancel_requested'])
        body = {'expected_revision': self.projects.revision(first)}
        resumed = self.client.post('/api/v2/jobs/' + jid + '/resume', json=body, headers=self.headers('resume-first'))
        self.assertEqual(resumed.status_code, 202, resumed.text)
        self.assertEqual(resumed.json()['job_id'], jid)
        replay = self.client.post('/api/v2/jobs/' + jid + '/resume', json=body, headers=self.headers('resume-first'))
        self.assertEqual(replay.status_code, 202, replay.text)
        self.assertEqual(replay.json(), resumed.json())
        self.assertEqual(len(self.db.jobs()), 2)
        self.assertTrue(json.loads(self.db.job(jid)['payload'])['strict_render'])
        # Replaying stop cannot cancel the later resumed job again.
        self.assertEqual(self.client.post('/api/v2/jobs/' + jid + '/stop', json={},
                                         headers=self.headers('stop-first')).json(), stopped.json())
        self.assertEqual(self.db.job(jid)['status'], 'queued')

    def test_terminal_job_stop_does_not_cancel_newer_same_project_job(self):
        pid = self.create()['id']
        old = self.db.enqueue(pid, 'outline')
        self.db.update(old, 'done')
        current = self.db.enqueue(pid, 'render')
        response = self.client.post('/api/v2/jobs/' + old + '/stop', json={}, headers=self.headers('stop-old'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.db.job(current)['status'], 'queued')
        self.assertFalse(self.db.job(current)['cancel_requested'])

    def test_all_state_changing_routes_require_request_key(self):
        pid = self.create()['id']
        revision = self.projects.revision(pid)
        cases = [('post', '/api/v2/projects', self.body),
                 ('patch', '/api/v2/projects/' + pid, {'expected_revision': revision, 'settings': {'subtitles': True}}),
                 ('post', f'/api/v2/projects/{pid}/run', {'plan_id': 'a' * 64}),
                 ('post', '/api/v2/jobs/missing/resume', {}),
                 ('post', '/api/v2/jobs/missing/stop', {})]
        for method, path, body in cases:
            with self.subTest(path=path):
                response = getattr(self.client, method)(path, json=body)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(response.json()['code'], 'VALIDATION_ERROR')
                self.assertTrue(any(item['field'] == 'header.idempotency-key' for item in response.json()['details']))
        self.assertEqual(len(self.projects.list()), 1)
        self.assertEqual(self.db.jobs(), [])
        self.start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
