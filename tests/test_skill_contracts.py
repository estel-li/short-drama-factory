"""Guard the application-level skill contract against the drift found in review.

These checks cover the live skills/ directory (not only the bundled copy), the repeated blocks
that used to be maintained in several places at once, and the render limits that made some
saved packages impossible to render.
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

from app.content import BASE_FIELDS, REF_FIELDS, keyframe_prefix
from app.quality import dialogue_budget, spoken_units
from app.schemas import Shot, Story
from app.skills import MAX_SKILL_TEXT, Skills, strip_front_matter
from app.storage import ROOT

STAGES = ('outline', 'storyboard', 'prompt', 'image_prompt')
VARIABLES = {
    'outline': {'style': '水彩', 'genre': '治愈', 'duration': '24.00', 'language': 'Chinese', 'music': 'N/A'},
    'storyboard': {'style': '水彩', 'genre': '治愈', 'duration': '24.00', 'language': 'Chinese', 'music': 'N/A'},
    'prompt': {'style': '水彩', 'genre': '治愈', 'duration': '24.00', 'language': 'Chinese', 'music': 'N/A', 'mode': 'T2VA'},
    'image_prompt': {'style': '水彩', 'purpose': 'general', 'ratio': '9:16'},
}


def render_all(root):
    skills = Skills(root)
    for entry in skills.list():
        yield entry, skills.render(entry['id'], entry['stage'], VARIABLES[entry['stage']])


class LiveSkillContractTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'skills'

    def test_live_skills_match_the_bundled_copy(self):
        bundled = ROOT / 'resources/builtin_skills'
        live = Skills(self.root).list()
        self.assertEqual(len(live), 17)
        manifest = json.loads((ROOT / 'resources/builtin_skills.json').read_text(encoding='utf-8'))
        # Rebuilding used to emit only the 13 reviewed profiles and silently drop the image skills.
        self.assertEqual(sorted(manifest['ids']), sorted(s['id'] for s in live))
        for entry in live:
            folder, reference = self.root / entry['id'], bundled / entry['id']
            self.assertTrue((reference / 'metadata.json').is_file(), entry['id'])
            for path in folder.rglob('*'):
                if path.is_file():
                    other = reference / path.relative_to(folder)
                    self.assertTrue(other.is_file(), str(path))
                    self.assertEqual(path.read_bytes(), other.read_bytes(), str(path))

    def test_every_skill_renders_and_stays_under_the_cap(self):
        for entry, (text, snapshot) in render_all(self.root):
            self.assertLessEqual(len(text), MAX_SKILL_TEXT, entry['id'])
            self.assertEqual(snapshot['loaded_files'][-1], 'SKILL.md')
            self.assertFalse(text.lstrip().startswith('---'), entry['id'])

    def test_h3_skills_request_the_schema_fields_not_a_prompt_wrapper(self):
        for entry, (text, _) in render_all(self.root):
            if entry['stage'] != 'prompt':
                continue
            self.assertNotIn('{"prompt"', text, entry['id'])
            for name in (REF_FIELDS if entry['id'] == 'h3-ref2va' else BASE_FIELDS):
                self.assertIn(name, text, entry['id'])

    def test_ref2va_documents_its_six_sections_and_has_no_alignment_line(self):
        text, _ = Skills(self.root).render('h3-ref2va', 'prompt',
                                           {**VARIABLES['prompt'], 'mode': 'Ref2VA'})
        for marker in ('subject_definitions', 'retention_analysis', 'fully_preserved',
                       'attribute_transfer', '[unclear]', '[reference generation]'):
            self.assertIn(marker, text)
        # Ref2VA emits no first/last-frame line, so it must not inherit the keyframe wording.
        self.assertEqual(keyframe_prefix('Ref2VA', 8.0), '')
        self.assertNotIn('尾帧对齐指令将该时长', text)

    def test_first_frame_rules_are_not_duplicated_into_skills(self):
        for entry, (text, _) in render_all(self.root):
            self.assertNotIn('首帧功能（工作台 2.2）', text, entry['id'])

    def test_no_skill_injects_an_empty_mode_or_unknown_placeholders(self):
        for entry, (text, _) in render_all(self.root):
            self.assertNotIn('实际 H3 模式：。', text, entry['id'])
            self.assertNotIn('实际 H3 模式：。\n', text, entry['id'])
            self.assertFalse(re.search(r'\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}', text), entry['id'])

    def test_outline_and_storyboard_do_not_mention_the_dropped_upstream_workflow(self):
        for entry, (text, _) in render_all(self.root):
            self.assertNotIn('ai-video-storyboard', text, entry['id'])
            if entry['stage'] == 'storyboard':
                for ghost in ('begin_state', 'end_state', 'keyframe_description', 'continuity_notes'):
                    self.assertNotIn(ghost, text, entry['id'])


class SkillRuntimeGuardTests(unittest.TestCase):
    def test_relative_links_resolve_inside_each_package(self):
        """A skill's own SKILL.md must not link to a reference file that is not in the package.

        Upstream prose may cite files the application deliberately did not bundle (that is recorded
        in metadata.sources); what must never dangle is the adapter's own index of loaded files.
        """
        missing = []
        for folder in sorted(p for p in (ROOT / 'skills').iterdir() if p.is_dir()):
            metadata = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
            body = (folder / 'SKILL.md').read_text(encoding='utf-8', errors='ignore')
            for link in re.findall(r'\]\(([^)#:]+\.(?:md|txt))\)', body):
                if not (folder / link).is_file():
                    missing.append(f'{folder.name}/SKILL.md -> {link}')
            for relative in metadata.get('context_references', []):
                self.assertTrue((folder / relative).is_file(), f'{folder.name}/{relative}')
        self.assertEqual([], missing)

    def test_front_matter_is_not_sent_to_the_model(self):
        self.assertEqual('body', strip_front_matter('---\nname: x\n---\n\nbody'))
        self.assertEqual('plain', strip_front_matter('plain'))

    def test_save_rejects_a_package_that_cannot_render(self):
        with tempfile.TemporaryDirectory() as folder:
            skills = Skills(Path(folder) / 'skills')
            # Each file stays under the 100KB per-file gate, but the combined render is over the cap.
            heavy = '中' * 32_000
            self.assertLess(len(heavy.encode()), 100_000)
            with self.assertRaises(ValueError):
                skills.save('big', {'name': 'big', 'stage': 'outline'},
                            {'SKILL.md': 'x', 'a.md': heavy, 'b.md': heavy})

    def test_placeholder_values_are_substituted_once(self):
        with tempfile.TemporaryDirectory() as folder:
            skills = Skills(Path(folder) / 'skills')
            skills.save('once', {'name': 'once', 'stage': 'outline'}, {'SKILL.md': '风格={{style}}'})
            text, _ = skills.render('once', 'outline', {'style': '{{style}} 混搭'})
            self.assertEqual('风格={{style}} 混搭', text)

    def test_a_broken_package_does_not_break_the_manager_list(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'skills'
            (root / 'ok').mkdir(parents=True)
            (root / 'ok' / 'SKILL.md').write_text('ok', encoding='utf-8')
            (root / 'ok' / 'metadata.json').write_text(
                json.dumps({'id': 'ok', 'name': 'ok', 'stage': 'outline'}), encoding='utf-8')
            (root / 'broken').mkdir()
            (root / 'broken' / 'metadata.json').write_text(
                json.dumps({'id': 'broken', 'name': 'bad', 'stage': 'outline',
                            'references': ['missing.md']}), encoding='utf-8')
            (root / 'broken' / 'SKILL.md').write_text('bad', encoding='utf-8')
            self.assertEqual(['ok'], [s['id'] for s in Skills(root).list()])


class ShotSchemaTests(unittest.TestCase):
    def test_mode_is_restricted_to_real_h3_modes(self):
        for value in ('auto', 'T2VA', 'Ref2VA'):
            Story.model_validate({'title': 't', 'shots': [{'mode': value}]})
        for value in ('I2V', 'fl2va', 'T2VA ', ''):
            with self.assertRaises(Exception, msg=value):
                Story.model_validate({'title': 't', 'shots': [{'mode': value}]})

    def test_scene_id_is_a_first_class_field(self):
        shot = Shot.model_validate({'scene_id': 'SC-1'})
        self.assertEqual('SC-1', shot.scene_id)
        self.assertIn('scene_id', Shot.model_fields)


class EnglishDialogueBudgetTests(unittest.TestCase):
    def test_an_english_line_fits_a_normal_shot(self):
        line = 'I never expected you to come back so soon, honestly.'
        # Counting letters made this 41 units (> 8s) and blocked every English project.
        self.assertLess(dialogue_budget([{'text': line}])['required_seconds'], 8)

    def test_chinese_counting_is_unchanged(self):
        self.assertEqual(4, spoken_units('我回来了。'))
        self.assertEqual(0, spoken_units(''))


if __name__ == '__main__':
    unittest.main()
