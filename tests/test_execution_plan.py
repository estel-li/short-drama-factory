"""Execution planning is deterministic and reads actual inputs without engine work."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.assets import Assets
from app.content import Content, keyframe_prefix
from app.contracts import ContractError
from app.execution_plan import _model_observations, build_plan
from app.quality import render_contract
from app.schemas import Options
from app.storage import ROOT, read_json, write_json


class ExecutionPlanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        request = read_json(ROOT / 'agent-skills/short-drama-factory/assets/project-storyboard.json')
        self.story = copy.deepcopy(request['storyboard'])
        for index, shot in enumerate(self.story['shots']):
            shot['uid'] = f'shot-{index + 1}'
        self.options = Options.model_validate(request['options'])
        self.renderer = {'profiles': {'draft': {'label': 'test', 'workflow': 'native', 'megapixels': .4,
                                              'steps': 4, 'turbo': False}},
                         'mode': 'local', 'comfy_dir': str(self.root / 'comfy'), 'comfy_auth_token': 'never-show-me'}
        self.config = SimpleNamespace(renderer_config=lambda: copy.deepcopy(self.renderer))
        self.projects = SimpleNamespace(path=lambda pid: self.root, options=lambda folder: self.options)
        self.assets = Assets(self.config, self.projects)
        self.content = SimpleNamespace(mode=lambda shot, options, bindings: Content.mode(None, shot, options, bindings))
        self.save()

    def save(self):
        for shot in self.story['shots']:
            if shot.get('use_previous_last_frame') and not shot['prompt'].startswith('For the target video'):
                shot['prompt'] = keyframe_prefix('I2VA', 107 / 24) + '\n\n' + shot['prompt']
        write_json(self.root / '分镜.json', self.story)
        write_json(self.root / 'settings.json', self.options.model_dump())

    def plan(self, **request):
        return build_plan(self.projects, self.assets, self.content, self.config, 'project-1', request, 'revision-1')

    def completed(self, *uids):
        records = read_json(self.root / 'state.json', {}).get('shots_by_uid', {})
        (self.root / 'clips').mkdir(exist_ok=True)
        for shot in self.story['shots']:
            if uids and shot['uid'] not in uids:
                continue
            relative = 'clips/' + shot['uid'] + '.mp4'
            (self.root / relative).write_bytes(('test clip ' + shot['uid']).encode())
            records[shot['uid']] = {'status': 'done', 'clip_relative': relative,
                                   'render_contract': render_contract(self.story, shot), 'signature': 'recorded-graph-signature'}
        write_json(self.root / 'state.json', {'shots_by_uid': records})
        write_json(self.root / 'renderer_snapshot.json', {'settings': self.options.model_dump(),
                   'environment': {'profiles': self.renderer['profiles']}, 'models': {'example': 'recorded-model'}})

    def add_shot(self, uid, character=None, chained=False):
        shot = copy.deepcopy(self.story['shots'][0])
        shot.update(id=len(self.story['shots']) + 1, uid=uid, scene='same', scene_id='same',
                    characters=[character] if character else [], use_previous_last_frame=chained)
        self.story['shots'].append(shot)
        return shot

    def test_plan_is_reproducible_read_only_and_never_claims_cache_hit(self):
        self.completed()
        before = {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        with patch('requests.get', side_effect=AssertionError('network')), patch('requests.post', side_effect=AssertionError('network')), \
             patch('app.rendering.fingerprint_models', side_effect=AssertionError('fingerprint mutation')), \
             patch.object(self.assets, 'materialize', side_effect=AssertionError('upload')), \
             patch('pipeline.Runner.references', side_effect=AssertionError('reference mutation')):
            first, second = self.plan(), self.plan()
        self.assertEqual(first, second)
        self.assertTrue(first['ready'], first['blocked'])
        self.assertEqual(first['expected']['aligned_seconds'], 214 / 24)
        self.assertEqual([shot['cache'] for shot in first['shots']], ['candidate_reuse', 'candidate_reuse'])
        self.assertTrue(all(not shot['cache_guaranteed'] for shot in first['shots']))
        self.assertIsNone(first['estimates']['wall_seconds'])
        self.assertNotIn('never-show-me', json.dumps(first))
        self.assertEqual(before, {path.relative_to(self.root).as_posix(): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})

    def test_continuity_closure_and_locked_dependency(self):
        for shot in self.story['shots']:
            shot.update(scene='same', scene_id='same')
        self.story['shots'][1]['use_previous_last_frame'] = True
        self.add_shot('shot-3', chained=True)
        self.add_shot('shot-4')
        self.save()
        self.completed('shot-4')
        plan = self.plan(uids=['shot-1'], regenerate=True, internal_text='allowed')
        self.assertEqual(plan['affected_uids'], ['shot-1', 'shot-2', 'shot-3'])
        self.assertEqual(plan['reasons']['shot-3'], ['previous_last_frame:shot-2'])
        self.story['shots'][1]['locked'] = True
        self.save()
        self.assertIn('DEPENDENCY_LOCKED', [issue['code'] for issue in self.plan(uids=['shot-1'], regenerate=True)['blocked']])

    def test_auto_capture_dependency_respects_pinned_reference(self):
        self.options.auto_reference = True
        self.story['characters'] = [{'id': 'a', 'name': 'Alice', 'visual_description': 'blue coat'}]
        self.story['shots'][0]['characters'] = ['a']
        self.add_shot('shot-3', character='a')
        self.add_shot('shot-4', chained=True)
        self.story['shots'][2].update(scene='same', scene_id='same')
        self.save()
        self.completed('shot-2')
        plan = self.plan(uids=['shot-1'], regenerate=True, internal_text='allowed')
        self.assertEqual(plan['affected_uids'], ['shot-1', 'shot-3', 'shot-4'])
        self.assertIn('captured_character_reference:shot-1', plan['reasons']['shot-3'])
        write_json(self.root / 'references.json', {'a': {'shot_id': 0, 'image': 'external.png'}})
        self.completed()
        pinned = self.plan(uids=['shot-1'], regenerate=True, internal_text='allowed')
        self.assertEqual(pinned['affected_uids'], ['shot-1'])

    def test_missing_dependency_expands_and_unrelated_missing_clip_allows_pilot(self):
        self.story['shots'][0].update(scene='same', scene_id='same')
        self.story['shots'][1].update(scene='same', scene_id='same', use_previous_last_frame=True)
        self.add_shot('unrelated')
        self.save()
        plan = self.plan(uids=['shot-2'], internal_text='allowed')
        self.assertEqual(plan['affected_uids'], ['shot-1', 'shot-2'])
        self.assertTrue(plan['ready'], plan['blocked'])
        self.assertTrue(any(issue['code'] == 'OUTSIDE_SCOPE_CLIP_NOT_READY' and issue['uid'] == 'unrelated' for issue in plan['warnings']))
        self.assertEqual(plan['expected']['delivery_scope'], 'selected_shots')
        self.assertFalse(any(effect['action'] == 'assemble_subtitles_and_review' for effect in plan['effects']))

    def test_stale_continuity_receipt_expands_prerequisite(self):
        for shot in self.story['shots']:
            shot.update(scene='same', scene_id='same')
        self.story['shots'][1]['use_previous_last_frame'] = True
        self.add_shot('shot-3', chained=True)
        self.save()
        self.completed()
        state = read_json(self.root / 'state.json')
        state['shots_by_uid']['shot-2']['first_frame'] = {'source_shot_uid': 'shot-1', 'source_clip_sha256': 'old clip hash'}
        write_json(self.root / 'state.json', state)
        plan = self.plan(uids=['shot-3'])
        self.assertEqual(plan['affected_uids'], ['shot-2', 'shot-3'])
        self.assertIn('missing_or_stale_dependency_clip:shot-3', plan['reasons']['shot-2'])

    def test_required_speech_resource_is_reported_without_download(self):
        self.renderer['runtime_root'] = str(self.root)
        self.story['shots'][0]['dialogue'] = [{'speaker': 'narrator', 'text': 'Hi.', 'narration': True}]
        self.options.narration = True
        self.save()
        self.completed()
        with patch('requests.get', side_effect=AssertionError('no download')):
            plan = self.plan(action='finish')
        issue = next(issue for issue in plan['blocked'] if issue['code'] == 'SPEECH_MODEL_MISSING')
        expected = read_json(ROOT / 'manifests/quality.json')['model']
        self.assertEqual(issue['size'], expected['size'])
        self.assertEqual(next(effect for effect in plan['effects'] if effect['kind'] == 'download')['requirements'],
                         [{'name': expected['filename'], 'bytes': expected['size']}])
        self.assertFalse((self.root / 'data/quality').exists())
        self.options.edit_preset = 'original'
        self.options.subtitle_alignment = 'approximate'
        self.assertNotIn('SPEECH_MODEL_MISSING', [issue['code'] for issue in self.plan(action='finish')['blocked']])

    def test_fingerprint_tracks_real_assets_clips_settings_and_model_stats(self):
        self.completed()
        (self.root / 'asset.png').write_bytes(b'first pixels')
        write_json(self.root / 'assets.json', {'asset1': {'file': 'asset.png', 'sha256': 'stale-manifest-value'}})
        first = self.plan()
        (self.root / 'asset.png').write_bytes(b'changed pixels')
        second = self.plan()
        self.assertNotEqual(first['input_fingerprint'], second['input_fingerprint'])
        self.assertEqual(first['environment_fingerprint'], second['environment_fingerprint'])
        (self.root / 'clips/shot-1.mp4').write_bytes(b'changed rendered clip')
        third = self.plan()
        self.assertNotEqual(second['input_fingerprint'], third['input_fingerprint'])
        self.assertEqual(second['environment_fingerprint'], third['environment_fingerprint'])
        self.options.seed += 1
        fourth = self.plan()
        self.assertNotEqual(third['input_fingerprint'], fourth['input_fingerprint'])
        self.renderer['fl_model'] = 'test.safetensors'
        model = self.root / 'comfy/models/diffusion_models/test.safetensors'
        model.parent.mkdir(parents=True)
        model.write_bytes(b'fake weights')
        fifth = self.plan()
        model.write_bytes(b'new fake weights')
        sixth = self.plan()
        self.assertNotEqual(fifth['input_fingerprint'], sixth['input_fingerprint'])
        self.assertNotEqual(fifth['environment_fingerprint'], sixth['environment_fingerprint'])
        self.assertEqual(sixth['models'][0]['availability'], 'local')

    def test_required_models_follow_selected_modes_and_native_turbo(self):
        roles = {'fl_model': 'diffusion_models', 'text_encoder': 'text_encoders',
                 'video_vae': 'vae', 'audio_vae': 'vae'}
        for role, category in roles.items():
            filename = role + '.safetensors'
            self.renderer[role] = filename
            path = self.root / 'comfy/models' / category / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture model')
        self.renderer.update(ref_model='absent-ref.safetensors', fl_lora='absent-fl-lora.safetensors',
                             ref_lora='absent-ref-lora.safetensors')
        self.completed()
        plan = self.plan(uids=['shot-1'])
        self.assertTrue(plan['ready'], plan['blocked'])
        self.assertEqual({model['role'] for model in plan['models']}, set(roles))
        self.assertEqual(plan['modes'], ['T2VA'])
        self.renderer['profiles']['draft']['turbo'] = True
        turbo = self.plan(uids=['shot-1'])
        self.assertIn('fl_lora', {model['role'] for model in turbo['models']})
        self.assertNotIn('ref_lora', {model['role'] for model in turbo['models']})
        self.assertIn('MODEL_FILES_MISSING', [issue['code'] for issue in turbo['blocked']])

    def test_optional_workflow_models_use_only_corresponding_head(self):
        from app.video_workflows import BUILTIN_PROFILES
        self.renderer.update(fl_model='fl.safetensors', ref_model='ref.safetensors')
        self.renderer['mode'] = 'remote'
        self.renderer['profiles']['draft'] = copy.deepcopy(BUILTIN_PROFILES['pdd-upscale'])
        fl = {model['role'] for model in _model_observations(self.renderer, 'draft', {'I2VA'})}
        self.assertEqual(fl, {'fl_model', 'pdd_fl', 'upscaler'})
        ref = {model['role'] for model in _model_observations(self.renderer, 'draft', {'Ref2VA'})}
        self.assertEqual(ref, {'ref_model', 'pdd_ref', 'upscaler'})
        self.assertEqual(_model_observations(self.renderer, 'draft', set()), [])

    def test_larry_turbo_observes_its_own_adapter_without_the_old_turbo_stack(self):
        from app.video_workflows import BUILTIN_PROFILES
        self.renderer.update(fl_model='fl.safetensors', fl_lora='old-turbo.safetensors')
        self.renderer['mode'] = 'remote'
        self.renderer['profiles']['draft'] = copy.deepcopy(BUILTIN_PROFILES['larry-turbo'])
        rows = _model_observations(self.renderer, 'draft', {'T2VA'})
        by_role = {row['role']: row for row in rows}
        self.assertEqual(by_role['workflow_lora']['name'], 'minimax_h3_turbo_v4_step600_ema.safetensors')
        self.assertNotIn('fl_lora', by_role)
        self.assertNotIn('ref_model', by_role)

    def test_partial_scope_never_promises_current_full_assembly_after_settings_change(self):
        self.completed()
        for change in ('unchanged', 'ratio', 'profile'):
            with self.subTest(change=change):
                if change == 'ratio':
                    self.options.ratio = '16:9'
                elif change == 'profile':
                    self.renderer['profiles']['draft']['megapixels'] = .6
                plan = self.plan(uids=['shot-1'])
                outside = next(shot for shot in plan['shots'] if shot['uid'] == 'shot-2')
                self.assertTrue(outside['source_valid'])
                self.assertFalse(outside['assembly_ready'])
                self.assertEqual(plan['expected']['delivery_scope'], 'selected_shots')
                self.assertTrue(any(issue['code'] == 'OUTSIDE_SCOPE_CLIP_UNVERIFIED' for issue in plan['warnings']))
                self.assertFalse(any(effect['action'] == 'assemble_subtitles_and_review' for effect in plan['effects']))

    def test_strict_missing_content_and_automatic_image_preparation_are_explicit(self):
        self.story['shots'][0]['prompt'] = ''
        self.save()
        plan = self.plan()
        self.assertFalse(plan['ready'])
        self.assertIn('EXTERNAL_CONTENT_REQUIRED', [issue['code'] for issue in plan['blocked']])
        self.options.reference_images.enabled = True
        strict = self.plan()
        self.assertIn('REFERENCE_PREPARATION_SKIPPED', [issue['code'] for issue in strict['warnings']])
        self.assertFalse(any(effect['kind'] == 'text' for effect in strict['effects']))
        allowed = self.plan(internal_text='allowed')
        self.assertIn('REFERENCE_PREPARATION_SKIPPED', [issue['code'] for issue in allowed['warnings']])
        self.assertIn('EXTERNAL_CONTENT_REQUIRED', [issue['code'] for issue in allowed['blocked']])
        self.assertEqual(allowed['effective_internal_text'], 'forbid')
        text_plan = self.plan(action='plan', internal_text='allowed')
        self.assertNotIn('REFERENCE_PREPARATION_REQUIRES_EXPLICIT_CONTENT', [issue['code'] for issue in text_plan['blocked']])
        self.assertTrue(any(effect['action'] == 'reference_image_prompt_optimization' for effect in text_plan['effects']))

    def test_workflow_contract_and_missing_models_are_reported_without_preparation(self):
        from app.video_workflows import BUILTIN_PROFILES
        self.renderer['profiles']['draft'] = copy.deepcopy(BUILTIN_PROFILES['h3-audio-drive'])
        self.renderer['fl_model'] = 'missing.safetensors'
        plan = self.plan()
        codes = [issue['code'] for issue in plan['blocked']]
        self.assertIn('WORKFLOW_BLOCKED', codes)
        self.assertIn('MODEL_FILES_MISSING', codes)
        self.assertTrue(any(effect['kind'] == 'download' and effect['action'] == 'none_authorized' for effect in plan['effects']))

    def test_finish_requires_matching_complete_clips_and_has_no_gpu_effect(self):
        missing = self.plan(action='finish')
        self.assertIn('FINISH_INPUT_NOT_READY', [issue['code'] for issue in missing['blocked']])
        self.completed()
        ready = self.plan(action='finish')
        self.assertTrue(ready['ready'], ready['blocked'])
        self.assertFalse(any(effect['kind'] in ('gpu', 'text') for effect in ready['effects']))
        with patch.object(self.assets, 'resolve', side_effect=AssertionError('finish does not need original reference assets')):
            self.assertTrue(self.plan(action='finish')['ready'])
        self.story['shots'][0]['action'] = 'Different action'
        self.save()
        self.assertFalse(self.plan(action='finish')['ready'])

    def test_invalid_or_empty_scope_is_not_silently_all_shots(self):
        self.assertEqual(self.plan(uids=None)['requested_uids'], ['shot-1', 'shot-2'])
        for request in ({'uids': []}, {'uids': ['absent']}, {'uids': 'shot-1'}, {'action': 'finish', 'regenerate': True}):
            with self.subTest(request=request), self.assertRaises(ContractError):
                self.plan(**request)


if __name__ == '__main__':
    unittest.main()
