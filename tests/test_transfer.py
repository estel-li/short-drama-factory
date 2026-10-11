import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.config import ConfigStore
from app.database import Database
from app.projects import Projects
from app.skills import Skills
from app.storage import write_json
from app.transfer import Transfer


class TransferTests(unittest.TestCase):
    def test_roundtrip_removes_keys_and_rebinds_project(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_json(root / 'config.json', {'profiles': {'draft': {'label': 'test', 'megapixels': .4, 'steps': 4, 'turbo': True}}})
            config = ConfigStore(root)
            config.set_key('deepseek', 'fake-secret-for-transfer')
            db = Database(root / 'queue.sqlite3')
            projects = Projects(config, db)
            project = projects.create('输入含有 fake-secret-for-transfer，导出后应脱敏。', {}, None)
            skills = Skills(root / 'skills')
            skills.save('custom', {'name': 'test', 'stage': 'outline'}, {'SKILL.md': 'fake-secret-for-transfer {{style}}'})
            transfer = Transfer(config, projects, skills)
            (project / 'assets').mkdir()
            (project / 'assets/ref.mp4').write_bytes(b'reference-video-content')
            write_json(project / 'assets.json', {'ref': {'id': 'ref', 'type': 'video', 'name': 'reference', 'file': 'assets/ref.mp4'}})
            path = transfer.export([project.name])
            with zipfile.ZipFile(path) as archive:
                self.assertNotIn(b'fake-secret-for-transfer', b''.join(archive.read(n) for n in archive.namelist()))
                self.assertFalse(any('.secrets' in n for n in archive.namelist()))
            imported = transfer.import_package(path)
            self.assertEqual(len(imported['projects']), 1)
            self.assertNotEqual(imported['projects'][0], project.name)
            restored = projects.get(imported['projects'][0])
            self.assertIn('[REDACTED]', restored['outline'])
            self.assertEqual(config.key('deepseek'), 'fake-secret-for-transfer')
            self.assertEqual(restored['assets']['ref']['file'], 'assets/ref.mp4')
            self.assertEqual((projects.path(restored['id']) / 'assets/ref.mp4').read_bytes(), b'reference-video-content')

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = ConfigStore(root)
            projects = Projects(config, Database(root / 'db.sqlite3'))
            transfer = Transfer(config, projects, Skills(root / 'skills'))
            path = root / 'bad.zip'
            manifest = {'kind': 'drama-factory-transfer', 'version': 2, 'projects': {'project': {}},
                        'files': {'projects/project/../../../escape.txt': 'bad'}}
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('transfer.json', json.dumps(manifest))
            with self.assertRaises(ValueError):
                transfer.import_package(path)


if __name__ == '__main__':
    unittest.main()
