import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from PIL import Image
from fastapi.testclient import TestClient

from app.assets import Assets
from app.config import ConfigStore
from app.database import Database
from app.image_schemas import ImageRequest
from app.image_studio import ImageStudio, image_graph
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json
from app.transfer import Transfer


class ImageInputTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        config = self.config.get(); config['projects_dir'] = str(self.root / 'projects'); self.config.save(config)
        self.db = Database(self.root / 'data/test.sqlite3')
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.studio = ImageStudio(self.config, self.db, self.projects, self.assets, Skills())
        self.plan = {'ready': True, 'comfy_url': 'http://image.test', 'variant': 'turbo-int8',
                     'recommendation': {'resolution': 512}, 'reference_support': True,
                     'models': [{'category': c, 'name': c, 'comfy_name': c} for c in ('diffusion_models', 'text_encoders', 'vae')]}

    @staticmethod
    def png(color='blue', size=(64, 96)):
        output = io.BytesIO(); Image.new('RGB', size, color).save(output, format='PNG'); return output.getvalue()

    def input(self, color='blue'):
        return self.studio.inputs.upload(base64.b64encode(self.png(color)).decode(), '参考图.png')

    def project(self):
        return self.projects.create('test', {'input_mode': 'storyboard'}, {
            'title': 'test', 'characters': [{'id': 'hero', 'name': '小雨', 'visual_description': '黄衣女孩'}],
            'shots': [{'characters': ['hero'], 'scene': '小屋', 'prompt': 'original'}]}).name

    def test_upload_validates_image_and_normalizes_exif_with_stable_content_ids(self):
        photo = Image.new('RGB', (30, 60), 'red'); exif = Image.Exif(); exif[274] = 6
        exif[270] = 'private metadata'
        output = io.BytesIO(); photo.save(output, format='JPEG', exif=exif)
        result = self.studio.inputs.upload(base64.b64encode(output.getvalue()).decode(), '../../portrait.jpg')
        self.assertEqual((result['width'], result['height']), (60, 30))
        self.assertEqual(self.studio.inputs.add(output.getvalue())['id'], result['id'])
        with Image.open(self.studio.inputs.file(result['id'])) as saved:
            self.assertEqual(saved.format, 'PNG'); self.assertFalse(saved.getexif())
        self.assertNotIn(b'private metadata', self.studio.inputs.file(result['id']).read_bytes())
        self.studio.inputs.file(result['id']).write_bytes(b'corrupted cache')
        self.studio.inputs.add(output.getvalue())
        with Image.open(self.studio.inputs.file(result['id'])) as repaired:
            self.assertEqual(repaired.size, (60, 30))
        for data in ('bad base64?', base64.b64encode(b'not an image').decode(), 'A' * 11_000_001):
            with self.assertRaises(ValueError): self.studio.inputs.upload(data)
        with self.assertRaises(ValueError): self.studio.inputs.get('../outside')

    def test_native_reference_and_edit_graphs_use_images_and_keep_sampler_paths(self):
        inputs = [self.input('blue'), self.input('red')]
        uploaded = [{**item, 'comfy_name': 'factory/' + item['id'] + '.png'} for item in inputs]
        for variant in ('turbo-int8', 'quality-int8'):
            for mode in ('reference', 'edit'):
                request = ImageRequest(prompt='修改 <image1>，服装参考 <image2>', reference_images=[i['id'] for i in inputs],
                                       reference_mode=mode, resolution='512', ratio='16:9', seed=1)
                graph, width, height = image_graph(request, request.prompt, {**self.plan, 'variant': variant}, self.studio.environment.manifest, 'test', uploaded)
                self.assertEqual(graph['3']['inputs']['images.image_1'], ['21', 0])
                self.assertEqual(graph['3']['inputs']['images.image_2'], ['22', 0])
                self.assertEqual(graph['3']['inputs']['vae'], ['5', 0])
                self.assertEqual(graph['7']['inputs']['latent_image'], ['3', 2] if mode == 'edit' else ['4', 0])
                self.assertEqual(width < height, mode == 'edit')
        for raw in ({'reference_images': [inputs[0]['id']] * 2}, {'reference_images': ['bad']},
                    {'reference_images': [], 'reference_mode': 'edit'}, {'reference_images': [f'{i:064x}' for i in range(11)]}):
            with self.assertRaises(ValueError): ImageRequest(prompt='p', **raw)

    def test_task_keeps_independent_snapshot_and_detects_corruption_before_submit(self):
        item = self.input()
        task = self.studio.create({'prompt': 'p', 'optimize': False, 'reference_images': [item['id']]})
        reference = self.studio.get(task['id'])['reference_inputs'][0]
        snapshot = self.studio.path(task['id']) / reference['file']
        original = snapshot.read_bytes()
        self.studio.inputs.file(item['id']).write_bytes(b'modified original cache')
        self.assertEqual(snapshot.read_bytes(), original)
        with patch('app.image_studio.httpx.Client') as client:
            snapshot.write_bytes(b'changed task snapshot')
            with self.assertRaisesRegex(ValueError, '快照'):
                self.studio.upload_references(self.studio.get(task['id']), 'http://image.test', lambda *a, **k: None, lambda: False)
            client.assert_not_called()

    def test_upload_failure_retries_same_image_then_resume_does_not_upload_or_submit_again(self):
        item = self.input()
        task = self.studio.create({'prompt': 'edit <image1>', 'optimize': False, 'reference_images': [item['id']], 'reference_mode': 'edit'})
        uploads, requests = [], []
        def transport(request):
            uploads.append(request.read())
            if len(uploads) == 1: return httpx.Response(503)
            return httpx.Response(200, json={'name': item['id'] + '.png', 'subfolder': 'refs', 'type': 'input'})
        real_client = httpx.Client
        def request(url, path, body=None):
            requests.append((path, body))
            if path == '/queue': return {'queue_running': [], 'queue_pending': []}
            if path == '/prompt': return {'prompt_id': body['prompt_id']}
            if path.startswith('/history/'):
                return {path.rsplit('/', 1)[1]: {'status': {'completed': True}, 'outputs': {'9': {'images': [{'filename': 'result.png'}]}}}}
            raise AssertionError(path)
        with patch.object(self.studio.environment, 'plan', return_value=self.plan), \
             patch.object(self.studio, 'release_idle'), patch.object(self.studio, 'request', side_effect=request), \
             patch('app.image_studio.httpx.Client', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(transport), **kw)), \
             patch('app.image_studio.download_file', side_effect=lambda item, target, *a: target.write_bytes(self.png())):
            with self.assertRaisesRegex(RuntimeError, '上传失败'):
                self.studio.generate(task['id'], lambda *a, **k: None, lambda: False)
            self.assertFalse(any(p == '/prompt' for p, _ in requests))
            self.assertNotIn('prompt_id', self.studio.get(task['id']))
            self.assertEqual(self.studio.generate(task['id'], lambda *a, **k: None, lambda: False)['status'], 'complete')
            self.studio.generate(task['id'], lambda *a, **k: None, lambda: False)
        self.assertEqual(len(uploads), 2)
        self.assertIn(b'Content-Disposition: form-data; name="image"', uploads[1])
        self.assertEqual(sum(p == '/prompt' for p, _ in requests), 1)
        graph = next(body['prompt'] for p, body in requests if p == '/prompt')
        self.assertEqual(graph['21']['inputs']['image'], 'refs/' + item['id'] + '.png')

    def test_character_sources_persist_in_project_transfer_and_do_not_bind_as_final_identity(self):
        pid = self.project()
        asset = self.assets.add_image(pid, base64.b64encode(self.png()).decode(), '原始角色照片')
        self.studio.set_reference_sources(pid, 'character-hero', {'asset_ids': [asset['id']]})
        request = self.studio.reference_request(pid, 'character-hero')
        self.assertEqual(len(request['reference_images']), 1)
        self.assertEqual(self.projects.get(pid)['story']['shots'][0].get('bindings', {}).get('images', []), [])
        transfer = Transfer(self.config, self.projects, Skills(self.root / 'transfer-skills'))
        imported = transfer.import_package(transfer.export([pid]))['projects'][0]
        self.assertEqual(self.studio.reference_request(imported, 'character-hero')['reference_images'], request['reference_images'])
        self.assertEqual(self.studio.candidates(imported)[0]['source_assets'], [asset['id']])
        with self.assertRaises(ValueError): self.studio.set_reference_sources(pid, 'character-hero', {'asset_ids': ['missing']})
        story = self.projects.get(pid)['story']; story['shots'][0]['locked'] = True; self.projects.save_story(pid, story)
        with self.assertRaisesRegex(ValueError, '解锁'):
            self.studio.set_reference_sources(pid, 'character-hero', {'asset_ids': []})

    def test_new_references_invalidate_optimized_prompt_on_same_task(self):
        first, second = self.input(), self.input('red')
        task = self.studio.create({'prompt': 'p', 'reference_images': [first['id']]})
        self.studio.update(task['id'], status='ready', optimized_prompt='old optimized')
        result = self.studio.start(task['id'], self.db.enqueue, request={'reference_images': [second['id']]})
        self.assertEqual(result['id'], task['id'])
        current = self.studio.get(task['id'])
        self.assertEqual(current['optimized_prompt'], '')
        self.assertEqual(current['reference_inputs'][0]['id'], second['id'])

    def test_batch_uses_custom_character_source_and_only_regenerates_when_source_changes(self):
        pid = self.project()
        first = self.assets.add_image(pid, base64.b64encode(self.png()).decode(), '角色一', 'hero')
        second = self.assets.add_image(pid, base64.b64encode(self.png('red')).decode(), '角色二')
        self.studio.set_reference_sources(pid, 'character-hero', {'asset_ids': [first['id']]})
        generated = []
        def generate(iid, *args):
            task = self.studio.get(iid); generated.append(task)
            (self.studio.path(iid) / 'image.png').write_bytes(self.png('yellow'))
            return self.studio.update(iid, file='image.png', status='complete')
        config = self.projects.get(pid)['settings']; config['reference_images']['scenes'] = False
        self.projects.save_options(pid, config)
        with patch.object(self.studio, 'generate', side_effect=generate):
            self.studio.ensure_references(pid, lambda *a, **k: None, lambda: False)
            self.assertEqual(len(generated), 1)
            self.assertEqual(len(generated[0]['reference_inputs']), 1)
            self.studio.ensure_references(pid, lambda *a, **k: None, lambda: False)
            self.assertEqual(len(generated), 1)
            self.studio.set_reference_sources(pid, 'character-hero', {'asset_ids': [second['id']]})
            self.studio.ensure_references(pid, lambda *a, **k: None, lambda: False)
            self.assertEqual(len(generated), 2)
        self.assertNotEqual(generated[0]['reference_inputs'][0]['id'], generated[1]['reference_inputs'][0]['id'])

    def test_image_api_upload_snapshot_and_gallery_reuse_survive_gallery_deletion(self):
        from app import api
        from app.jobs import Worker
        worker = Worker(self.db, self.config, self.projects, None, self.assets)
        with patch.object(api, 'worker', worker), patch.object(api, 'config', self.config), patch.object(api, 'db', self.db):
            client = TestClient(api.app, base_url='http://localhost')
            item = client.post('/api/image-inputs', json={'data': base64.b64encode(self.png()).decode(), 'name': 'ref.png'}).json()
            self.assertEqual(client.get(item['url']).status_code, 200)
            self.assertEqual(client.get('/api/image-inputs/' + item['id']).json()['width'], 64)
            self.assertEqual(client.post('/api/image-inputs', json={'data': 'bad'}).status_code, 400)
            task = worker.images.create({'prompt': 'p', 'reference_images': [item['id']]})
            self.assertEqual(client.get(f'/api/images/{task["id"]}/references/1').status_code, 200)
            self.assertEqual(client.get(f'/api/images/{task["id"]}/references/2').status_code, 400)
            (worker.images.path(task['id']) / 'image.png').write_bytes(self.png('red'))
            worker.images.update(task['id'], file='image.png', status='complete')
            reused = client.post(f'/api/images/{task["id"]}/use-as-reference', json={}).json()
            self.assertEqual(client.post(f'/api/images/{task["id"]}/delete', json={}).status_code, 200)
            self.assertEqual(client.get(reused['url']).status_code, 200)
            client.close()


if __name__ == '__main__': unittest.main()
