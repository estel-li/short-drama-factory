"""Agent contract checks against isolated projects, without provider or GPU work."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import api
from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class AgentAPITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/jobs.sqlite3')
        project_root = patch('app.projects.ROOT', self.root)
        project_root.start()
        self.addCleanup(project_root.stop)
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.content = Content(self.config, Skills(), self.projects)
        self.worker = Worker(self.db, self.config, self.projects, self.content, self.assets)
        for name in ('config', 'db', 'projects', 'assets', 'content', 'worker'):
            item = patch.object(api, name, getattr(self, name))
            item.start()
            self.addCleanup(item.stop)
        self.client = TestClient(api.app, base_url='http://127.0.0.1')
        self.addCleanup(self.client.close)

    def test_invalid_input_has_actionable_fields_without_original_values(self):
        result = self.client.post('/api/projects', json={'input': 'hello', 'start': False,
                                  'options': {'private_token': 'never-echo-this-value'}})
        self.assertEqual(result.status_code, 400)
        error = result.json()
        self.assertEqual(error['code'], 'VALIDATION_ERROR')
        self.assertTrue(error['details'])
        self.assertEqual(error['details'][0]['field'], 'body.options.private_token')
        self.assertNotIn('never-echo-this-value', result.text)
        self.assertTrue(error['next_actions'])
        self.assertEqual(self.projects.list(), [])

    def test_old_job_and_events_remain_queryable_after_list_window(self):
        first = self.db.enqueue('first-project', 'plan', {'secret': 'not-public'})
        self.db.update(first, 'done', 'Planning complete')
        for index in range(105):
            self.db.enqueue('p' + str(index), 'render')
        self.assertNotIn(first, [item['id'] for item in self.client.get('/api/jobs').json()])
        response = self.client.get('/api/jobs/' + first)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['outcome'], 'stage_completed')
        self.assertNotIn('payload', response.json())
        self.assertNotIn('not-public', response.text)
        page = self.client.get('/api/jobs/page?project_id=first-project').json()
        self.assertEqual([item['id'] for item in page['items']], [first])
        events = self.client.get('/api/jobs/' + first + '/events').json()
        self.assertTrue(events['items'])
        self.assertTrue(any(item['data'].get('status') == 'done' for item in events['items']))
        following = self.client.get('/api/jobs/' + first + '/events', params={'after': events['next_cursor']}).json()
        self.assertEqual(following['items'], [])
        missing = self.client.get('/api/jobs/missing')
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['code'], 'JOB_NOT_FOUND')

    def test_doctor_does_not_start_any_work_when_engine_unavailable(self):
        with patch.object(api, 'health', return_value={'version': api.VERSION, 'comfy': False}), \
                patch.object(self.worker, 'enqueue', side_effect=AssertionError('Must not enqueue')), \
                patch.object(self.worker, 'start', side_effect=AssertionError('Must not start')), \
                patch.object(self.content, 'call', side_effect=AssertionError('Must not call LLM')):
            response = self.client.get('/api/doctor')
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertTrue(report['read_only'])
        self.assertFalse(report['ready'])
        self.assertEqual(report['checks'][1]['code'], 'ENGINE_UNAVAILABLE')
        self.assertEqual(self.db.jobs(), [])

    def test_core_openapi_exposes_options_story_and_stage_fields(self):
        spec = self.client.get('/openapi.json').json()
        schemas = spec['components']['schemas']
        self.assertIn('options', schemas['CreateProjectRequest']['properties'])
        self.assertIn('shots', schemas['Story']['properties'])
        self.assertIn('limit', schemas['StageRequest']['properties'])
        self.assertTrue(schemas['CreateProjectRequest']['properties']['start']['default'])
        self.assertIn('/api/jobs/{jid}', spec['paths'])


if __name__ == '__main__':
    unittest.main()
