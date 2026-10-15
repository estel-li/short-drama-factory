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

    def test_optimized_image_continues_same_record_and_job_with_user_edits(self):
        image = self.studio.create({'prompt': 'old prompt'})
        jid = self.db.enqueue(image['owner'], 'image-optimize', {'image_id': image['id']})
        self.studio.update(image['id'], job_id=jid)
        self.db.claim()
        self.studio.update(image['id'], status='ready', optimized_prompt='machine prompt')
        self.db.update(jid, 'done')
        result = self.studio.start(image['id'], self.db.enqueue,
                                   request={'optimized_prompt': 'edited prompt', 'seed': None})
        self.assertEqual(result, {'id': image['id'], 'job_id': jid})
        self.assertEqual(len(self.db.jobs()), 1)
        self.assertEqual(self.db.jobs()[0]['kind'], 'image-generate')
        with patch('app.image_studio.LLMClient', side_effect=AssertionError('must not optimize again')):
            self.assertEqual(self.studio.optimize(image['id'], lambda *a, **k: None, lambda: False), 'edited prompt')
        self.assertEqual(self.studio.get(image['id'])['request']['seed'], image['request']['seed'])
        with self.assertRaisesRegex(ValueError, '正在处理'):
            self.studio.start(image['id'], self.db.enqueue)
        self.db.update(jid, 'done')
        self.studio.start(image['id'], self.db.enqueue, request={'prompt': 'new original', 'optimize': False, 'optimized_prompt': ''})
        self.assertEqual(self.studio.optimize(image['id'], lambda *a, **k: None, lambda: False), 'new original')

    def test_submitted_image_cannot_change_request_on_resume(self):
        image = self.studio.create({'prompt': 'original', 'optimize': False})
        self.studio.update(image['id'], prompt_id='already-submitted', status='paused')
        with self.assertRaisesRegex(ValueError, '不能修改参数'):
            self.studio.start(image['id'], self.db.enqueue, request={'prompt': 'changed'})
        self.assertEqual(self.studio.get(image['id'])['request']['prompt'], 'original')
        self.assertEqual(self.db.jobs(), [])

    def test_continued_image_joins_queue_tail_without_changing_job_id(self):
        from unittest.mock import patch
        with patch('app.database.now', return_value='2026-10-15 21:00:00'):
            image = self.studio.create({'prompt': 'a room'})
            jid = self.db.enqueue(image['owner'], 'image-optimize', {'image_id': image['id']})
            self.db.update(jid, 'done')
            other = self.studio.create({'prompt': 'another room'})
            next_job = self.db.enqueue(other['owner'], 'image-generate', {'image_id': other['id']})
            self.assertEqual(self.db.requeue_image(jid, image['owner'], image['id'], 'image-generate'), jid)
            self.assertEqual(self.db.claim()['id'], next_job)
            self.assertEqual(self.db.claim()['id'], jid)

    def test_confirmed_plan_downloads_and_reports_actual_progress(self):
        import hashlib
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        data = b'controlled local download' * 1000
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        target = self.root / 'models/test.safetensors'
        pending = {**self.plan, 'ready': False, 'selection_errors': [], 'requires_confirmation': True, 'confirmation_token': 'explicit-plan',
                   'engine': 'shared', 'local_download': True, 'missing_nodes': [], 'free_disk_bytes': 10**10,
                   'models_download_bytes': len(data), 'selection': {},
                   'models': [{'action': 'download', 'name': target.name, 'target': str(target), 'size': len(data),
                               'sha256': hashlib.sha256(data).hexdigest(), 'url': f'http://127.0.0.1:{server.server_port}/model'}]}
        events = []
        with patch.object(self.studio.environment, 'plan', side_effect=[pending, self.plan]):
            result = self.studio.environment.prepare('auto', lambda message, **detail: events.append(detail), lambda: False, confirmation='explicit-plan')
        self.assertTrue(result['ready'])
        self.assertEqual(target.read_bytes(), data)
        self.assertTrue(any(e.get('progress', {}).get('bytes') == len(data) for e in events))

    def test_environment_pause_keeps_file_and_byte_progress(self):
        from app.jobs import Worker
        from app import api
        worker = Worker(self.db, self.config, self.projects, None, self.assets)
        jid = self.db.enqueue('__image_environment', 'image-prepare', {'variant': 'auto'})
        job = self.db.claim()
        path = self.root / 'data/image-environment-progress.json'
        progress = {'file': 'model.safetensors', 'bytes': 40, 'total': 100}
        write_json(path, {'job_id': jid, 'status': 'running', 'progress': progress})
        with patch.object(api, 'worker', worker), patch.object(api, 'config', self.config):
            api.image_prepare_stop()
        worker.image_failure(job, 'paused', 'paused')
        saved = read_json(path)
        self.assertEqual(saved['status'], 'paused')
        self.assertEqual(saved['job_id'], jid)
        self.assertEqual(saved['progress'], progress)

    def test_delete_removes_gallery_record_but_preserves_adopted_project_asset(self):
        pid = self.project()
        image = self.completed(pid, 'character-hero')
        adopted = self.studio.adopt(pid, 'character-hero', image['id'])
        other = self.completed()
        asset = self.projects.get(pid)['assets'][adopted['asset_id']]
        self.studio.delete(image['id'])
        self.assertFalse((self.studio.root / image['id']).exists())
        self.assertTrue((self.projects.path(pid) / asset['file']).exists())
        self.assertTrue(self.studio.get(other['id'])['file_available'])
        self.assertNotIn(image['id'], [i['id'] for i in self.studio.listing()])
        self.studio.adopt(pid, 'character-hero', image['id'])
        self.assertEqual(self.projects.get(pid)['story']['shots'][0]['bindings']['images'], [adopted['asset_id']])

    def test_delete_refuses_active_worker_or_owned_comfy_task(self):
        image = self.completed()
        jid = self.db.enqueue(image['owner'], 'image-generate', {'image_id': image['id']})
        with self.assertRaisesRegex(ValueError, '正在处理'):
            self.studio.delete(image['id'])
        self.db.update(jid, 'paused')
        self.studio.update(image['id'], prompt_id='owned', comfy_url='http://localhost:8190', submission='submitted')
        with patch.object(self.studio, 'request', return_value={'queue_running': [[0, 'owned']]}):
            with self.assertRaisesRegex(ValueError, 'ComfyUI 队列'):
                self.studio.delete(image['id'])
        self.assertTrue(self.studio.path(image['id']).is_dir())

    def test_missing_models_require_confirmation_even_with_legacy_auto_download(self):
        from app.image_environment import DownloadConfirmationRequired
        config = self.config.get();config['image_generation'] = {'engine': 'managed', 'auto_download': True};self.config.save(config)
        unavailable = {'connected': False, 'missing_nodes': ['TextEncodeQwenImage21'], 'choices': {}, 'gpu': None, 'vram_mb': None}
        with patch.object(self.studio.environment, 'probe', return_value=unavailable), \
             patch('app.image_environment.hardware', return_value={'gpu': [{'name': 'test', 'vram_mb': 16311}]}), \
             patch('app.image_environment.Downloader') as downloader:
            plan = self.studio.environment.plan()
            self.assertTrue(plan['requires_confirmation'])
            with self.assertRaises(DownloadConfirmationRequired):
                self.studio.environment.prepare('auto', lambda *a, **k: None, lambda: False)
            with self.assertRaises(DownloadConfirmationRequired):
                self.studio.environment.prepare('quality-int8', lambda *a, **k: None, lambda: False, confirmation=plan['confirmation_token'])
            downloader.assert_not_called()

    def test_custom_model_catalog_round_trip_and_request_graph(self):
        config = self.config.get();config['image_generation'] = {'engine': 'shared', 'comfy_url': 'http://localhost:8190', 'models_dir': str(self.root/'models')};self.config.save(config)
        choices = {c: ['custom/' + c + '.safetensors'] for c in ('diffusion_models', 'text_encoders', 'vae')}
        remote = {'connected': True, 'missing_nodes': [], 'choices': choices, 'gpu': {'name': 'GPU'}, 'vram_mb': 16311}
        models = {c: names[0] for c, names in choices.items()}
        local = self.root/'models/diffusion_models/another.safetensors';local.parent.mkdir(parents=True);local.write_bytes(b'local model')
        with patch.object(self.studio.environment, 'probe', return_value=remote):
            plan = self.studio.environment.plan('turbo-int8', models)
            self.assertTrue(plan['ready'])
            self.assertEqual(plan['download_bytes'], 0)
            self.assertFalse(plan['requires_confirmation'])
            self.assertIn('another.safetensors', [i['name'] for i in plan['available_models']['diffusion_models']])
            graph, _, _ = image_graph(ImageRequest(prompt='p', seed=1, models=models), 'p', plan, self.studio.environment.manifest, 'test')
            self.assertEqual(graph['1']['inputs']['unet_name'], models['diffusion_models'])
            self.assertEqual(graph['2']['inputs']['clip_name'], models['text_encoders'])
            self.assertEqual(graph['5']['inputs']['vae_name'], models['vae'])
            missing = self.studio.environment.plan(models={**models, 'vae': 'missing.safetensors'})
            self.assertFalse(missing['ready'])
            self.assertTrue(missing['selection_errors'])
        with self.assertRaises(ValueError):
            ImageRequest(prompt='p', models={'vae': '../outside.safetensors'})


if __name__ == '__main__':
    unittest.main()
