import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.config import ConfigStore
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.providers import Cancelled
from app.schemas import Options, Quality
from app.skills import Skills
from app.storage import read_json, write_json
from app.transfer import Transfer
from app.workflow_checks import workflow_report


def setup(root, profiles=None):
    config = ConfigStore(root)
    value = config.get()
    value['environment']['profiles'] = {
        'draft': {'label': 'Draft', 'megapixels': .4, 'steps': 4}, **(profiles or {})}
    config.save(value)
    db = Database(root / 'queue.sqlite3')
    with patch('app.projects.ROOT', root), patch('app.series.ROOT', root):
        projects = Projects(config, db)
        worker = Worker(db, config, projects, None, None)
    return config, db, projects, worker


class WorkerFailureTests(unittest.TestCase):
    def test_offline_project_does_not_stop_other_queued_projects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, db, projects, worker = setup(root)
            first = projects.create('first', {})
            second = projects.create('second', {})
            first_job = db.enqueue(first.name, 'all')
            second_job = db.enqueue(second.name, 'all')
            offline = root / 'offline-project'
            self.assertTrue(first.resolve().is_relative_to(root.resolve()))
            self.assertTrue(offline.resolve().is_relative_to(root.resolve()))
            first.rename(offline)

            def execute(job):
                projects.path(job['project_id'])
                worker.shutdown.set()
                return 'done'

            worker.execute = execute
            worker.loop()
            statuses = {job['id']: job['status'] for job in db.jobs()}
            self.assertEqual(statuses, {first_job: 'error', second_job: 'done'})
            self.assertIsNone(worker.active)

    def test_cancelled_job_with_corrupt_state_does_not_stop_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, db, projects, worker = setup(root)
            first = projects.create('first', {})
            second = projects.create('second', {})
            (first / 'state.json').write_text('{bad json', encoding='utf-8')
            first_job = db.enqueue(first.name, 'all')
            second_job = db.enqueue(second.name, 'all')

            def execute(job):
                if job['id'] == first_job:
                    raise Cancelled('Stopped')
                worker.shutdown.set()
                return 'done'

            worker.execute = execute
            worker.loop()
            self.assertEqual({job['id']: job['status'] for job in db.jobs()},
                             {first_job: 'paused', second_job: 'done'})

    def test_unwritable_state_and_log_still_enforce_series_failure_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, db, projects, worker = setup(root)
            first, second, third = [projects.create(text, {}) for text in ('first', 'second', 'third')]
            series_jobs = db.enqueue_many([
                (project.name, 'all', {'series_id': 'test-series', 'fail_policy': 'stop'})
                for project in (first, second)], 'test-batch')
            last_job = db.enqueue(third.name, 'all')
            (root / 'logs').write_text('cannot create log directory', encoding='utf-8')

            def execute(job):
                if job['id'] == series_jobs[0]:
                    raise RuntimeError('original failure')
                worker.shutdown.set()
                return 'done'

            worker.execute = execute
            with (patch.object(worker, 'image_failure', side_effect=PermissionError('image state')),
                 patch('app.jobs.write_json', side_effect=PermissionError('project state')),
                 patch.object(worker.series, 'mark_paused', side_effect=PermissionError('series state'))):
                worker.loop()
            self.assertEqual({job['id']: job['status'] for job in db.jobs()},
                             {series_jobs[0]: 'error', series_jobs[1]: 'paused', last_job: 'done'})


class SkillStorageTests(unittest.TestCase):
    def test_render_only_replaces_original_template_placeholders(self):
        with tempfile.TemporaryDirectory() as folder:
            skills = Skills(Path(folder))
            skills.save('literal', {'name': 'Literal', 'stage': 'outline'},
                        {'SKILL.md': '{{style}} / {{music}}'})
            text, _ = skills.render('literal', 'outline', {'style': '{{music}}', 'music': '{{style}}'})
            self.assertEqual(text, '{{music}} / {{style}}')

    def test_save_counts_only_selected_context_and_render_header(self):
        with tempfile.TemporaryDirectory() as folder:
            skills = Skills(Path(folder))
            metadata = {'name': 'Small context', 'stage': 'outline', 'context_references': []}
            files = {'SKILL.md': 'short', 'reference.md': 'x' * 65000}
            skills.save('small', metadata, files)
            text, snapshot = skills.render('small', 'outline', {})
            self.assertEqual(text, '## 文件：SKILL.md\n\nshort')
            self.assertEqual(snapshot['loaded_files'], ['SKILL.md'])
            with self.assertRaisesRegex(ValueError, '64000'):
                skills.save('large', {**metadata, 'context_references': ['reference.md']}, files)
            self.assertFalse((Path(folder) / 'large').exists())
            with self.assertRaises(ValueError):
                skills.save('null', {**metadata, 'context_references': None}, files)


