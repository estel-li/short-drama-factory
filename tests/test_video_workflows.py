import copy
import unittest
from unittest.mock import patch

import pipeline
from app.schemas import Quality
from app.video_workflows import BUILTIN_PROFILES, subgraph, replace_link


class VideoWorkflowTests(unittest.TestCase):
    def graph(self, workflow, reference=False):
        config = copy.deepcopy(pipeline.CONFIG)
        config['profiles'].update(copy.deepcopy(BUILTIN_PROFILES))
        config['attention'] = 'comfy kitchen attention'
        shot = {'id':1,'duration':4,'prompt':'A woman opens a book in a warm quiet bookstore.'}
        with patch.dict(pipeline.CONFIG, config, clear=True):
            return pipeline.graph_for(shot,'test',workflow,'16:9',references=[{'name':'hero','image':'hero.png'}] if reference else [])

    def test_pdd_uses_trained_sigmas_and_matching_trunk_without_turbo_stack(self):
        for reference in (False,True):
            graph=self.graph('pdd-8',reference)
            self.assertEqual(graph['5']['class_type'],'MiniMaxH3PDDAccApply')
            self.assertIn('ref2va' if reference else 'fl2va',graph['5']['inputs']['pdd_file'])
            self.assertEqual(graph['18']['inputs']['shift_video'],12)
            self.assertEqual(graph['11']['class_type'],'MiniMaxH3PDDAccScheduler')
            self.assertEqual(graph['10']['inputs']['sampler_name'],'euler')
            self.assertNotIn('LoraLoaderModelOnly',{n['class_type'] for n in graph.values()})

    def test_lightx2v_8_selects_its_actual_adapter_and_rejects_ref_mode(self):
        graph=self.graph('lightx2v-8')
        self.assertIn('8step_v1.0_768p',graph['5']['inputs']['lora_name'])
        self.assertEqual(graph['11']['inputs']['steps'],8)
        with self.assertRaisesRegex(ValueError,'Ref2VA'):
            self.graph('lightx2v-8',True)

    def test_two_pass_graph_retains_original_audio_and_cache_all_dependencies(self):
        graph=self.graph('pdd-upscale')
        self.assertEqual(graph['12']['class_type'],'DramaPreserveLatentAudio')
        self.assertEqual(graph['12']['inputs']['original'],['19',0])
        self.assertEqual(graph['34']['inputs']['latent_image'],['36',0])
        self.assertEqual(graph['35']['class_type'],'MinimaxH3LatentUpscaler3D')
        self.assertEqual(graph['35']['inputs']['mode.scale'],1.25)
        self.assertEqual(graph['36']['inputs']['audio_latent'],['20',1])
        encoding=subgraph(graph,['7'])
        render={k:copy.deepcopy(v) for k,v in graph.items() if k not in encoding or k in ('3','4')}
        render['7']={'class_type':'DramaLoadConditioning','inputs':{'filename':'test.safetensors'}}
        render['17']={'class_type':'EmptyMiniMaxH3LatentAV','inputs':{'width':832,'height':480,'length':107}}
        replace_link(render,['7',1],['17',0])
        self.assertEqual(render['19']['inputs']['latent_image'],['17',0])
        sampling=subgraph(render,['12'])
        self.assertTrue({'19','20','33','34','35','36','12'}<=set(sampling))
        self.assertNotIn('2',sampling)
        self.assertNotIn('3',sampling)
        decoding=subgraph(render,['16'],stop={'12'})
        self.assertNotIn('34',decoding)
        self.assertNotIn('19',decoding)
        with patch.dict(pipeline.CONFIG,{'profiles':BUILTIN_PROFILES}):
            self.assertEqual(pipeline.output_canvas(BUILTIN_PROFILES['pdd-upscale'],'16:9'),(1024,608))

    def test_invalid_training_grid_or_path_fails_before_gpu(self):
        for change in ({'steps':7},{'pdd_fl':'../outside.safetensors'},{'upscale_by':float('inf')}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                Quality.model_validate({**BUILTIN_PROFILES['pdd-upscale'],**change})

    def test_dependency_traversal_rejects_cycles_and_missing_inputs(self):
        for graph in ({'1':{'inputs':{'x':['1',0]}}},{'1':{'inputs':{'x':['2',0]}}}):
            with self.assertRaises(ValueError):subgraph(graph,['1'])


if __name__=='__main__':unittest.main()
