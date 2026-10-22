import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pipeline
from app.assets import Assets
from app.config import ConfigStore
from app.content import BASE_FIELDS, Content, assemble_prompt
from app.contracts import ContractError
from app.database import Database
from app.execution_policy import execution_policy
from app.image_studio import ImageStudio
from app.jobs import Worker
from app.projects import Projects
from app.providers import LLMClient
from app.quality import render_contract
from app.schemas import Options, Provider
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class ScopedExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/queue.sqlite3')
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.content = Content(self.config, Skills(), self.projects)
        self.worker = Worker(self.db, self.config, self.projects, self.content, self.assets)
        self.options = Options(input_mode='storyboard', duration_rule='count',
                               shot_count=3, total_seconds=12, auto_reference=False)
        self.prompt = assemble_prompt({name: '[Shot 1] A quiet room.' for name in BASE_FIELDS}, 'T2VA', 107 / 24)
        raw = {'title': 'Scoped rendering', 'shots': [
            {'uid': uid, 'scene': 'room', 'continuity_group': 'day', 'summary': uid, 'prompt': self.prompt}
            for uid in ('first', 'second', 'third')]}
        self.project = self.projects.create('', self.options.model_dump(), raw)
        self.story = self.projects.get(self.project.name)['story']
        config_patch = patch.dict(pipeline.CONFIG, self.config.renderer_config(), clear=True)
        config_patch.start()
        self.addCleanup(config_patch.stop)

    def run_renderer(self, allowed, *, regenerate=(), execution_id='plan-a'):
        runner = pipeline.Runner(self.project)
        runner.allowed_uids = allowed
        runner.regenerate_uids = regenerate
        runner.execution_id = execution_id
        runner.encode = lambda graph, shot, signature: graph
        runner.sample = lambda graph, shot, signature: graph
        runner.wait = lambda prompt_id: {'filename': 'fixture.mp4', 'type': 'output'}
        return runner

    def rendering_mocks(self):
        """Exercise Runner's real selection/cache logic, replace only engine I/O."""
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch('pipeline.ensure_comfy'))
        stack.enter_context(patch('pipeline.validate_graph'))
        submit = stack.enter_context(patch('pipeline.api', side_effect=lambda path, data=None:
            {'prompt_id': 'fake-prompt'} if path == '/prompt' else {'queue_running': [], 'queue_pending': []}))
        assemble = stack.enter_context(patch('pipeline.assemble', return_value=self.project / '成片.mp4'))
        stack.enter_context(patch('app.comfyio.download_file', side_effect=lambda item, path, *args: Path(path).write_bytes(b'clip')))
        width, height = pipeline.output_canvas(pipeline.CONFIG['profiles'][self.options.profile], self.options.ratio)
        stack.enter_context(patch('pipeline.media_info', return_value={'frames': 107, 'width': width, 'height': height,
                                                                      'audio': True, 'timestamps_monotonic': True}))
        return stack, submit, assemble

    def test_selected_render_never_generates_other_missing_shots_or_assembles(self):
        self.story['shots'][0]['prompt'] = ''
        self.story['shots'][2]['prompt'] = ''
        self.projects.save_story(self.project.name, self.story)
        stack, submit, assemble = self.rendering_mocks()
        with stack:
            runner = self.run_renderer(['second'])
            runner.run()
        graphs = [call.args[1]['prompt'] for call in submit.call_args_list if call.args[0] == '/prompt']
        self.assertEqual(len(graphs), 1)
        self.assertIn('second', graphs[0]['16']['inputs']['filename_prefix'])
        assemble.assert_not_called()
        self.assertEqual(runner.state['current_stage'], 'scope_complete')
        self.assertEqual(runner.state['status'], 'ready')
        self.assertEqual(runner.state['pending_uids'], ['first', 'third'])
        self.assertEqual(runner.state['pending_count'], 2)

    def test_empty_scope_never_starts_engine(self):
        with patch('pipeline.ensure_comfy') as engine, patch('pipeline.assemble') as assemble:
            runner = self.run_renderer([])
            runner.run()
        engine.assert_not_called()
        assemble.assert_not_called()
        self.assertEqual(runner.state['pending_count'], 3)

    def test_changed_global_settings_leave_outside_cache_unverified_and_never_assemble(self):
        stack, _, _ = self.rendering_mocks()
        with stack:
            self.run_renderer(None).run()
        self.options.profile = 'dialogue'
        self.options.ratio = '16:9'
        self.projects.save_options(self.project.name, self.options.model_dump())
        stack, _, assemble = self.rendering_mocks()
        with stack:
            runner = self.run_renderer(['second'])
            runner.run()
        assemble.assert_not_called()
        self.assertEqual(runner.state['status'], 'ready')
        self.assertEqual(runner.state['pending_uids'], ['first', 'third'])
        self.assertEqual(runner.state['unverified_uids'], ['first', 'third'])
        self.assertEqual(runner.state['pending_reasons'],
                         {'first': 'not_validated_in_scope', 'third': 'not_validated_in_scope'})

    def test_continuity_cannot_use_previous_selected_instead_of_previous_shot(self):
        self.story['shots'][2]['use_previous_last_frame'] = True
        self.story['shots'][2]['prompt'] = assemble_prompt(
            {name: '[Shot 1] <Picture 1> continues.' for name in BASE_FIELDS}, 'I2VA', 107 / 24)
        self.projects.save_story(self.project.name, self.story)
        stack, _, assemble = self.rendering_mocks()
        with stack, patch('app.continuity.extract_last_frame') as extract:
            with self.assertRaises(ContractError) as caught:
                self.run_renderer(['first', 'third']).run()
        self.assertEqual(caught.exception.code, 'DEPENDENCY_OUTSIDE_SCOPE')
        extract.assert_not_called()
        assemble.assert_not_called()

    def test_continuity_uses_valid_unselected_immediate_predecessor(self):
        self.story['shots'][2]['use_previous_last_frame'] = True
        self.story['shots'][2]['prompt'] = assemble_prompt(
            {name: '[Shot 1] <Picture 1> continues.' for name in BASE_FIELDS}, 'I2VA', 107 / 24)
        self.story = self.projects.save_story(self.project.name, self.story)
        clip = self.project / 'second.mp4'
        clip.write_bytes(b'prior-clip')
        state = read_json(self.project / 'state.json')
        state['shots_by_uid'] = {'second': {'status': 'done', 'clip': str(clip),
                                           'render_contract': render_contract(self.story, self.story['shots'][1])}}
        write_json(self.project / 'state.json', state)
        frame = {'source_shot_uid': 'second', 'source_clip_sha256': 'source-hash', 'sha256': 'frame-hash',
                 'comfy_file': 'frame.png', 'type': 'image'}
        stack, _, assemble = self.rendering_mocks()
        with stack, patch('app.continuity.extract_last_frame', return_value=frame) as extract, \
                patch('app.continuity.materialize_frame', return_value=frame):
            self.run_renderer(['third']).run()
        self.assertEqual(extract.call_args.args[2]['uid'], 'second')
        self.assertEqual(extract.call_args.args[3], clip)
        assemble.assert_not_called()

    def test_stale_unselected_continuity_take_cannot_be_used_as_new_source(self):
        for shot in self.story['shots'][1:]:
            shot['use_previous_last_frame'] = True
            shot['prompt'] = assemble_prompt(
                {name: '[Shot 1] <Picture 1> continues.' for name in BASE_FIELDS}, 'I2VA', 107 / 24)
        self.story = self.projects.save_story(self.project.name, self.story)
        records = {}
        for shot in self.story['shots'][:2]:
            clip = self.project / (shot['uid'] + '.mp4')
            clip.write_bytes(b'current-clip')
            records[shot['uid']] = {'status': 'done', 'clip': str(clip),
                                    'render_contract': render_contract(self.story, shot)}
        records['second']['first_frame'] = {'source_shot_uid': 'first', 'source_clip_sha256': 'stale-hash'}
        state = read_json(self.project / 'state.json')
        state['shots_by_uid'] = records
        write_json(self.project / 'state.json', state)
        with patch('pipeline.ensure_comfy'), patch('app.continuity.extract_last_frame') as extract:
            with self.assertRaises(ContractError) as caught:
                self.run_renderer(['third']).run()
        self.assertEqual(caught.exception.code, 'DEPENDENCY_OUTSIDE_SCOPE')
        extract.assert_not_called()

    def test_regeneration_nonce_forces_once_and_same_receipt_resumes_cache(self):
        stack, submit, _ = self.rendering_mocks()
        with stack:
            self.run_renderer(['second']).run()
            self.run_renderer(['second'], regenerate=['second']).run()
            self.run_renderer(['second'], regenerate=['second']).run()
            self.run_renderer(['second']).run()
        self.assertEqual(sum(call.args[0] == '/prompt' for call in submit.call_args_list), 2)
        self.assertEqual(read_json(self.project / '分镜.json'), self.story)

    def test_old_assembly_archives_only_when_real_render_work_starts(self):
        final = self.project / '成片.mp4'
        final.write_bytes(b'old-assembly')
        stack, _, _ = self.rendering_mocks()
        with stack:
            runner = self.run_renderer(['second'])
            runner.before_render = lambda: self.projects.archive_final(self.project)
            runner.run()
            self.assertFalse(final.exists())
            self.assertEqual(len(list((self.project / 'takes').glob('final_*/成片.mp4'))), 1)
            final.write_bytes(b'current-assembly')
            cached = self.run_renderer(['second'])
            cached.before_render = Mock()
            cached.run()
            cached.before_render.assert_not_called()
            self.assertTrue(final.exists())

    def test_strict_worker_skips_hidden_text_and_reference_preparation(self):
        self.options.reference_images.enabled = True
        self.projects.save_options(self.project.name, self.options.model_dump())
        payload = {'internal_text': 'allowed', 'strict_render': True, 'allowed_uids': ['second']}
        jid = self.worker.enqueue(self.project.name, 'render', payload)
        job = self.db.claim()
        with patch.object(self.content, 'call', side_effect=AssertionError('internal text called')), \
                patch.object(self.worker.images, 'ensure_references', side_effect=AssertionError('hidden reference generation')), \
                patch.object(self.worker.images, 'release_idle'), \
                patch('app.jobs.fingerprint_models', return_value={}) as fingerprint, patch('pipeline.Runner') as runner:
            runner.return_value.state = {}
            def validate_dynamic(limit=None):
                shot = copy.deepcopy(self.story['shots'][1])
                shot.pop('prompt_manual', None)
                shot['prompt_snapshot'] = {'settings_hash': 'old'}
                result = runner.return_value.prompt_compiler(self.story, shot, {})
                self.assertEqual(result, self.prompt)
            runner.return_value.run.side_effect = validate_dynamic
            self.assertEqual(self.worker.execute(job), 'done')
            self.assertEqual(runner.return_value.allowed_uids, ['second'])
            self.assertEqual(fingerprint.call_args.kwargs['modes'], {'T2VA'})
        self.assertEqual(job['id'], jid)

    def test_strict_missing_prompt_fails_before_engine_and_provider(self):
        self.story['shots'][1]['prompt'] = ''
        self.projects.save_story(self.project.name, self.story)
        jid = self.worker.enqueue(self.project.name, 'render', {'strict_render': True, 'allowed_uids': ['second']})
        with patch('pipeline.Runner') as runner, patch.object(self.content, 'call') as provider:
            with self.assertRaises(ContractError) as caught:
                self.worker.execute(self.db.job(jid))
        self.assertEqual(caught.exception.code, 'EXTERNAL_CONTENT_REQUIRED')
        runner.assert_not_called()
        provider.assert_not_called()


