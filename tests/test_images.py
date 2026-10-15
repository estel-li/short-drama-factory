import base64
import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx

from PIL import Image

from app.assets import Assets
from app.config import ConfigStore
from app.database import Database
from app.image_environment import recommendation, image_size
from app.image_schemas import ImageRequest
from app.image_studio import ImageStudio, image_graph
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json
from app.transfer import Transfer


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/test.sqlite3')
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.studio = ImageStudio(self.config, self.db, self.projects, self.assets, Skills())
        self.plan = {'ready': True, 'comfy_url': 'http://127.0.0.1:8190', 'variant': 'turbo-int8',
                     'recommendation': recommendation(16311),
                     'models': [{'category': c, 'name': name, 'comfy_name': name} for c, name in (
                         ('diffusion_models', 'qwen-turbo.safetensors'), ('text_encoders', 'qwen-clip.safetensors'), ('vae', 'qwen-vae.safetensors'))]}

    def project(self):
        story = {'title': 'study', 'characters': [{'id': 'hero', 'name': '小雨', 'visual_description': '黄衣短发女孩'}],
                 'scenes': [{'id': 'room', 'name': '小屋', 'description': '木窗与书桌'}],
                 'shots': [{'characters': ['hero'], 'scene': '小屋', 'prompt': 'original prompt'},
                           {'characters': [], 'scene': '小屋', 'prompt': 'empty room'}]}
        return self.projects.create('study', {'input_mode': 'storyboard'}, story).name

    def completed(self, pid='', target=''):
        value = self.studio.create({'prompt': 'a room', 'optimize': False}, pid, target)
        Image.new('RGBA', (64, 64), (20, 40, 80, 255)).save(self.studio.path(value['id']) / 'image.png')
        return self.studio.update(value['id'], status='complete', file='image.png')

    def test_hardware_defaults_and_turbo_uses_official_schedule(self):
        self.assertEqual(recommendation(8 * 1024)['resolution'], 512)
        self.assertEqual(recommendation(16 * 1024)['variant'], 'turbo-int8')
        self.assertEqual(recommendation(48 * 1024)['variant'], 'turbo-bf16')
        self.assertEqual(recommendation(None)['resolution'], 768)
        request = ImageRequest(prompt='雨夜', seed=123, ratio='9:16')
        graph, width, height = image_graph(request, request.prompt, self.plan, self.studio.environment.manifest, 'test')
        self.assertEqual((width, height), image_size('9:16', 1024))
        self.assertEqual(width % 32, 0)
        self.assertEqual(height % 32, 0)
        self.assertEqual(graph['7']['class_type'], 'SamplerCustomAdvanced')
        self.assertEqual(len(graph['10']['inputs']['sigmas'].split(',')), 9)
        self.assertEqual(graph['12']['inputs']['noise_seed'], 123)
        quality, _, _ = image_graph(request, request.prompt, {**self.plan, 'variant': 'quality-int8'}, self.studio.environment.manifest, 'test')
        self.assertEqual(quality['7']['class_type'], 'KSampler')

    def test_optimization_is_default_but_off_and_manual_do_not_call_llm(self):
        self.assertTrue(ImageRequest(prompt='原文').optimize)
        for request, expected in (({'prompt': '原文', 'optimize': False}, '原文'),
                                  ({'prompt': '原文', 'optimized_prompt': '人工优化结果'}, '人工优化结果')):
            image = self.studio.create(request)
            with patch('app.image_studio.LLMClient', side_effect=AssertionError('unexpected API call')):
                self.assertEqual(self.studio.optimize(image['id'], lambda *a, **k: None, lambda: False), expected)

    def test_optimization_keeps_original_and_writes_skill_snapshot(self):
        image = self.studio.create({'prompt': '黄衣女孩', 'purpose': 'character'})
        with patch('app.image_studio.LLMClient') as client:
            client.return_value.generate.return_value = {'text': '{"prompt":"一位黄衣女孩站在干净背景前","summary":"补充构图"}', 'usage': {'total_tokens': 8}}
            prompt = self.studio.optimize(image['id'], lambda *a, **k: None, lambda: False)
        saved = self.studio.get(image['id'])
        self.assertEqual(saved['request']['prompt'], '黄衣女孩')
        self.assertEqual(saved['optimized_prompt'], prompt)
        self.assertEqual(saved['optimization']['skill']['id'], 'image-qwen-character')

    def test_generate_downloads_real_png_and_reuses_finished_result(self):
        image = self.studio.create({'prompt': 'a room', 'optimize': False})
        calls = []
        def request(url, path, body=None):
            calls.append((path, body))
            if path == '/queue': return {'queue_running': [], 'queue_pending': []}
            if path == '/prompt': return {'prompt_id': body['prompt_id']}
            if path.startswith('/history/'):
                return {path.rsplit('/', 1)[1]: {'status': {'completed': True}, 'outputs': {'9': {'images': [{'filename': 'result.png'}]}}}}
            raise AssertionError(path)
        def download(item, target, *args):
            Image.new('RGBA', (64, 64), (10, 40, 90, 0)).save(target)
        with patch.object(self.studio.environment, 'plan', return_value=self.plan), patch.object(self.studio, 'request', side_effect=request), \
             patch.object(self.studio, 'release_idle'), patch('app.image_studio.download_file', side_effect=download):
            result = self.studio.generate(image['id'], lambda *a, **k: None, lambda: False)
            self.assertTrue(result['has_transparency'])
            self.assertEqual(result['status'], 'complete')
            self.studio.generate(image['id'], lambda *a, **k: None, lambda: False)
        self.assertEqual(sum(path == '/prompt' for path, _ in calls), 1)

    def test_unknown_submit_never_posts_again_and_keeps_original_environment(self):
        image = self.studio.create({'prompt': 'a room', 'optimize': False})
        self.studio.update(image['id'], prompt_id='owned-id', submission='intent', comfy_url=self.plan['comfy_url'], model_plan=self.plan)
        with patch.object(self.studio.environment, 'plan', side_effect=AssertionError('must use saved plan')), \
             patch.object(self.studio, 'release_idle'), patch.object(self.studio, 'request', return_value={}) as request:
            with self.assertRaisesRegex(RuntimeError, '提交结果未知'):
                self.studio.generate(image['id'], lambda *a, **k: None, lambda: False)
        self.assertFalse(any(c.args[1] == '/prompt' for c in request.call_args_list))

    def test_stop_only_targets_owned_prompt(self):
        image = self.studio.create({'prompt': 'a room', 'optimize': False})
        self.studio.update(image['id'], prompt_id='mine', comfy_url=self.plan['comfy_url'])
        with patch.object(self.studio, 'request', return_value={'queue_running': [[0, 'other']], 'queue_pending': []}) as request:
            self.studio.interrupt(image['id'])
            self.assertEqual(request.call_count, 1)
        with patch.object(self.studio, 'request', return_value={'queue_running': [[0, 'mine']], 'queue_pending': []}) as request:
            self.studio.interrupt(image['id'])
            self.assertEqual(request.call_args.args[1:], ('/interrupt', {'prompt_id': 'mine'}))

    def test_comfy_control_routes_may_return_empty_success(self):
        with patch('app.image_studio.httpx.Client') as client:
            client.return_value.__enter__.return_value.post.return_value = httpx.Response(200, content=b'')
            self.assertEqual(self.studio.request('http://127.0.0.1:8190', '/free', {'unload_models': True}), {})

    def test_scene_reference_preserves_manual_character_and_empty_shot_has_no_identity(self):
        pid = self.project()
        png = io.BytesIO(); Image.new('RGB', (32, 32), 'blue').save(png, format='PNG')
        identity = self.assets.add_image(pid, base64.b64encode(png.getvalue()).decode(), 'hero', 'hero')
        candidates = self.studio.candidates(pid)
        scenes = [c for c in candidates if c['kind'] == 'scene']
        self.assertEqual(len(scenes), 1)
        image = self.completed(pid, scenes[0]['key'])
        first = self.studio.adopt(pid, scenes[0]['key'], image['id'])
        project = self.projects.get(pid)
        self.assertFalse(project['assets'][first['asset_id']]['character'])
        self.assertEqual(set(project['story']['shots'][0]['bindings']['images']), {first['asset_id'], identity['id']})
        self.assertEqual(project['story']['shots'][1]['bindings']['images'], [first['asset_id']])
        self.assertEqual(project['story']['shots'][0]['prompt'], '')
        second_image = self.completed(pid, scenes[0]['key'])
        second = self.studio.adopt(pid, scenes[0]['key'], second_image['id'])
        self.assertNotEqual(first['asset_id'], second['asset_id'])
        with patch.object(self.studio, 'get', side_effect=AssertionError('imported history may not have image library')):
            self.studio.adopt(pid, scenes[0]['key'], image['id'])
        project = self.projects.get(pid)
        self.assertIn(first['asset_id'], project['story']['shots'][0]['bindings']['images'])
        self.assertNotIn(second['asset_id'], project['story']['shots'][0]['bindings']['images'])
        self.assertIn(second['asset_id'], project['assets'])

    def test_config_round_trip_preserves_image_settings(self):
        settings = self.config.get()
        settings['image_generation'] = {'managed_port': 8198, 'auto_download': False}
        self.config.save(settings)
        settings = self.config.get(); settings.pop('image_generation')
        self.config.save(settings)
        self.assertEqual(self.config.public()['image_generation']['managed_port'], 8198)
        self.assertFalse(self.config.public()['image_generation']['auto_download'])

    def test_old_image_is_not_busy_when_same_project_has_another_task(self):
        pid = self.project()
        old = self.completed(pid)
        current = self.studio.create({'prompt': 'new picture', 'optimize': False}, pid)
        self.db.enqueue(pid, 'image-generate', {'image_id': current['id']})
        self.assertTrue(self.studio.get(current['id'])['busy'])
        self.assertFalse(self.studio.get(old['id'])['busy'])
        self.assertTrue(self.studio.get(old['id'])['project_busy'])

    def test_locked_reference_target_is_rejected_before_generation(self):
        pid = self.project()
        story = self.projects.get(pid)['story']
        story['shots'][0]['locked'] = True
        self.projects.save_story(pid, story)
        with self.assertRaisesRegex(ValueError, '先解锁'):
            self.studio.reference_request(pid, 'character-hero')
        self.assertEqual(self.studio.listing(pid), [])

    def test_adoption_recovers_from_missing_book_without_duplicate_asset(self):
        pid = self.project()
        image = self.completed(pid, 'character-hero')
        first = self.studio.adopt(pid, 'character-hero', image['id'])
        before = self.projects.get(pid)['assets']
        write_json(self.projects.path(pid) / 'reference-images.json', {'items': {}})
        second = self.studio.adopt(pid, 'character-hero', image['id'])
        self.assertEqual(first['asset_id'], second['asset_id'])
        self.assertEqual(self.projects.get(pid)['assets'], before)

    def test_reference_history_survives_project_transfer_without_image_library(self):
        pid = self.project()
        image = self.completed(pid, 'character-hero')
        selected = self.studio.adopt(pid, 'character-hero', image['id'])
        transfer = Transfer(self.config, self.projects, Skills(self.root / 'transfer-skills'))
        archive = transfer.export([pid])
        imported = transfer.import_package(archive)['projects'][0]
        self.assertNotEqual(imported, pid)
        with patch.object(self.studio, 'get', side_effect=AssertionError('no external image library after migration')):
            adopted = self.studio.adopt(imported, 'character-hero', image['id'])
        self.assertEqual(adopted['asset_id'], selected['asset_id'])
        asset = self.projects.get(imported)['assets'][selected['asset_id']]
        self.assertTrue((self.projects.path(imported) / asset['file']).is_file())

    def test_fresh_machine_plan_includes_gpu_runtime_without_h3_models(self):
        unavailable = {'connected': False, 'missing_nodes': ['TextEncodeQwenImage21'], 'choices': {}, 'gpu': None, 'vram_mb': None}
        with patch.object(self.studio.environment, 'probe', return_value=unavailable), \
             patch('app.image_environment.hardware', return_value={'gpu': [{'name': 'test GPU', 'vram_mb': 16311}]}):
            plan = self.studio.environment.plan()
        self.assertTrue(plan['bootstrap_needed'])
        self.assertGreater(plan['runtime_download_bytes'], 0)
        self.assertEqual(len(plan['models']), 3)
        self.assertTrue(all('minimax' not in row['name'] for row in plan['models']))
        self.assertEqual(plan['variant'], 'turbo-int8')

    def test_remote_recommendation_uses_server_gpu_not_workbench_gpu(self):
        config = self.config.get()
        config['image_generation'] = {'engine': 'shared', 'comfy_url': 'https://gpu.example.test'}
        self.config.save(config)
        remote = {'connected': True, 'missing_nodes': [], 'choices': {}, 'gpu': {'name': 'server GPU'}, 'vram_mb': 48 * 1024}
        with patch.object(self.studio.environment, 'probe', return_value=remote), \
             patch('app.image_environment.hardware', side_effect=AssertionError('must not substitute local GPU')):
            plan = self.studio.environment.plan()
        self.assertEqual(plan['variant'], 'turbo-bf16')
        self.assertFalse(plan['local_download'])

    def test_image_api_queues_and_cancels_only_selected_image(self):
        from fastapi.testclient import TestClient
        from app import api
        from app.content import Content
        from app.jobs import Worker
        worker = Worker(self.db, self.config, self.projects, Content(self.config, Skills(), self.projects), self.assets)
        worker.images = self.studio
        with patch.object(api, 'worker', worker), patch.object(api, 'config', self.config), patch.object(api, 'db', self.db):
            client = TestClient(api.app, base_url='http://localhost')
            first = client.post('/api/images', json={'request': {'prompt': 'rain', 'optimize': False}}).json()
            second = client.post('/api/images', json={'request': {'prompt': 'sun', 'optimize': False}}).json()
            self.assertEqual(client.post('/api/images/' + first['id'] + '/stop').status_code, 200)
            jobs = {j['id']: j for j in self.db.jobs()}
            self.assertEqual(jobs[first['job_id']]['status'], 'paused')
            self.assertEqual(jobs[second['job_id']]['status'], 'queued')
            self.assertEqual(client.get('/api/images/' + first['id']).json()['status'], 'paused')
            client.close()


if __name__ == '__main__':
    unittest.main()
