import copy
import hashlib
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.assets import Assets
from app.config import ConfigStore
from app.database import Database
from app.downloads import Downloader
from app.image_environment import DownloadConfirmationRequired, ImageEnvironment, REQUIRED_NODES
from app.image_models import model_spec
from app.image_studio import ImageStudio
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class ImageRelease366Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)

    @contextmanager
    def environment(self, model_id, remote=False):
        settings = self.config.get()
        settings['image_generation'] = {
            'engine': 'shared', 'image_model': model_id,
            'comfy_url': 'https://gpu.example.test' if remote else 'http://127.0.0.1:8188',
            'models_dir': str(self.root / 'models/qwen'),
            'library_models_dir': str(self.root / 'models/library'),
        }
        self.config.save(settings)
        environment = ImageEnvironment(self.config)
        if model_id == 'qwen-image-2.1':
            environment.manifest = copy.deepcopy(environment.manifest)
            files = [environment.manifest['models'][role]
                     for role in environment.manifest['variants']['turbo-int8']['files']]
            directory = self.root / 'models/qwen'
            spec = None
        else:
            spec = copy.deepcopy(model_spec(model_id))
            files = spec['files']
            directory = self.root / 'models/library'
        choices, contents = {}, {}
        for model in files:
            data = ('test weight: ' + model['name']).encode()
            model.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
            target = directory / model['category'] / model['name']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            Downloader().verified(target, len(data), model['sha256'])
            contents[target] = data
            choices.setdefault(model['category'], []).append(model['name'])
        nodes = set(REQUIRED_NODES) | {
            'CLIPTextEncode', 'VAEEncode', 'ImageScale', 'LoadImage',
            'CheckpointLoaderSimple', 'EmptyLatentImage',
        }
        probe = {'connected': True, 'missing_nodes': [], 'node_types': list(nodes),
                 'choices': choices, 'gpu': {'name': 'test'}, 'vram_mb': 16384}
        with patch.object(environment, 'probe', return_value=probe), \
             patch('app.image_library.model_spec', return_value=spec):
            yield environment, contents

    def test_advertised_truncated_weights_require_repair_confirmation(self):
        for model_id in ('qwen-image-2.1', 'sdxl-base'):
            with self.subTest(model=model_id), self.environment(model_id) as (environment, contents):
                target = next(iter(contents))
                target.write_bytes(b'broken')
                plan = environment.plan(image_model=model_id)
                row = next(m for m in plan['models'] if m['target'] == str(target.resolve()))
                self.assertIsNotNone(row['comfy_name'])
                self.assertEqual(row['action'], 'download')
                self.assertFalse(plan['ready'])
                self.assertTrue(plan['requires_confirmation'])
                with patch.object(Downloader, 'fetch', side_effect=AssertionError('unconfirmed download')):
                    with self.assertRaises(DownloadConfirmationRequired):
                        environment.prepare('auto', lambda *a, **k: None, lambda: False, image_model=model_id)

    def test_advertised_unverified_weights_are_hashed_before_becoming_ready(self):
        for model_id in ('qwen-image-2.1', 'sdxl-base'):
            with self.subTest(model=model_id), self.environment(model_id) as (environment, contents):
                target = next(iter(contents))
                target.with_name(target.name + '.verified.json').unlink()
                plan = environment.plan(image_model=model_id)
                self.assertFalse(plan['ready'])
                self.assertFalse(plan['requires_confirmation'])
                self.assertEqual(plan['models'][0]['action'], 'verify')
                with patch.object(Downloader, 'fetch', side_effect=AssertionError('unnecessary download')):
                    ready = environment.prepare('auto', lambda *a, **k: None, lambda: False, image_model=model_id)
                self.assertTrue(ready['ready'])
                self.assertEqual(ready['models'][0]['action'], 'available')

    def test_checksum_failure_is_confirmed_then_repaired_even_when_advertised(self):
        for model_id in ('qwen-image-2.1', 'sdxl-base'):
            with self.subTest(model=model_id), self.environment(model_id) as (environment, contents):
                target, original = next(iter(contents.items()))
                target.write_bytes(b'x' * len(original))
                target.with_name(target.name + '.verified.json').unlink()
                with patch.object(Downloader, 'fetch', side_effect=AssertionError('unconfirmed download')):
                    with self.assertRaises(DownloadConfirmationRequired) as error:
                        environment.prepare('auto', lambda *a, **k: None, lambda: False, image_model=model_id)
                repair = error.exception.plan
                self.assertFalse(repair['ready'])
                self.assertTrue(repair['requires_confirmation'])
                self.assertEqual(repair['models'][0]['action'], 'download')

                def replace_weight(url, path, size, checksum, *args):
                    Path(path).write_bytes(contents[Path(path)])
                    self.assertTrue(Downloader().verified(path, size, checksum))
                    return Path(path)

                with patch.object(Downloader, 'fetch', side_effect=replace_weight) as fetch:
                    ready = environment.prepare('auto', lambda *a, **k: None, lambda: False,
                                                confirmation=repair['confirmation_token'], image_model=model_id)
                self.assertEqual(fetch.call_count, 1)
                self.assertTrue(ready['ready'])

    def test_remote_enumerated_weights_do_not_require_local_files(self):
        for model_id in ('qwen-image-2.1', 'sdxl-base'):
            with self.subTest(model=model_id), self.environment(model_id, remote=True) as (environment, contents):
                for target in contents:
                    target.unlink()
                with patch.object(Downloader, 'verification_status', side_effect=AssertionError('remote local check')):
                    plan = environment.plan(image_model=model_id)
                self.assertTrue(plan['ready'])
                self.assertFalse(plan['local_download'])
                self.assertTrue(all(row['action'] == 'available' for row in plan['models']))

    def test_shared_engine_may_map_models_outside_the_configured_directory(self):
        for model_id in ('qwen-image-2.1', 'sdxl-base'):
            with self.subTest(model=model_id), self.environment(model_id) as (environment, contents):
                for target in contents:
                    target.unlink()
                with patch.object(Downloader, 'fetch', side_effect=AssertionError('duplicate download')):
                    plan = environment.prepare('auto', lambda *a, **k: None, lambda: False, image_model=model_id)
                self.assertTrue(plan['ready'])
                self.assertEqual(plan['download_bytes'], 0)

    def studio(self):
        db = Database(self.root / 'data/test.sqlite3')
        projects = Projects(self.config, db)
        studio = ImageStudio(self.config, db, projects, Assets(self.config, projects), Skills())
        return studio, SimpleNamespace(images=studio, enqueue=db.enqueue)

    def test_regeneration_preserves_direct_manual_prompt_without_llm(self):
        from app import api
        studio, worker = self.studio()
        original = studio.create({'prompt': 'a room', 'optimized_prompt': 'EXACT MANUAL PROMPT'})
        studio.update(original['id'], status='complete', effective_prompt='EXACT MANUAL PROMPT')
        with patch.object(api, 'worker', worker), \
             patch('app.image_studio.LLMClient', side_effect=AssertionError('unexpected optimization')):
            result = api.image_regenerate(original['id'], {})
            prompt = studio.optimize(result['id'], lambda *a, **k: None, lambda: False)
        self.assertEqual(prompt, 'EXACT MANUAL PROMPT')
        self.assertEqual(studio.get(result['id'])['parent_id'], original['id'])

    def test_regeneration_preserves_cached_optimization_and_explicit_override(self):
        from app import api
        studio, worker = self.studio()
        original = studio.create({'prompt': 'a room'})
        studio.update(original['id'], status='complete', optimized_prompt='CACHED PROMPT')
        with patch.object(api, 'worker', worker):
            result = api.image_regenerate(original['id'], {})
            self.assertEqual(studio.get(result['id'])['request']['optimized_prompt'], 'CACHED PROMPT')
            result = api.image_regenerate(original['id'], {'request': {'prompt': 'a garden', 'optimized_prompt': 'NEW MANUAL PROMPT'}})
            self.assertEqual(studio.get(result['id'])['request']['optimized_prompt'], 'NEW MANUAL PROMPT')

    def test_regeneration_invalidates_prompt_on_semantic_changes_or_opt_out(self):
        from app import api
        studio, worker = self.studio()
        original = studio.create({'prompt': 'a room', 'optimized_prompt': 'OLD MANUAL PROMPT'})
        with patch.object(api, 'worker', worker):
            for changes in ({'prompt': 'a garden'}, {'image_model': 'sdxl-base'}, {'optimize': False}):
                with self.subTest(changes=changes):
                    result = api.image_regenerate(original['id'], {'request': changes})
                    self.assertEqual(studio.get(result['id'])['request']['optimized_prompt'], '')


if __name__ == '__main__':
    unittest.main()