class ActualProviderBoundaryTests(unittest.TestCase):
    def test_generation_boundaries_block_before_configuration_or_network(self):
        client = LLMClient(Provider(id='example', name='Example', base_url='https://invalid.test/v1'), '')
        content = Content(Mock(), Mock(), Mock())
        image = ImageStudio.__new__(ImageStudio)
        image.get = Mock(return_value={'request': {'prompt': 'A cloud', 'optimize': True}})
        image.environment = Mock()
        with execution_policy(), patch.object(client, 'client') as network:
            for call in (lambda: client.generate([]),
                         lambda: content.call(None, 'prompt', None, {}, {}, None, None, None),
                         lambda: image.optimize('id', None, None),
                         lambda: pipeline.plan('story')):
                with self.assertRaises(ContractError) as caught:
                    call()
                self.assertEqual(caught.exception.code, 'TEXT_GENERATION_FORBIDDEN')
        network.assert_not_called()
        content.config.provider.assert_not_called()
        image.environment.settings.assert_not_called()

    def test_image_authored_or_cached_prompt_remains_usable_in_strict_mode(self):
        image = ImageStudio.__new__(ImageStudio)
        image.environment = Mock()
        for request, cached, expected in (({'prompt': 'A cloud', 'optimize': False}, '', 'A cloud'),
                ({'prompt': 'A cloud', 'optimized_prompt': 'User authored'}, '', 'User authored'),
                ({'prompt': 'A cloud'}, 'Previously authored', 'Previously authored')):
            image.get = Mock(return_value={'request': request, 'optimized_prompt': cached})
            with execution_policy():
                self.assertEqual(image.optimize('id', None, None), expected)
        image.environment.settings.assert_not_called()


