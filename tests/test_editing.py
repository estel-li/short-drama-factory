import copy
import tempfile
import unittest
from pathlib import Path

from app.config import ConfigStore
from app.content import Content, prompt_valid
from app.database import Database
from app.processes import InstanceLock
from app.projects import Projects
from app.providers import Cancelled
from app.schemas import Options, Story
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class EditingTests(unittest.TestCase):
    def setup_project(self, folder, count=7):
        root = Path(folder)
        write_json(root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        config = ConfigStore(root)
        projects = Projects(config, Database(root / 'data/test.sqlite3'))
        options = Options(duration_rule='count', total_seconds=count * 4, shot_count=count)
        project = projects.create('A simple story', options.model_dump())
        write_json(project / 'outline.json', {'premise': 'A simple story'})
        content = Content(config, Skills(), projects)
        return project, projects, content, options

    def test_storyboard_recovers_completed_batch_and_retains_locked_shot(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options = self.setup_project(folder)
            calls = []
            def generate(project, stage, options, data, schema, validate, status, cancel):
                calls.append(data['start_shot'])
                if calls == [1, 7]:
                    raise Cancelled('Interrupted between batches')
                story = {'title': 'test', 'characters': [], 'shots': [
                    {'id': data['start_shot'] + i, 'summary': str(data['start_shot'] + i), 'duration': 4} for i in range(data['required_shots'])]}
                return validate(story), {'input': data['start_shot']}
            content.call = generate
            with self.assertRaises(Cancelled):
                content.storyboard(project, options, lambda message: None, lambda: False)
            first = read_json(project / 'storyboard_partial.json')['story']['shots'][0]['uid']
            story = content.storyboard(project, options, lambda message: None, lambda: False)
            self.assertEqual(calls, [1, 7, 7])
            self.assertEqual(story['shots'][0]['uid'], first)
            story['shots'][0].update(locked=True, action='Exact user edit')
            saved = projects.save_story(project.name, story)
            locked = copy.deepcopy(saved['shots'][0])
            regenerated = content.storyboard(project, options, lambda message: None, lambda: False, reset=True)
            self.assertEqual(regenerated['shots'][0], locked)

    def test_reorder_keeps_identity_and_user_prompt_survives_compiler(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options = self.setup_project(folder, count=2)
            text = 'integrated_multimodal_description:\n[Shot 1] A quiet room.\noverall_soundscape:\nRain.\nnon_diegetic_music:\nN/A'
            story = projects.save_story(project.name, {'title': 'test', 'shots': [{'summary': 'one', 'prompt': text}, {'summary': 'two', 'prompt': text}]})
            original = {s['uid']: s['seed_offset'] for s in story['shots']}
            story['shots'].reverse()
            story = projects.save_story(project.name, story)
            self.assertEqual({s['uid']: s['seed_offset'] for s in story['shots']}, original)
            content.call = lambda *a, **k: self.fail('Manual prompt must not invoke an LLM')
            self.assertEqual(content.prompt_shot(project, story, story['shots'][0], options, {}, lambda message: None, lambda: False), text)
            story['shots'][0]['action'] = 'Changed action'
            changed = projects.save_story(project.name, story)
            self.assertEqual(changed['shots'][0]['prompt'], '')

    def test_invalid_dialogue_or_missing_reference_is_rejected(self):
        text = 'subject_definitions:\n<Picture 1> A girl\nsummary:\nScene\nretention_analysis:\nFace\ndetailed_description:\n[Shot 1] She waves.\noverall_soundscape:\nWind\nnon_diegetic_music:\nN/A'
        with self.assertRaises(ValueError):
            prompt_valid(text, 'Ref2VA', {'images': [{}], 'videos': [{}]})
        with self.assertRaises(ValueError):
            prompt_valid(text, 'Ref2VA', {'images': [{}]}, [{'text': '你好'}])

    def test_single_worker_lock_prevents_second_service(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = InstanceLock(Path(folder) / 'worker.lock'), InstanceLock(Path(folder) / 'worker.lock')
            first.acquire()
            try:
                with self.assertRaises(RuntimeError):
                    second.acquire()
            finally:
                first.release()
            second.acquire()
            second.release()


if __name__ == '__main__':
    unittest.main()
