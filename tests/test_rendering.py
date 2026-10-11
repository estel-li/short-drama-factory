import copy
import unittest

from app.rendering import semantic_signature


class RenderingTests(unittest.TestCase):
    def test_unused_model_changes_do_not_invalidate_other_mode(self):
        graph = {'1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'fl.safetensors'}}}
        models = {'fl': {'category': 'diffusion_models', 'name': 'fl.safetensors', 'sha256': 'fl-sha'},
                  'ref': {'category': 'diffusion_models', 'name': 'ref.safetensors', 'sha256': 'old-ref'}}
        initial = semantic_signature(graph, {}, [], models)
        models['ref']['sha256'] = 'new-ref'
        self.assertEqual(initial, semantic_signature(graph, {}, [], models))
        models['fl']['sha256'] = 'new-fl'
        self.assertNotEqual(initial, semantic_signature(graph, {}, [], models))

    def test_cache_follows_content_across_moves(self):
        graph = {'1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'model.safetensors'}},
                 '8': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': 42}},
                 '21': {'class_type': 'LoadImage', 'inputs': {'image': 'old-project/frame.png'}},
                 '16': {'class_type': 'SaveVideo', 'inputs': {'filename_prefix': 'old-project/shot'}}}
        bindings = {'images': [{'sha256': 'original-image'}]}
        version = {'model': {'sha256': 'original-model'}}
        original = semantic_signature(graph, bindings, [], version)
        moved = copy.deepcopy(graph)
        moved['21']['inputs']['image'] = 'new-project/frame.png'
        moved['16']['inputs']['filename_prefix'] = 'new-project/shot'
        self.assertEqual(original, semantic_signature(moved, bindings, [], version))
        self.assertNotEqual(original, semantic_signature(graph, {'images': [{'sha256': 'modified-image'}]}, [], version))
        self.assertNotEqual(original, semantic_signature(graph, bindings, [], {'model': {'sha256': 'modified-model'}}))
        moved['8']['inputs']['noise_seed'] = 43
        self.assertNotEqual(original, semantic_signature(moved, bindings, [], version))


if __name__ == '__main__':
    unittest.main()
