"""Upgrade, semantic edit, and per-line narration regressions."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import ConfigStore
from app.content import compatible_prompt_hashes
from app.database import Database
from app.finishing import collect_clips, readiness
from app.projects import Projects
from app.quality import _render_data, render_contract, render_contract_matches, shot_dependencies, story_report
from app.schemas import Options, Story
from app.storage import ROOT, digest, read_json, write_json


class StoryUpgradeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'test.sqlite3')
        with patch('app.projects.ROOT', self.root):
            self.projects = Projects(self.config, self.db)

    def fixture(self, locked=False, legacy=False):
        project = self.projects.create('review', {}, None)
        story = self.projects.save_story(project.name, {
            'title': 'definitions',
            'scenes': [{'id': 'room', 'name': 'room', 'description': 'red room'},
                       {'id': 'street', 'name': 'street', 'description': 'empty street'}],
            'props': [{'id': 'box', 'name': 'box', 'description': 'red box'}],
            'shots': [{'uid': 's1', 'scene': 'room', 'scene_id': 'room', 'props': ['box'],
                       'prompt': 'OLD RED PROMPT', 'locked': locked}],
        })
        clip = project / 'clip.mp4'
        clip.write_bytes(b'fixture for provenance only')
        contract = digest(_render_data(story, story['shots'][0])) if legacy else render_contract(story, story['shots'][0])
        write_json(project / 'state.json', {'shots_by_uid': {'s1': {
            'status': 'done', 'clip': str(clip), 'render_contract': contract,
        }}})
        return project, story

    def test_legacy_scene_default_and_integer_duration_remain_usable(self):
        project, _ = self.fixture()
        old = self.projects.normalize(project.name, {'title': 'legacy', 'shots': [{'uid': 's1', 'dialogue': [{'speaker': '', 'text': 'hello'}]}]})
        old['shots'][0].pop('scene_id')
        old['shots'][0]['dialogue'][0].pop('narration')
        old['shots'][0]['duration'] = 4
        receipt = digest(_render_data(old, old['shots'][0]))
        write_json(project / '分镜.json', old)
        state = read_json(project / 'state.json')
        state['shots_by_uid']['s1']['render_contract'] = receipt
        write_json(project / 'state.json', state)
        (project / '成片.mp4').write_bytes(b'keep existing final')
        normalized = self.projects.get(project.name)['story']
        self.assertTrue(readiness(project, normalized)['ready'])
        self.assertEqual(len(collect_clips(project, normalized)), 1)
        saved = self.projects.save_story(project.name, normalized)
        self.assertEqual((project / '成片.mp4').read_bytes(), b'keep existing final')
        self.assertTrue(readiness(project, saved)['ready'])
        self.assertTrue(read_json(project / 'state.json')['shots_by_uid']['s1']['render_contract'].startswith('v2:'))
        changed = copy.deepcopy(saved)
        changed['shots'][0]['dialogue'][0]['text'] = 'different words'
        self.assertFalse(render_contract_matches(receipt, changed, changed['shots'][0]))

    def test_360_empty_scene_receipt_and_false_narration_are_compatible(self):
        story = Story.model_validate({'title': 'legacy', 'shots': [{'uid': 's1', 'dialogue': [{'text': 'hello'}]}]}).model_dump()
        old = copy.deepcopy(story)
        old['shots'][0]['dialogue'][0].pop('narration')
        receipt = digest(_render_data(old, old['shots'][0]))
        self.assertTrue(render_contract_matches(receipt, story, story['shots'][0]))
        self.assertEqual(render_contract(old, old['shots'][0]), render_contract(story, story['shots'][0]))
        story['shots'][0]['dialogue'][0]['narration'] = True
        self.assertFalse(render_contract_matches(receipt, story, story['shots'][0]))

    def test_definition_changes_invalidate_legacy_clips_across_repeated_saves(self):
        for collection in ('scenes', 'props'):
            with self.subTest(collection=collection):
                project, story = self.fixture(legacy=True)
                story[collection][0]['description'] = 'blue replacement'
                saved = self.projects.save_story(project.name, story)
                self.assertEqual(saved['shots'][0]['prompt'], '')
                self.assertEqual(read_json(project / 'state.json')['changed_shots'], ['s1'])
                self.assertFalse(readiness(project, saved)['ready'])
                saved = self.projects.save_story(project.name, saved)
                self.assertFalse(readiness(project, saved)['ready'])
                with self.assertRaisesRegex(ValueError, '重生成'):
                    collect_clips(project, saved)

    def test_locked_definition_edit_is_rejected_and_unrelated_edit_stays_usable(self):
        project, story = self.fixture(locked=True)
        changed = copy.deepcopy(story)
        changed['scenes'][0]['description'] = 'blue room'
        with self.assertRaisesRegex(ValueError, '解锁'):
            self.projects.save_story(project.name, changed)
        self.assertEqual(read_json(project / '分镜.json'), story)
        story['scenes'][1]['description'] = 'rainy street'
        saved = self.projects.save_story(project.name, story)
        self.assertEqual(saved['shots'][0]['prompt'], 'OLD RED PROMPT')
        self.assertTrue(readiness(project, saved)['ready'])

    def test_new_receipts_track_definition_changes_without_a_save(self):
        _, story = self.fixture()
        receipt = render_contract(story, story['shots'][0])
        story['props'][0]['description'] = 'blue box'
        self.assertFalse(render_contract_matches(receipt, story, story['shots'][0]))

    def test_voiceover_survives_save_and_does_not_exempt_ordinary_dialogue(self):
        project = self.projects.create('voiceover', {'narration': True}, None)
        raw = {'title': 'voiceover', 'characters': [{'id': 'a', 'name': 'Alice', 'visual_description': 'red coat', 'voice_description': 'soft'}],
               'shots': [{'uid': 's1', 'dialogue': [{'speaker': 'Alice', 'text': 'Hello.', 'narration': True}]}]}
        saved = self.projects.save_story(project.name, raw)
        restored = self.projects.get(project.name)['story']
        self.assertTrue(restored['shots'][0]['dialogue'][0]['narration'])
        self.assertTrue(story_report(restored, Options(narration=True))['ready'])
        self.assertFalse(story_report(restored, Options(narration=False))['ready'])
        self.assertEqual(shot_dependencies(restored, restored['shots'][0])['voiceover_characters'][0]['voice_description'], 'soft')
        receipt = render_contract(saved, saved['shots'][0])
        restored['characters'][0]['voice_description'] = 'deep'
        self.assertFalse(render_contract_matches(receipt, restored, restored['shots'][0]))
        restored['shots'][0]['dialogue'][0]['narration'] = False
        self.assertFalse(story_report(restored, Options(narration=True))['ready'])

    def test_legacy_prompt_hashes_only_ignore_semantically_empty_defaults(self):
        old = {'shot': {'dialogue': [{'speaker': 'Alice', 'text': 'Hello.'}]}, 'scenes': []}
        current = copy.deepcopy(old)
        current['shot']['scene_id'] = ''
        current['shot']['dialogue'][0]['narration'] = False
        self.assertIn(digest(old), compatible_prompt_hashes(current))
        current['shot']['dialogue'][0]['narration'] = True
        self.assertNotIn(digest(old), compatible_prompt_hashes(current))
        linked_old = {'shot': {'dialogue': [], 'use_previous_last_frame': True},
                      'first_frame_continuity': {'previous_shot': {'scene_id': None}}}
        linked_current = copy.deepcopy(linked_old)
        linked_current['shot']['scene_id'] = ''
        linked_current['first_frame_continuity']['previous_shot']['scene_id'] = ''
        self.assertIn(digest(linked_old), compatible_prompt_hashes(linked_current))


if __name__ == '__main__':
    unittest.main()
