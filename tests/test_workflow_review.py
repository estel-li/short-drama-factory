import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.content import Content
from app.database import Database
from app.schemas import Options, Quality
from app.storage import write_json
from app.video_workflows import BUILTIN_PROFILES
from app.workflow_checks import workflow_report


class WorkflowPreflightTests(unittest.TestCase):
    def report(self, workflow, bindings, mode='auto', duration=4, **preset):
        story = {'characters': [], 'shots': [{'id': 1, 'uid': 'one', 'duration': duration,
                 'characters': [], 'dialogue': [], 'mode': mode}]}
        options = Options(profile=workflow)
        config = {'profiles': {workflow: {**BUILTIN_PROFILES[workflow], **preset}}}
        return workflow_report(story, options, config, lambda *args: bindings,
                               lambda shot, options, bindings: Content.mode(None, shot, options, bindings))

    def test_missing_slots_and_conflicting_modes_are_not_ready(self):
        self.assertFalse(self.report('h3-audio-drive', {})['ready'])
        report = self.report('lightx2v-8', {'images': [{'id': 'hero'}]})
        self.assertFalse(report['ready'])
        self.assertIn('Ref2VA', report['issues'][0]['message'])
        report = self.report('h3-foley', {'source_video': {'frames': 200}, 'first_frame': {'id': 'first'}}, mode='T2VA')
        self.assertFalse(report['ready'])

    def test_video_length_uses_aligned_frames_and_offset_not_requested_seconds(self):
        # A 4 second source has 96 frames but H3 needs 107 for a 4 second request.
        self.assertFalse(self.report('h3-foley', {'source_video': {'frames': 96}})['ready'])
        report = self.report('h3-foley', {'source_video': {'frames': 131, 'fps': 24}}, source_start_seconds=1)
        self.assertTrue(report['ready'])
        self.assertEqual(report['shots'][0]['aligned_frames'], 107)
        self.assertFalse(self.report('h3-foley', {'source_video': {'frames': 130}}, source_start_seconds=1)['ready'])

    def test_context_limit_and_audio_tail_are_checked_before_rendering(self):
        self.assertFalse(self.report('h3-motion-context', {'source_video': {'frames': 21}})['ready'])
        self.assertFalse(self.report('h3-motion-context', {'source_video': {'frames': 360}}, duration=15)['ready'])
        report = self.report('h3-audio-drive', {'source_audio': {'duration': 3}})
        self.assertTrue(report['ready'])
        self.assertEqual(report['issues'][0]['severity'], 'warning')
        self.assertFalse(self.report('h3-audio-drive', {'source_audio': {'duration': 3}}, source_start_seconds=3)['ready'])

    def test_invalid_pdd_and_nonfinite_profiles_fail_before_graph_submission(self):
        for fields in ({'sampler': 'heun'}, {'turbo': True}, {'denoise': .5},
                       {'megapixels': float('nan')}, {'lora_strength': float('nan')}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                Quality.model_validate({**BUILTIN_PROFILES['pdd-8'], **fields})

    def test_auto_identity_cannot_change_to_unsupported_ref_mode_on_later_shots(self):
        story = {'characters': [{'id': 'hero', 'name': 'hero'}], 'shots': [
            {'id': 1, 'duration': 4, 'characters': ['hero'], 'dialogue': []}]}
        config = {'profiles': BUILTIN_PROFILES}
        options = Options(profile='lightx2v-8')
        report = workflow_report(story, options, config, lambda *args: {},
            lambda shot, options, bindings: Content.mode(None, shot, options, bindings))
        self.assertFalse(report['ready'])
        self.assertIn('自动角色参考', report['issues'][0]['message'])
        options.h3_mode = 'T2VA'
        self.assertTrue(workflow_report(story, options, config, lambda *args: {},
            lambda shot, options, bindings: Content.mode(None, shot, options, bindings))['ready'])

    def test_prepare_progress_is_scoped_and_uses_durable_queue_status(self):
        from app import api
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = Database(root / 'test.sqlite3')
            first = database.enqueue('__video_environment', 'video-prepare', {'profile': 'pdd-8'})
            database.update(first, 'done', 'ready')
            second = database.enqueue('__video_environment', 'video-prepare', {'profile': 'h3-foley'})
            write_json(root / 'data/video-environment-progress.json', {'job_id': first, 'status': 'done', 'progress': {'bytes': 999}})
            with patch.object(api, 'db', database), patch.object(api, 'config', SimpleNamespace(root=root)):
                client = TestClient(api.app, base_url='http://127.0.0.1')
                state = client.get('/api/video/workflows/progress').json()
                self.assertEqual((state['job_id'], state['status'], state['profile']), (second, 'queued', 'h3-foley'))
                self.assertNotIn('progress', state)
                database.cancel('__video_environment')
                self.assertEqual(client.get('/api/video/workflows/progress').json()['status'], 'paused')
                self.assertEqual(client.get('/api/video/workflows/progress', params={'job_id': first}).json()['status'], 'done')


if __name__ == '__main__':
    unittest.main()
