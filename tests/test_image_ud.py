import copy
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.config import ConfigStore
from app.downloads import Downloader
from app.image_environment import DownloadConfirmationRequired, ImageEnvironment
from app.image_models import QWEN_UD_MODEL, qwen_manifest
from app.image_sampling import sampling_for_plan
from app.image_schemas import ImageRequest, ImageSettings, ReferenceImageOptions
from app.image_studio import ImageStudio, image_graph
from app.storage import ROOT, read_json, write_json


class QwenUDTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        value = self.config.get()
        value['image_generation'] = {'engine': 'shared', 'comfy_url': 'http://127.0.0.1:8188',
                                    'models_dir': str(self.root / 'models'), 'variant': 'turbo-bf16'}
        self.config.save(value)
        self.environment = ImageEnvironment(self.config)
        self.probe = {'connected': True, 'missing_nodes': [], 'reference_support': True,
                      'gpu': {'name': 'test GPU'}, 'vram_mb': 48 * 1024, 'choices': {}}

    def test_catalog_schemas_and_pinned_download_sources(self):
        from app.api import image_model_catalog
        spec = image_model_catalog()['models'][QWEN_UD_MODEL]
        self.assertEqual(spec['name'], 'Qwen2.1 UD版')
        self.assertTrue(spec['auto_prepare_on_select'])
        self.assertEqual(spec['max_reference_images'], 10)
        for schema in (ImageSettings, ReferenceImageOptions):
            self.assertEqual(schema(image_model=QWEN_UD_MODEL).image_model, QWEN_UD_MODEL)
        manifest = qwen_manifest(QWEN_UD_MODEL)
        for model in manifest['models'].values():
            self.assertIn(manifest['source'] + '/resolve/' + manifest['revision'] + '/', model['url'])
            self.assertEqual(len(model['sha256']), 64)
            self.assertGreater(model['size'], 0)
            self.assertTrue(model['name'].endswith('.safetensors'))
        self.assertNotEqual(manifest['models']['quality']['name'], self.environment.manifest['models']['quality']['name'])
        self.assertEqual(manifest['models']['vae']['sha256'], self.environment.manifest['models']['vae']['sha256'])

    def test_ud_plan_does_not_inherit_official_turbo_and_preserves_model_identity(self):
        with patch.object(self.environment, 'probe', return_value=self.probe):
            ud = self.environment.plan(image_model=QWEN_UD_MODEL)
            official = self.environment.plan()
            with self.assertRaisesRegex(ValueError, '不支持'):
                self.environment.plan('turbo-int8', image_model=QWEN_UD_MODEL)
        self.assertEqual((ud['image_model'], ud['variant']), (QWEN_UD_MODEL, 'quality-int8'))
        self.assertEqual(official['variant'], 'turbo-bf16')
        self.assertEqual(ud['max_reference_images'], 10)
        self.assertNotEqual(ud['confirmation_token'], official['confirmation_token'])
        self.assertEqual(ud['models_dir'], official['models_dir'])
        self.assertEqual(ud['models_download_bytes'], 17_283_104_888)

    def test_ud_graph_uses_standard_sampler_and_all_reference_inputs(self):
        studio = SimpleNamespace(environment=self.environment)
        request = ImageStudio.image_request(studio, {'image_model': QWEN_UD_MODEL, 'prompt': '参考 <image1> 和 <image2>',
            'reference_images': ['a' * 64, 'b' * 64], 'reference_mode': 'edit', 'transparent': True})
        with patch.object(self.environment, 'probe', return_value=self.probe):
            plan = self.environment.plan(image_model=QWEN_UD_MODEL)
        references = [{'comfy_name': name, 'width': 600, 'height': 800} for name in ('one.png', 'two.png')]
        graph, width, height = image_graph(request, request.prompt, plan, self.environment.manifest, 'test', references)
        self.assertEqual(graph['1']['inputs']['unet_name'], 'qwen-image-2.1-UC-int8_convrot.safetensors')
        self.assertEqual(graph['2']['inputs']['type'], 'qwen_image')
        self.assertEqual(graph['7']['class_type'], 'KSampler')
        self.assertEqual(graph['7']['inputs']['steps'], 25)
        self.assertEqual(graph['3']['inputs']['images.image_2'], ['22', 0])
        self.assertLess(width, height)
        self.assertEqual(sampling_for_plan(request, plan)['steps'], 25)
        request.sampling.steps = None
        self.assertEqual(sampling_for_plan(request, plan)['steps'], 25)
        with self.assertRaisesRegex(ValueError, 'Turbo'):
            image_graph(request, request.prompt, {**plan, 'variant': 'turbo-int8'}, self.environment.manifest, 'test', references)

    def test_preparation_downloads_verified_files_once_without_generating_images(self):
        manifest = copy.deepcopy(qwen_manifest(QWEN_UD_MODEL))
        contents = {}
        for model in manifest['models'].values():
            data = model['name'].encode()
            model.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
            contents[model['name']] = data
        choices = {}
        def fetch(url, target, size, sha256, report, cancel, token):
            target = Path(target)
            data = contents[target.name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            self.assertTrue(Downloader().verified(target, size, sha256))
            choices.setdefault(target.parent.name, []).append(target.name)
        with patch('app.image_environment.qwen_manifest', return_value=manifest), \
             patch.object(self.environment, 'probe', side_effect=lambda url: {**self.probe, 'choices': choices}), \
             patch.object(Downloader, 'fetch', side_effect=fetch) as download:
            plan = self.environment.plan(image_model=QWEN_UD_MODEL)
            with self.assertRaises(DownloadConfirmationRequired):
                self.environment.prepare('auto', lambda *a, **k: None, lambda: False, image_model=QWEN_UD_MODEL)
            download.assert_not_called()
            result = self.environment.prepare('auto', lambda *a, **k: None, lambda: False,
                                              confirmation=plan['confirmation_token'], image_model=QWEN_UD_MODEL)
            self.assertTrue(result['ready'])
            self.assertEqual(download.call_count, 3)
            self.assertEqual([call.args[0] for call in download.call_args_list], [m['url'] for m in manifest['models'].values()])
            self.assertTrue(self.environment.prepare('auto', lambda *a, **k: None, lambda: False, image_model=QWEN_UD_MODEL)['ready'])
            self.assertEqual(download.call_count, 3)

    def test_remote_service_cannot_receive_local_model_downloads(self):
        value = self.config.get()
        value['image_generation']['comfy_url'] = 'https://image.test'
        self.config.save(value)
        with patch.object(self.environment, 'probe', return_value=self.probe):
            plan = self.environment.plan(image_model=QWEN_UD_MODEL)
        self.assertFalse(plan['local_download'])


if __name__ == '__main__':
    unittest.main()
