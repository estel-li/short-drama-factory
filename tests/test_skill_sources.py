import hashlib
import tempfile
import unittest
from pathlib import Path

from app.content import keyframe_prefix, prompt_valid, reference_labels
from app.skills import Skills
from app.storage import ROOT, read_json
from launcher.seed_resources import seed


class SourceSkillTests(unittest.TestCase):
    def test_bundled_sources_are_complete_exact_and_loaded(self):
        skills = Skills(ROOT / 'resources/builtin_skills')
        entries = skills.list()
        self.assertEqual(len(entries), 17)
        self.assertEqual([sum(s['stage'] == stage for s in entries) for stage in ('outline','storyboard','prompt')], [4,4,5])
        variables = {'style':'水彩绘本','genre':'治愈','duration':4.46,'language':'Chinese','music':'N/A','mode':'T2VA','purpose':'general','ratio':'1:1'}
        for entry in entries:
            value = skills.get(entry['id'])
            for source in value['sources']:
                path = skills.root / entry['id'] / source['local_file']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source['sha256'], str(path))
            rendered, snapshot = skills.render(entry['id'], entry['stage'], variables)
            self.assertEqual(snapshot['loaded_files'][-1], 'SKILL.md')
            self.assertFalse(any('/licenses/' in path for path in snapshot['loaded_files']))
            # Verify the actual upstream contents, not just source metadata, reach the request context.
            for path in entry['context_references']:
                self.assertIn(value['files'][path], rendered)
        with tempfile.TemporaryDirectory() as folder:
            seed(folder)
            seeded = Skills(Path(folder) / 'skills')
            self.assertEqual(seeded.get('h3-ref2va')['files'], skills.get('h3-ref2va')['files'])

    def test_reference_numbers_follow_native_video_soundtrack_order(self):
        bindings = {'images':[{'id':'girl'}], 'videos':[{'id':'with-voice','include_audio':True},{'id':'silent','include_audio':False}], 'audios':[{'id':'voice'}]}
        labels = reference_labels('Ref2VA', bindings)
        self.assertEqual([x['label'] for x in labels], ['<Picture 1>','<Audio 1>','<Video 1>','<Video 2>','<Audio 2>'])
        self.assertEqual(labels[-1]['asset_id'], 'voice')
        prompt = 'subject_definitions:\n<Picture 1> girl <Video 1> movement <Video 2> view <Audio 1> original <Audio 2> voice\nsummary:\n[reference generation]\nretention_analysis:\nreference\ndetailed_description:\n[Shot 1] girl\noverall_soundscape:\nrain\nnon_diegetic_music:\nN/A'
        self.assertEqual(prompt_valid(prompt,'Ref2VA',bindings),prompt)
        with self.assertRaises(ValueError):
            prompt_valid(prompt.replace('<Audio 2>',''),'Ref2VA',bindings)

    def test_keyframe_instruction_uses_real_aligned_end_time(self):
        body = 'integrated_multimodal_description: [Shot 1] A woman opens an umbrella.\noverall_soundscape: Rain.\nnon_diegetic_music: N/A'
        for mode in ('I2VA','FL2VA','L2VA'):
            valid = keyframe_prefix(mode,107/24)+'\n\n'+body
            prompt_valid(valid,mode,{},strict_keyframes=True,seconds=107/24)
            with self.assertRaises(ValueError):
                prompt_valid(body,mode,{},strict_keyframes=True,seconds=107/24)
        self.assertIn('4.46-second',keyframe_prefix('L2VA',107/24))


if __name__ == '__main__':
    unittest.main()
