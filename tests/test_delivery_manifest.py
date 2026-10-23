"""Read-only delivery inventory, actual CPU decoding and provenance boundaries."""
import copy
import hashlib
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

import pipeline
from app.delivery import build_delivery, inspect_media
from app.quality import render_contract
from app.storage import digest, read_json, write_json


class DeliveryManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.shared.cleanup)
        cls.video = Path(cls.shared.name).resolve() / 'fixture.mp4'
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=24',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                         '-c:v', 'libx264', '-bf', '0', '-c:a', 'aac', '-frames:v', '12', '-t', '0.5', cls.video])

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        # Windows runners may expose TEMP through an 8.3 alias. Production
        # artifact paths are canonical, so compare against a canonical fixture.
        self.root = Path(temp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.busy = False
        self.story = {'title': 'fixture', 'characters': [], 'shots': [{'id': 1, 'uid': 's1', 'duration': .5,
                       'summary': 'blue scene', 'prompt': 'external prompt', 'dialogue': []}]}
        write_json(self.project / '分镜.json', self.story)
        write_json(self.project / 'state.json', {'status': 'complete', 'shots_by_uid': {}})
        write_json(self.project / 'settings.json', {'subtitles': False})
        self.projects = SimpleNamespace(path=lambda pid: self.project,
                                       revision=lambda pid: digest(read_json(self.project / '分镜.json')),
                                       db=SimpleNamespace(busy=lambda pid: self.busy))
        for target in ('requests.sessions.Session.request', 'app.speech.ensure_model', 'pipeline.Runner.run'):
            item = patch(target, side_effect=AssertionError('Delivery must not use providers, models or GPU'))
            item.start()
            self.addCleanup(item.stop)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def snapshot(self):
        return {path.relative_to(self.project).as_posix(): (self.sha(path), path.stat().st_mtime_ns)
                for path in self.project.rglob('*') if path.is_file()}

    def final(self):
        target = self.project / '成片.mp4'
        shutil.copy2(self.video, target)
        return target

    def complete_edit(self, name='edit-1', review=True):
        final = self.final()
        folder = self.project / 'edits' / name
        folder.mkdir(parents=True)
        shutil.copy2(final, folder / final.name)
        (self.project / '字幕.srt').write_text('', encoding='utf-8')
        (folder / '字幕.srt').write_text('', encoding='utf-8')
        source = self.project / 'source_cache' / 'snapshot.mp4'
        source.parent.mkdir(exist_ok=True)
        shutil.copy2(final, source)
        recipe = {'version': 1, 'story': copy.deepcopy(self.story), 'width': 96, 'height': 64,
                  'sources': [{'uid': 's1', 'file': 'source_cache/snapshot.mp4', 'sha256': self.sha(source)}]}
        write_json(folder / 'recipe.json', recipe)
        report = {'version': 1, 'edit_id': name, 'recipe_hash': digest(recipe), 'expected_frames': 12,
                  'final': {'frames': 12, 'width': 96, 'height': 64, 'audio': True}}
        write_json(folder / '媒体验收.json', report)
        shutil.copy2(folder / '媒体验收.json', self.project / '媒体验收.json')
        write_json(folder / 'completed.json', {'completed_at': 'fixture', 'files':
                   {item: self.sha(folder / item) for item in ('成片.mp4', '字幕.srt', '媒体验收.json')}})
        write_json(self.project / 'current_edit.json', {'id': name, 'recipe': 'edits/' + name + '/recipe.json'})
        if review:
            page = folder / 'review' / 'overview_001.png'
            page.parent.mkdir()
            Image.new('RGB', (32, 24), 'blue').save(page)
            write_json(folder / 'review/index.json', {'pages': [{'kind': 'overview', 'file': 'review/overview_001.png',
                                                                 'sha256': self.sha(page), 'items': 1}]})
        return folder

    def test_manifest_lists_real_aliases_hashes_urls_and_never_writes(self):
        folder = self.complete_edit()
        (self.project / 'private.secret').write_text('must not inventory', encoding='utf-8')
        before = self.snapshot()
        first, second = build_delivery(self.projects, 'project'), build_delivery(self.projects, 'project')
        self.assertEqual(first, second)
        self.assertEqual(self.snapshot(), before)
        original = first['aliases']['original']
        self.assertEqual(original['sha256'], self.sha(self.project / '成片.mp4'))
        self.assertEqual(original['size'], self.video.stat().st_size)
        self.assertTrue(Path(original['local_path']).is_absolute())
        self.assertEqual(original['mime'], 'video/mp4')
        self.assertTrue(original['api_url'].startswith('/api/v2/projects/project/delivery/files/'))
        self.assertIsNone(first['aliases']['subtitled'])
        self.assertEqual(first['aliases']['subtitles']['mime'], 'application/x-subrip')
        self.assertFalse(first['media_verified'])
        self.assertFalse(first['ready_for_delivery'])
        self.assertEqual(first['checks']['media']['status'], 'not_checked')
        self.assertEqual(first['checks']['recorded_provenance']['status'], 'passed')
        self.assertEqual(first['current_edit']['id'], folder.name)
        self.assertTrue(first['current_edit']['review_pages'][0]['hash_matches'])
        self.assertNotIn('private.secret', [item['relative_path'] for item in first['artifacts']])

    def test_full_decode_measures_real_video_and_audio_without_claiming_content(self):
        self.complete_edit()
        before = self.snapshot()
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(manifest['media_verified'], manifest['checks'])
        self.assertTrue(manifest['ready_for_delivery'], manifest['checks'])
        media = manifest['aliases']['original']['media']
        self.assertEqual((media['width'], media['height'], media['frames']), (96, 64, 12))
        self.assertAlmostEqual(media['duration'], .5, places=5)
        self.assertTrue(media['audio'])
        audio = next(stream for stream in media['streams'] if stream['type'] == 'audio')
        self.assertGreater(audio['samples'], 0)
        self.assertTrue(all(stream['timestamps_monotonic'] for stream in media['streams']))
        self.assertEqual(manifest['delivery_scope'], 'technical_integrity_only')
        self.assertFalse(manifest['content_review_complete'])
        for check in ('visual_content', 'dialogue_content', 'subtitle_content'):
            self.assertEqual(manifest['checks'][check]['status'], 'not_checked')
        self.assertEqual(manifest['aliases']['original']['verification']['sha256'], self.sha(self.video))

    def test_missing_prior_report_is_unavailable_not_prior_pass(self):
        self.final()
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'unavailable')
        self.assertTrue(manifest['media_verified'])
        self.assertTrue(manifest['ready_for_delivery'])

    def test_real_finishing_report_and_review_index_are_linked_to_actual_files(self):
        from app.finishing import build
        source = self.project / 'source.mp4'
        shutil.copy2(self.video, source)
        build(self.project, self.story, [source], 96, 64,
              {'edit_preset': 'original', 'subtitle_alignment': 'approximate', 'subtitles': False})
        before = self.snapshot()
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(manifest['ready_for_delivery'], manifest['checks'])
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'passed')
        self.assertTrue(manifest['current_edit']['review_pages'])
        self.assertTrue(all(page['hash_matches'] for page in manifest['current_edit']['review_pages']))

    def test_subtitled_alias_is_verified_independently_of_good_original(self):
        self.final()
        (self.project / '成片_字幕版.mp4').write_bytes(b'corrupted subtitle render')
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['aliases']['original']['verification']['status'], 'passed')
        self.assertEqual(manifest['aliases']['subtitled']['verification']['status'], 'failed')
        self.assertFalse(manifest['media_verified'])
        self.assertFalse(manifest['ready_for_delivery'])

    def test_missing_decoder_is_unavailable_instead_of_false_success(self):
        self.final()
        with patch.dict('sys.modules', {'av': None}):
            manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['media']['status'], 'unavailable')
        self.assertFalse(manifest['media_verified'])

    def test_incomplete_scope_and_busy_state_never_claim_delivery_ready(self):
        self.complete_edit()
        write_json(self.project / 'state.json', {'status': 'ready', 'scope_complete': True, 'completed_uids': ['s1']})
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertTrue(manifest['media_verified'])
        self.assertEqual(manifest['scope'], 'selected_shots')
        self.assertFalse(manifest['ready_for_delivery'])
        write_json(self.project / 'state.json', {'status': 'complete'})
        self.busy = True
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertFalse(manifest['ready_for_delivery'])
        self.assertEqual(manifest['checks']['idle']['status'], 'failed')

    def test_shot_clips_are_listed_but_not_implicitly_decoded_or_final(self):
        clip = self.project / 'clips' / 's1.mp4'
        clip.parent.mkdir()
        shutil.copy2(self.video, clip)
        write_json(self.project / 'state.json', {'status': 'ready', 'scope_complete': True, 'completed_uids': ['s1'],
                   'shots_by_uid': {'s1': {'status': 'done', 'clip_relative': 'clips/s1.mp4',
                                          'render_contract': render_contract(self.story, self.story['shots'][0])}}})
        with patch('app.delivery.inspect_media', wraps=inspect_media) as media:
            manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertTrue(manifest['shot_clips'][0]['selected'])
        self.assertTrue(manifest['shot_clips'][0]['current_contract'])
        self.assertTrue(all(call.kwargs.get('verify') is False for call in media.call_args_list))
        self.assertEqual(manifest['checks']['media']['status'], 'unavailable')
        self.assertFalse(manifest['ready_for_delivery'])

    def test_corrupt_final_and_missing_audio_fail_actual_verification(self):
        (self.project / '成片.mp4').write_bytes(b'not an mp4')
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['media']['status'], 'failed')
        self.assertFalse(manifest['media_verified'])
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=24', '-an', '-c:v', 'libx264',
                         '-frames:v', '12', self.project / '成片.mp4'])
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['media']['status'], 'failed')
        self.assertFalse(manifest['aliases']['original']['media']['audio'])

    def test_audio_stream_ending_far_before_video_is_not_verified(self):
        target = self.project / '成片.mp4'
        pipeline.ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=24',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=0.1',
                         '-c:v', 'libx264', '-c:a', 'aac', '-frames:v', '12', '-t', '0.5', target])
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertFalse(manifest['media_verified'])
        self.assertEqual(manifest['checks']['media']['status'], 'failed')
        self.assertFalse(manifest['aliases']['original']['media']['audio_video_extents_match'])

    def test_recipe_or_source_tampering_never_promotes_recorded_report(self):
        folder = self.complete_edit()
        recipe = read_json(folder / 'recipe.json')
        recipe['width'] = 192
        write_json(folder / 'recipe.json', recipe)
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'failed')
        self.assertFalse(manifest['ready_for_delivery'])
        recipe['width'] = 96
        write_json(folder / 'recipe.json', recipe)
        (self.project / 'source_cache/snapshot.mp4').write_bytes(b'tampered source')
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertFalse(manifest['current_edit']['recorded_evidence']['source_hashes_match'])
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'failed')

    def test_current_story_change_makes_prior_evidence_stale(self):
        self.complete_edit()
        story = copy.deepcopy(self.story)
        story['shots'][0]['summary'] = 'different required composition'
        write_json(self.project / '分镜.json', story)
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertTrue(manifest['media_verified'])
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'failed')
        self.assertFalse(manifest['ready_for_delivery'])

    def test_stale_published_report_is_not_current_evidence(self):
        self.complete_edit()
        write_json(self.project / '媒体验收.json', {'edit_id': 'unrelated-old-version', 'passed': True})
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'failed')
        self.assertFalse(manifest['ready_for_delivery'])

    def test_actual_decoded_frames_must_match_recorded_version_spec(self):
        folder = self.complete_edit()
        report = read_json(folder / '媒体验收.json')
        report['expected_frames'] = 13
        write_json(folder / '媒体验收.json', report)
        completed = read_json(folder / 'completed.json')
        completed['files']['媒体验收.json'] = self.sha(folder / '媒体验收.json')
        write_json(folder / 'completed.json', completed)
        manifest = build_delivery(self.projects, 'project', verify=True)
        self.assertEqual(manifest['checks']['version_specification']['status'], 'failed')
        self.assertFalse(manifest['media_verified'])
        self.assertFalse(manifest['ready_for_delivery'])

    def test_verify_scope_excludes_historical_edits(self):
        self.complete_edit('old-version', review=False)
        self.complete_edit('current-version', review=False)
        with patch('app.delivery.inspect_media', wraps=inspect_media) as media:
            manifest = build_delivery(self.projects, 'project', verify=True)
        decoded_paths = [Path(call.args[0]) for call in media.call_args_list if call.kwargs.get('verify')]
        self.assertEqual(decoded_paths, [self.project / '成片.mp4'])
        self.assertEqual(len(manifest['edits']), 2)
        self.assertEqual(manifest['version_id'], 'current-version')

    def test_untrusted_artifact_paths_cannot_escape_or_inventory_arbitrary_files(self):
        folder = self.complete_edit()
        outside = self.root / 'outside.mp4'
        shutil.copy2(self.video, outside)
        write_json(self.project / 'state.json', {'status': 'ready', 'shots_by_uid': {'s1':
                   {'status': 'done', 'clip': str(outside), 'render_contract': render_contract(self.story, self.story['shots'][0])}}})
        write_json(folder / 'review/index.json', {'pages': [{'file': '../../private.png'}, {'file': str(outside)}]})
        manifest = build_delivery(self.projects, 'project')
        self.assertIsNone(manifest['shot_clips'][0]['artifact'])
        self.assertEqual(manifest['current_edit']['review_pages'], [])
        self.assertTrue(all(Path(item['local_path']).is_relative_to(self.project) for item in manifest['artifacts']))
        self.assertIn('INVALID_REVIEW_PAGE', [issue['code'] for issue in manifest['issues']])
        write_json(self.project / 'current_edit.json', {'id': '../outside'})
        manifest = build_delivery(self.projects, 'project')
        self.assertIsNone(manifest['version_id'])
        self.assertEqual(manifest['checks']['recorded_provenance']['status'], 'failed')

    def test_fingerprint_changes_when_real_artifact_bytes_change(self):
        self.final()
        original = build_delivery(self.projects, 'project')
        (self.project / '字幕.srt').write_text('first subtitle text', encoding='utf-8')
        updated = build_delivery(self.projects, 'project')
        self.assertNotEqual(original['fingerprint'], updated['fingerprint'])
        self.assertEqual(updated['fingerprint'], build_delivery(self.projects, 'project')['fingerprint'])


if __name__ == '__main__':
    unittest.main()
