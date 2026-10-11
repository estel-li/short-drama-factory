import json
import tempfile
import unittest
from pathlib import Path

from app.config import ConfigStore
from app.database import Database
from app.projects import Projects
from app.schemas import Options, Provider, durations
from app.skills import Skills


class CoreTests(unittest.TestCase):
    def test_provider_cannot_reuse_installation_credentials(self):
        for name in ('hf', 'HF', 'comfy', 'Comfy'):
            with self.assertRaises(ValueError):
                Provider(id=name, name='test', base_url='http://localhost:8080/v1')

    def test_duration_precedence(self):
        total = durations(Options(total_seconds=15, shot_seconds=4, shot_count=40))
        self.assertEqual(total['count'], 3)
        self.assertAlmostEqual(total['allocated_total'], 15)
        count = durations(Options(duration_rule='count', total_seconds=15, shot_count=10))
        self.assertEqual(count['count'], 10)
        self.assertEqual(count['allocated_total'], 40)
        manual = durations(Options(duration_rule='manual', manual_durations=[4, 8]))
        self.assertEqual(manual['frames'], [107, 192])
        with self.assertRaises(ValueError):
            durations(Options(duration_rule='manual', manual_durations=[3]))

    def test_job_recovery_and_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / 'queue.sqlite3')
            jid = db.enqueue('project', 'all')
            self.assertEqual(db.claim()['id'], jid)
            self.assertIsNone(db.claim())
            with self.assertRaises(ValueError):
                db.enqueue('project', 'all')
            db.recover()
            self.assertEqual(db.claim()['id'], jid)
            db.cancel('project')
            self.assertTrue(db.cancelled(jid))
            db.recover()
            self.assertEqual(db.jobs()[0]['status'], 'paused')

    def test_skill_path_and_variables(self):
        with tempfile.TemporaryDirectory() as folder:
            skills = Skills(folder)
            with self.assertRaises(ValueError):
                skills.save('a', {'name': 'test', 'stage': 'outline'}, {'SKILL.md': 'test', '../../escape.txt': 'no'})
            skills.save('a', {'name': 'test', 'stage': 'outline'}, {'SKILL.md': '{{style}} {{missing}}'})
            with self.assertRaises(ValueError):
                skills.render('a', 'outline', {'style': 'cartoon'})
            text, snapshot = skills.render('a', 'outline', {'style': 'cartoon', 'missing': 'ok'})
            self.assertEqual(text, 'cartoon ok')
            self.assertTrue(snapshot['content_hash'])

    def test_config_secret_separation(self):
        with tempfile.TemporaryDirectory() as folder:
            config = ConfigStore(folder)
            config.set_key('deepseek', 'test-secret-value')
            self.assertNotIn('test-secret-value', json.dumps(config.public()))
            self.assertTrue(config.public()['providers'][0]['key_configured'])


if __name__ == '__main__':
    unittest.main()
