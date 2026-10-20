import copy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pipeline
from app.h3_advanced import PROFILES, RECIPES, CONTROL_MODEL
from app.schemas import Quality
from app.video_workflows import BUILTIN_PROFILES, subgraph, replace_link
from app.rendering import used_models
from app.assets import Assets
from app.storage import write_json


class AdvancedH3Tests(unittest.TestCase):
    def graph(self, workflow, **changes):
        config=copy.deepcopy(pipeline.CONFIG);config['profiles'].update(copy.deepcopy(BUILTIN_PROFILES))
        config['profiles'][workflow].update(changes)
        shot={'id':1,'duration':4,'prompt':'A woman opens a book in a warm quiet bookstore.','compiled_mode':'T2VA'}
        bindings={slot:{'id':slot,'comfy_file':slot+'.mp4' if slot=='source_video' else slot+'.wav' if slot=='source_audio' else slot+'.png'} for slot in RECIPES[workflow]['slots']}
        with patch.dict(pipeline.CONFIG,config,clear=True):
            return pipeline.graph_for(shot,'advanced-test',workflow,'16:9',bindings=bindings)

    def test_five_media_workflows_have_distinct_required_inputs_and_native_schedules(self):
        self.assertEqual(len(PROFILES),5)
        for workflow,profile in PROFILES.items():
            self.assertEqual(Quality.model_validate(profile).workflow,workflow)
            graph=self.graph(workflow)
            self.assertEqual(graph['11']['inputs']['steps'],12)
            self.assertNotIn('LoraLoaderModelOnly',{n['class_type'] for n in graph.values()})
            subgraph(graph,['16'])  # every output dependency must resolve

    def test_audio_drive_caches_locked_latent_and_muxes_source_audio(self):
        graph=self.graph('h3-audio-drive')
        self.assertEqual(graph['7']['class_type'],'DramaH3StageInputs')
        self.assertEqual(graph['7']['inputs']['latent'],['163',0])
        self.assertEqual(graph['163']['class_type'],'DramaH3AudioDrive')
        self.assertEqual(graph['15']['inputs']['audio'],['191',0])
        encoding=subgraph(graph,['7'])
        self.assertIn('LoadAudio',{n['class_type'] for n in encoding.values()})
        rendered={k:copy.deepcopy(v) for k,v in graph.items() if k not in encoding or k in ('3','4')}
        rendered['7']={'class_type':'DramaLoadConditioning','inputs':{'filename':'conditioning.safetensors'}}
        rendered['17']={'class_type':'DramaLoadLatent','inputs':{'filename':'source.safetensors'}}
        replace_link(rendered,['7',1],['17',0])
        sampling=subgraph(rendered,['12'])
        self.assertNotIn('EmptyMiniMaxH3LatentAV',{n['class_type'] for n in sampling.values()})
        decoding=subgraph(rendered,['16'],stop={'12'})
        self.assertIn('LoadAudio',{n['class_type'] for n in decoding.values()})
        self.assertNotIn('VAEDecodeAudio',{n['class_type'] for n in decoding.values()})

    def test_foley_preserves_source_pixels_instead_of_decoding_video_latent(self):
        graph=self.graph('h3-foley')
        self.assertEqual(graph['163']['class_type'],'DramaH3FoleyLatent')
        decoding=subgraph(graph,['16'],stop={'12'})
        self.assertNotIn('VAEDecodeTiled',{n['class_type'] for n in decoding.values()})
        self.assertIn('VAEDecodeAudio',{n['class_type'] for n in decoding.values()})
        self.assertEqual(graph['15']['inputs']['images'],['192',0])

    def test_middle_guide_position_and_continuation_output_length_are_explicit(self):
        guide=self.graph('h3-keyframe-guide',guide_position=0.25)
        self.assertEqual(guide['161']['inputs']['frame_idx'],26)
        for context in (5,22,39,56):
            graph=self.graph('h3-motion-context',context_frames=context)
            generated=graph['7']['inputs']['length']
            self.assertEqual(generated%17,5)
            self.assertGreaterEqual(generated-context,107)
            self.assertEqual(graph['191']['inputs']['frames'],107)
            self.assertEqual(graph['190']['inputs']['trim_frames'],context)

    def test_canny_patch_is_in_guider_path_and_fingerprinted(self):
        graph=self.graph('h3-canny-control',control_strength=0.6)
        self.assertEqual(graph['9']['inputs']['model'],['165',0])
        self.assertEqual(graph['165']['inputs']['strength'],0.6)
        self.assertEqual(graph['164']['inputs']['name'],CONTROL_MODEL)
        versions={'control':{'name':CONTROL_MODEL,'category':'model_patches','sha256':'a'*64}}
        self.assertTrue(used_models(graph,versions))

    def test_invalid_source_or_unsafe_schedule_fails_before_gpu(self):
        from app.h3_advanced import validate_inputs
        for workflow in RECIPES:
            with self.assertRaises(ValueError):validate_inputs(workflow,{}, {},'T2VA')
        with self.assertRaisesRegex(ValueError,'首尾帧'):
            validate_inputs('h3-motion-context',{}, {'source_video':{'id':'source'},'last_frame':{'id':'end'}},'L2VA')
        for change in ({'turbo':True},{'denoise':0.5},{'context_frames':20},
                       {'canny_low':0.8,'canny_high':0.2},{'control_start':0.9,'control_end':0.5}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                Quality.model_validate({**PROFILES['h3-canny-control'],**change})

    def test_source_bindings_enforce_types_and_do_not_hide_character_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'voice.wav').write_bytes(b'audio');(root/'face.png').write_bytes(b'face')
            write_json(root/'assets.json',{'voice':{'id':'voice','type':'audio','name':'voice','file':'voice.wav','sha256':'a'},
                'face':{'id':'face','type':'image','name':'face','file':'face.png','sha256':'b','character':'hero'}})
            assets=Assets(None,None)
            result=assets.resolve(root,{'bindings':{'source_audio':'voice'},'characters':['hero']},{})
            self.assertEqual(result['source_audio']['id'],'voice')
            self.assertEqual(result['images'][0]['id'],'face')
            with self.assertRaisesRegex(ValueError,'类型'):
                assets.resolve(root,{'bindings':{'source_video':'voice'}},{})

    def test_manual_modes_and_bound_keyframes_are_used_before_compilation_metadata_exists(self):
        config=copy.deepcopy(pipeline.CONFIG);config['profiles'].update(copy.deepcopy(BUILTIN_PROFILES))
        shot={'id':1,'duration':4,'prompt':'A reader opens a book in a quiet bookstore.'}
        with patch.dict(pipeline.CONFIG,config,clear=True):
            graph=pipeline.graph_for(shot,'manual','h3-audio-drive','16:9',bindings={
                'source_audio':{'comfy_file':'voice.wav'},'first_frame':{'comfy_file':'first.png'}})
            self.assertIn('first_frame',graph['169']['inputs'])
            graph=pipeline.graph_for({**shot,'mode':'Ref2VA'},'manual','pdd-8','16:9',
                bindings={'images':[{'comfy_file':'face.png','name':'reader'}]})
            self.assertEqual(graph['7']['class_type'],'MiniMaxH3ReferenceToVideo')
            self.assertIn('ref2va',graph['5']['inputs']['pdd_file'])

    def test_source_preview_is_never_selected_as_generated_video(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=pipeline.Runner(Path(folder));runner.state.update(shots={'1':{}},current_shot=1)
            source={'filename':'source.mp4','type':'input'};generated={'filename':'generated.mp4','type':'output'}
            history={'status':{'completed':True},'outputs':{'190':{'images':[source]},'16':{'images':[generated]}}}
            with patch('pipeline.api',return_value={'saved':history}):
                self.assertEqual(runner.wait('saved'),generated)
            history['outputs'].pop('16')
            with patch('pipeline.api',return_value={'saved':history}),self.assertRaisesRegex(RuntimeError,'未找到视频'):
                runner.wait('saved')

    def test_ref_audio_video_and_advanced_recipe_keep_disjoint_dependencies(self):
        config = copy.deepcopy(pipeline.CONFIG)
        config['profiles'].update(copy.deepcopy(BUILTIN_PROFILES))
        for workflow in ('h3-audio-drive', 'h3-keyframe-guide', 'h3-motion-context'):
            bindings = {'images': [{'comfy_file': 'face.png', 'name': 'reader'}],
                'videos': [{'comfy_file': 'reference.mp4', 'include_audio': True}],
                'audios': [{'comfy_file': 'reference.wav'}],
                **{slot: {'comfy_file': slot + '.mp4'} for slot in RECIPES[workflow]['slots']}}
            with self.subTest(workflow=workflow), patch.dict(pipeline.CONFIG, config, clear=True):
                graph = pipeline.graph_for({'id': 1, 'duration': 4, 'prompt': 'test', 'mode': 'Ref2VA'},
                    'test', workflow, '16:9', bindings=bindings)
                encoding = subgraph(graph, ['7'])
                ref = next(n for n in encoding.values() if n['class_type'] == 'MiniMaxH3ReferenceToVideo')
                audio_id = ref['inputs']['ref_audios.ref_audio_1'][0]
                self.assertEqual(encoding[audio_id]['class_type'], 'LoadAudio')
                self.assertEqual(encoding[audio_id]['inputs']['audio'], 'reference.wav')
                self.assertEqual(encoding['42']['class_type'], 'LoadVideo')
                subgraph(graph, ['16'])


if __name__=='__main__':unittest.main()