class RenderModelScopeTests(unittest.TestCase):
    def fingerprint(self, modes, workflow='native', turbo=True):
        from app.rendering import fingerprint_models
        config = read_json(ROOT / 'config.default.json')
        config['mode'] = 'remote'
        config['profiles'] = {'chosen': {'workflow': workflow, 'turbo': turbo}}
        if modes == {'T2VA'}:
            config.pop('ref_model', None)
            config.pop('ref_lora', None)
        with tempfile.TemporaryDirectory() as directory:
            config['runtime_root'] = directory
            def response(url, **kwargs):
                result = Mock(ok=True)
                result.json.return_value = {**kwargs['params'], 'name': kwargs['params']['filename'], 'sha256': 'a' * 64}
                return result
            with patch('app.rendering.requests.get', side_effect=response) as get:
                value = fingerprint_models(config, lambda message: None, lambda: False,
                                           profile='chosen', modes=modes)
        self.assertEqual(get.call_count, len(value))
        return set(value)

    def test_text_mode_does_not_require_or_probe_reference_models(self):
        common = {'text_encoder', 'video_vae', 'audio_vae', 'fl_model'}
        self.assertEqual(self.fingerprint({'T2VA'}), common | {'fl_lora'})
        self.assertEqual(self.fingerprint({'T2VA'}, turbo=False), common)

    def test_reference_pdd_only_checks_its_side_and_upscaler(self):
        self.assertEqual(self.fingerprint({'Ref2VA'}, workflow='pdd-upscale'),
                         {'text_encoder', 'video_vae', 'audio_vae', 'ref_model', 'pdd_ref', 'upscaler'})

    def test_empty_modes_do_not_probe_models_and_legacy_none_keeps_all(self):
        from app.rendering import ROLES
        self.assertEqual(self.fingerprint(set()), set())
        self.assertEqual(self.fingerprint(None, turbo=False), set(ROLES))

if __name__ == '__main__':
    unittest.main()