class TransferProfilesTests(unittest.TestCase):
    profile = {'label': 'My workflow', 'megapixels': .6, 'steps': 8}

    def transfer(self, root, profiles=None):
        config, _, projects, _ = setup(root, profiles)
        return config, projects, Transfer(config, projects, Skills(root / 'skills'))

    def create_project(self, projects, profile='custom-test'):
        return projects.create('', {'input_mode': 'storyboard', 'profile': profile},
                               {'title': 'Portable project', 'shots': [{'prompt': 'manual'}]})

    def rewrite_manifest(self, source, target, change):
        with zipfile.ZipFile(source) as incoming, zipfile.ZipFile(target, 'w') as outgoing:
            for name in incoming.namelist():
                value = incoming.read(name)
                if name == 'transfer.json':
                    manifest = json.loads(value)
                    change(manifest)
                    value = json.dumps(manifest).encode()
                outgoing.writestr(name, value)

    def test_custom_profile_roundtrip_keeps_sampling_without_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, projects, exporter = self.transfer(root / 'source', {
                'custom-test': self.profile, 'unrelated': {**self.profile, 'steps': 6}})
            value = source.get()
            value['environment'].update(comfy_dir='C:/private/comfy', comfy_auth_token='not-portable')
            source.save(value)
            project = self.create_project(projects)
            archive = exporter.export([project.name])
            with zipfile.ZipFile(archive) as package:
                manifest = json.loads(package.read('transfer.json'))
            self.assertEqual(manifest['profiles'], {'custom-test': Quality.model_validate(self.profile).model_dump()})
            self.assertNotIn('environment', manifest)
            target, restored, importer = self.transfer(root / 'target')
            before = target.get()['environment'].copy()
            pid = importer.import_package(archive)['projects'][0]
            options = restored.options(restored.path(pid))
            self.assertEqual(options.profile, 'custom-test')
            self.assertEqual(target.renderer_config()['profiles']['custom-test'], manifest['profiles']['custom-test'])
            self.assertEqual({k: v for k, v in target.get()['environment'].items() if k != 'profiles'},
                             {k: v for k, v in before.items() if k != 'profiles'})
            report = workflow_report(restored.get(pid)['story'], options, target.renderer_config(),
                                     lambda *args: {}, lambda *args: 'T2VA')
            self.assertTrue(report['ready'])

    def test_conflicting_profile_maps_project_and_personal_preset(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, projects, exporter = self.transfer(root / 'source', {'custom-test': self.profile})
            project = self.create_project(projects)
            write_json(root / 'source/presets/personal.json', {
                'favorite': {'name': 'Favorite', 'options': Options(profile='custom-test').model_dump()}})
            archive = exporter.export([project.name])
            target, restored, importer = self.transfer(root / 'target', {
                'custom-test': {**self.profile, 'steps': 6}})
            existing = copy.deepcopy(target.renderer_config()['profiles']['custom-test'])
            pid = importer.import_package(archive)['projects'][0]
            profile_id = restored.options(restored.path(pid)).profile
            self.assertNotEqual(profile_id, 'custom-test')
            self.assertEqual(target.renderer_config()['profiles']['custom-test'], existing)
            self.assertEqual(target.renderer_config()['profiles'][profile_id], Quality.model_validate(self.profile).model_dump())
            self.assertEqual(read_json(root / 'target/presets/personal.json')['favorite']['options']['profile'], profile_id)

    def test_identical_profile_reuses_existing_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, projects, exporter = self.transfer(root / 'source', {'custom-test': self.profile})
            project = self.create_project(projects)
            target, restored, importer = self.transfer(root / 'target', {'custom-test': self.profile})
            before = target.get()['environment']['profiles']
            pid = importer.import_package(exporter.export([project.name]))['projects'][0]
            self.assertEqual(restored.options(restored.path(pid)).profile, 'custom-test')
            self.assertEqual(target.get()['environment']['profiles'], before)

    def test_legacy_manifest_without_profiles_remains_importable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, projects, exporter = self.transfer(root / 'source')
            project = self.create_project(projects, 'draft')
            archive = exporter.export([project.name])
            legacy = root / 'legacy.zip'
            self.rewrite_manifest(archive, legacy, lambda value: value.pop('profiles'))
            _, restored, importer = self.transfer(root / 'target')
            pid = importer.import_package(legacy)['projects'][0]
            self.assertEqual(restored.options(restored.path(pid)).profile, 'draft')

    def test_removed_legacy_profile_does_not_prevent_project_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, projects, exporter = self.transfer(root, {'custom-test': self.profile})
            project = self.create_project(projects)
            value = source.get()
            value['environment']['profiles'].pop('custom-test')
            source.save(value)
            with zipfile.ZipFile(exporter.export([project.name])) as package:
                manifest = json.loads(package.read('transfer.json'))
            self.assertIn(project.name, manifest['projects'])
            self.assertEqual(manifest['profiles'], {})

    def test_non_quality_profile_fields_are_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, projects, exporter = self.transfer(root / 'source', {'custom-test': self.profile})
            project = self.create_project(projects)
            archive = exporter.export([project.name])
            invalid = root / 'invalid.zip'
            self.rewrite_manifest(archive, invalid, lambda value: value['profiles']['custom-test'].update(comfy_dir='C:/private'))
            target, restored, importer = self.transfer(root / 'target')
            before = target.get()
            with self.assertRaises(ValueError):
                importer.import_package(invalid)
            self.assertEqual(target.get(), before)
            self.assertEqual(restored.list(), [])


if __name__ == '__main__':
    unittest.main()
