import unittest
from types import SimpleNamespace
import copy
import hashlib
from pathlib import Path
import tempfile
from unittest.mock import patch

from app.image_models import library_image_graph, model_catalog, model_spec, model_sampling
from app.image_schemas import ImageRequest
from app.image_schemas import ImageSettings
from app.image_studio import ImageStudio
from app.storage import digest
from app.config import ConfigStore
from app.storage import ROOT,read_json,write_json
from app.image_environment import ImageEnvironment
from app.downloads import Downloader


class ImageModelGraphTests(unittest.TestCase):
    def plan(self, model_id):
        spec = model_spec(model_id)
        return {'image_model': model_id, 'variant': 'auto', 'models': [dict(f, comfy_name=f['name']) for f in spec['files']]}

    def request(self, model_id, **changes):
        return ImageRequest(prompt='A woman opens a book in a quiet bookstore.', optimize=False,
                            seed=20261020, sampling=model_spec(model_id)['sampling'], **changes)

    def test_six_distinct_checkpoints_have_pinned_files(self):
        models = model_catalog()
        self.assertGreaterEqual(len(models), 6)
        primary_hashes = set()
        for model in models.values():
            self.assertEqual(len(model['revision']), 40)
            primary_hashes.add(model['files'][0]['sha256'])
            for f in model['files']:
                self.assertEqual(len(f['sha256']), 64)
                self.assertGreater(f['size'], 0)
                self.assertIn('/resolve/' + model['revision'] + '/', f['url'])
        self.assertEqual(len(primary_hashes), len(models))

    def test_native_graphs_use_actual_model_architecture_and_presets(self):
        for mid, spec in model_catalog().items():
            with self.subTest(model=mid):
                graph, w, h = library_image_graph(self.request(mid), 'A bookstore', self.plan(mid), 'test')
                self.assertEqual(graph['7']['inputs']['steps'], spec['sampling']['steps'])
                self.assertEqual(graph['7']['inputs']['cfg'], spec['sampling']['cfg'])
                self.assertEqual((w, h), (spec['resolution'], spec['resolution']))
                types = {n['class_type'] for n in graph.values()}
                self.assertNotIn('TextEncodeQwenImage21', types)
                self.assertEqual(graph['8']['inputs']['vae'], ['5', 0] if mid == 'z-image-turbo' else ['1', 2])
                if mid == 'z-image-turbo':
                    self.assertEqual(graph['2']['inputs']['type'], 'lumina2')
                    self.assertEqual(graph['10']['inputs']['shift'], 3.0)
                elif mid == 'flux-schnell':
                    self.assertIn('EmptySD3LatentImage', types)
                    self.assertEqual(graph['7']['inputs']['cfg'], 1)
                else:
                    self.assertIn('EmptyLatentImage', types)

    def test_img2img_encodes_original_and_preserves_aspect_ratio(self):
        mid = 'sdxl-base'
        req = self.request(mid, reference_images=['a' * 64], reference_mode='edit')
        req.sampling.denoise = 0.6
        graph, w, h = library_image_graph(req, req.prompt, self.plan(mid), 'test',
                                        [{'comfy_name':'image_studio/input.png', 'width':600, 'height':800}])
        self.assertLess(w, h)
        self.assertEqual(graph['7']['inputs']['latent_image'], ['15', 0])
        self.assertEqual(graph['15']['inputs']['pixels'], ['14', 0])
        self.assertEqual(graph['21']['inputs']['image'], 'image_studio/input.png')
        self.assertEqual(graph['7']['inputs']['denoise'], 0.6)

    def test_does_not_silently_ignore_unsupported_reference_or_transparency(self):
        mid = 'sdxl-base'
        for values in [{'transparent': True}, {'reference_images':['a'*64]},
                       {'reference_images':['a'*64,'b'*64], 'reference_mode':'edit'}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                library_image_graph(self.request(mid, **values), 'bookstore', self.plan(mid), 'test')

    def test_missing_model_and_missing_uploaded_original_fail_before_submission(self):
        with self.assertRaises(ValueError):
            model_spec('../../anything')
        mid = 'dreamshaper-8'
        with self.assertRaises(ValueError):
            library_image_graph(self.request(mid,reference_images=['a'*64],reference_mode='edit'),
                                'bookstore',self.plan(mid),'test')

    def test_switching_models_does_not_inherit_another_architectures_sampling(self):
        settings=ImageSettings(image_model='z-image-turbo',sampling={'steps':9,'cfg':1})
        studio=SimpleNamespace(environment=SimpleNamespace(settings=lambda:settings))
        qwen=ImageStudio.image_request(studio,{'prompt':'bookstore','image_model':'qwen-image-2.1'})
        self.assertIsNone(qwen.sampling.steps)
        sdxl=ImageStudio.image_request(studio,{'prompt':'bookstore','image_model':'sdxl-base'})
        self.assertEqual((sdxl.sampling.steps,sdxl.sampling.cfg),(28,7))
        inherited=ImageStudio.image_request(studio,{'prompt':'bookstore'})
        self.assertEqual(inherited.image_model,'z-image-turbo')
        self.assertEqual(inherited.sampling.steps,9)

    def test_project_model_changes_invalidate_reference_without_invalidating_legacy_qwen(self):
        preference=SimpleNamespace(image_model='qwen-image-2.1')
        projects=SimpleNamespace(path=lambda pid:pid,options=lambda path:SimpleNamespace(style='warm',reference_images=preference))
        studio=SimpleNamespace(projects=projects)
        candidate={'description':'bookstore'}
        qwen=ImageStudio.reference_signature(studio,'test',candidate)
        self.assertEqual(qwen,digest(['bookstore','warm']))
        preference.image_model='sdxl-base';sdxl=ImageStudio.reference_signature(studio,'test',candidate)
        preference.image_model='dreamshaper-8';dream=ImageStudio.reference_signature(studio,'test',candidate)
        self.assertEqual(len({qwen,sdxl,dream}),3)

    def test_auto_engine_reuses_local_library_when_video_service_has_no_image_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);write_json(root/'config.default.json',read_json(ROOT/'config.default.json'))
            environment=ImageEnvironment(ConfigStore(root))
            spec=copy.deepcopy(model_spec('sdxl-base'));spec['files'][0].update(size=4,sha256=hashlib.sha256(b'sdxl').hexdigest())
            model=root/'models/image-library/checkpoints'/spec['files'][0]['name']
            model.parent.mkdir(parents=True);model.write_bytes(b'sdxl')
            Downloader().verified(model,4,spec['files'][0]['sha256'])
            shared={'connected':True,'missing_nodes':[],'node_types':['CLIPTextEncode','KSampler','VAEDecode','SaveImage','VAEEncode','ImageScale','LoadImage','CheckpointLoaderSimple','EmptyLatentImage'],
                    'choices':{},'gpu':{'vram_total':16*1024**3},'vram_mb':16384,'sampling_support':None}
            offline={**shared,'connected':False,'node_types':[],'gpu':None,'vram_mb':None}
            with patch.object(environment,'probe',side_effect=lambda url:shared if url.endswith('8188') else offline),patch('app.image_library.model_spec',return_value=spec),patch('app.image_library.hardware',return_value={'gpu':[{'vram_mb':16384}]}):
                plan=environment.plan(image_model='sdxl-base')
            self.assertEqual(plan['engine'],'managed')
            self.assertEqual(plan['models_download_bytes'],0)
            self.assertEqual(plan['models'][0]['action'],'verified')


if __name__ == '__main__':
    unittest.main()
