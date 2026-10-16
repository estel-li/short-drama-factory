import base64
import io
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

from app.assets import Assets
from app.config import ConfigStore
from app.database import Database
from app.image_sampling import resolve_sampling
from app.image_schemas import ImageRequest, ImageSampling, ImageSettings
from app.image_studio import ImageStudio, image_graph
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json
from app.transfer import Transfer


class ImageSamplingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        config = self.config.get(); config['projects_dir'] = str(self.root / 'projects'); self.config.save(config)
        self.db = Database(self.root / 'data/test.sqlite3'); self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.studio = ImageStudio(self.config, self.db, self.projects, self.assets, Skills())
        self.plan = {'ready': True, 'comfy_url': 'http://image.test', 'variant': 'turbo-int8', 'recommendation': {'resolution': 512},
                     'models': [{'category': c, 'name': c, 'comfy_name': c} for c in ('diffusion_models', 'text_encoders', 'vae')]}

    def test_defaults_preserve_official_turbo_and_standard_graphs(self):
        request = ImageRequest(prompt='p', seed=1)
        graph, _, _ = image_graph(request, 'p', self.plan, self.studio.environment.manifest, 'test')
        self.assertEqual(graph['10']['class_type'], 'ManualSigmas')
        self.assertEqual(graph['13']['class_type'], 'BasicGuider')
        self.assertEqual(resolve_sampling(request, 'turbo-int8')['steps'], 8)
        graph, _, _ = image_graph(request, 'p', {**self.plan, 'variant': 'quality-int8'}, self.studio.environment.manifest, 'test')
        self.assertEqual(graph['7']['inputs']['steps'], 40)
        self.assertEqual(graph['7']['inputs']['denoise'], 1)
        self.assertNotIn('15', graph)

    def test_custom_sampling_and_source_latent_reach_both_real_sampler_paths(self):
        request = ImageRequest(prompt='p', seed=2, reference_images=['a' * 64], reference_mode='edit', resolution='512',
                               sampling={'steps': 12, 'cfg': 2.5, 'sampler': 'dpmpp_2m', 'scheduler': 'karras', 'denoise': .65, 'negative_prompt': 'watermark'})
        for variant in ('turbo-int8', 'quality-int8'):
            graph, width, height = image_graph(request, 'p', {**self.plan, 'variant': variant}, self.studio.environment.manifest, 'test',
                                               [{'comfy_name': 'ref.png', 'width': 128, 'height': 192}])
            self.assertEqual(graph['3']['inputs']['negative_prompt'], 'watermark')
            self.assertEqual(graph['7']['inputs']['latent_image'], ['15', 0])
            self.assertEqual(graph['15']['inputs'], {'pixels': ['14', 0], 'vae': ['5', 0]})
            self.assertEqual(graph['14']['inputs']['image'], ['21', 0])
            self.assertEqual((graph['14']['inputs']['width'], graph['14']['inputs']['height']), (width, height))
            self.assertLess(width, height)
            sampler = graph['10']['inputs'] if variant.startswith('turbo') else graph['7']['inputs']
            self.assertEqual((sampler['steps'], sampler['scheduler'], sampler['denoise']), (12, 'karras', .65))
            if variant.startswith('turbo'):
                self.assertEqual(graph['13']['class_type'], 'CFGGuider')
                self.assertEqual(graph['13']['inputs']['cfg'], 2.5)
                self.assertEqual(graph['11']['inputs']['sampler_name'], 'dpmpp_2m')
            else:
                self.assertEqual((sampler['cfg'], sampler['sampler_name']), (2.5, 'dpmpp_2m'))
        request.sampling.scheduler = 'auto'
        self.assertEqual(resolve_sampling(request, 'turbo-int8')['scheduler'], 'simple')

    def test_invalid_ranges_and_incompatible_modes_are_rejected(self):
        for value in ({'steps': 0}, {'steps': 101}, {'steps': 1.5}, {'cfg': float('nan')}, {'cfg': float('inf')},
                      {'cfg': .5}, {'cfg': 21}, {'denoise': 0}, {'denoise': 1.1}, {'sampler': 'unknown'},
                      {'scheduler': 'unknown'}, {'negative_prompt': 'x' * 4001}):
            with self.assertRaises(ValueError): ImageSampling.model_validate(value)
        for raw in ({}, {'reference_images': ['a' * 64]}, {'reference_mode': 'edit'}):
            with self.assertRaises(ValueError): ImageRequest(prompt='p', sampling={'denoise': .5}, **raw)

    def test_default_settings_are_snapshotted_and_sampling_edits_keep_optimized_task(self):
        config = self.config.get(); config['image_generation']['sampling'] = ImageSampling(steps=16, cfg=2).model_dump(); self.config.save(config)
        task = self.studio.create({'prompt': 'p', 'optimized_prompt': 'approved prompt'})
        config['image_generation']['sampling']['steps'] = 24; self.config.save(config)
        self.assertEqual(self.studio.get(task['id'])['request']['sampling']['steps'], 16)
        jid = self.db.enqueue(task['owner'], 'image-optimize', {'image_id': task['id']})
        self.db.update(jid, status='done')
        self.studio.update(task['id'], job_id=jid, optimized_prompt='approved prompt')
        started = self.studio.start(task['id'], self.db.enqueue, {'sampling': ImageSampling(steps=20).model_dump()})
        self.assertEqual(started['job_id'], jid)
        self.assertEqual(self.studio.get(task['id'])['optimized_prompt'], 'approved prompt')
        self.assertEqual(self.studio.get(task['id'])['request']['sampling']['steps'], 20)
        self.assertEqual(ImageSettings.model_validate({}).sampling.steps, None)

    def test_unsupported_engine_fails_before_upload_or_submission(self):
        task = self.studio.create({'prompt': 'p', 'optimize': False, 'sampling': {'steps': 12}})
        support = {'samplers': ['euler'], 'schedulers': ['simple'], 'nodes': []}
        with patch.object(self.studio.environment, 'plan', return_value={**self.plan, 'sampling_support': support}), \
             patch.object(self.studio, 'request') as request, patch.object(self.studio, 'upload_references') as upload:
            with self.assertRaisesRegex(ValueError, '高级采样节点'):
                self.studio.generate(task['id'], lambda *a, **k: None, lambda: False)
        request.assert_not_called(); upload.assert_not_called()
        self.assertNotIn('prompt_id', self.studio.get(task['id']))

    def test_legacy_history_regeneration_keeps_legacy_defaults(self):
        from app import api
        task = self.studio.create({'prompt': 'p', 'optimize': False})
        request = task['request']; request.pop('sampling')
        self.studio.update(task['id'], request=request)
        config = self.config.get(); config['image_generation']['sampling'] = ImageSampling(steps=24, cfg=3).model_dump(); self.config.save(config)
        client = TestClient(api.app, base_url='http://127.0.0.1'); self.addCleanup(client.close)
        with patch.object(api, 'worker', SimpleNamespace(images=self.studio, enqueue=self.db.enqueue)):
            response = client.post('/api/images/' + task['id'] + '/regenerate', json={})
            self.assertEqual(response.status_code, 202)
            result = response.json()
        retry = self.studio.get(result['id'])
        self.assertIsNone(retry['request']['sampling']['steps'])
        self.assertEqual(retry['request']['sampling']['cfg'], 1)

    def test_character_sampling_persists_and_transfers_with_project(self):
        pid = self.projects.create('test', {'input_mode': 'storyboard'}, {'title': 'test',
            'characters': [{'id': 'hero', 'name': '小雨', 'visual_description': '黄衣女孩'}],
            'shots': [{'characters': ['hero'], 'prompt': 'p'}]}).name
        image = io.BytesIO(); Image.new('RGB', (64, 96), 'blue').save(image, format='PNG')
        asset = self.assets.add_image(pid, base64.b64encode(image.getvalue()).decode(), '原图')
        selection = {'asset_ids': [asset['id']], 'reference_mode': 'edit', 'sampling': ImageSampling(steps=18, denoise=.6).model_dump()}
        before = self.studio.reference_signature(pid, self.studio.candidates(pid)[0])
        self.studio.set_reference_sources(pid, 'character-hero', selection)
        request = self.studio.reference_request(pid, 'character-hero')
        self.assertEqual(request['sampling']['steps'], 18)
        self.assertEqual(request['sampling']['denoise'], .6)
        self.studio.set_reference_sources(pid, 'character-hero', {'asset_ids': [asset['id']], 'reference_mode': 'edit'})
        self.assertEqual(self.studio.reference_request(pid, 'character-hero')['sampling'], selection['sampling'])
        self.assertNotEqual(before, self.studio.reference_signature(pid, self.studio.candidates(pid)[0]))
        transfer = Transfer(self.config, self.projects, Skills(self.root / 'transfer-skills'))
        imported = transfer.import_package(transfer.export([pid]))['projects'][0]
        self.assertEqual(self.studio.reference_request(imported, 'character-hero')['sampling'], selection['sampling'])
        with self.assertRaises(ValueError): self.studio.set_reference_sources(pid, 'character-hero', {**selection, 'reference_mode': 'reference'})
        self.studio.set_reference_sources(pid, 'character-hero', {**selection, 'sampling': None})
        self.assertIsNone(self.studio.candidates(pid)[0]['sampling'])


if __name__ == '__main__': unittest.main()
