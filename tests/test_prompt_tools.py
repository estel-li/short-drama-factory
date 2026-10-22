import base64
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image

from app.assets import Assets
from app.config import ConfigStore
from app.content import BASE_FIELDS, REF_FIELDS, Content, keyframe_prefix
from app.contracts import ContractError, error_body
from app.database import Database
from app.projects import Projects
from app.prompt_tools import install_prompt_routes
from app.schemas import Options
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class PromptToolsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        self.config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/queue.sqlite3')
        root_patch = patch('app.projects.ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.projects = Projects(self.config, self.db)
        self.assets = Assets(self.config, self.projects)
        self.content = Content(self.config, Skills(), self.projects)
        self.services = SimpleNamespace(db=self.db, config=self.config, projects=self.projects,
                                        assets=self.assets, content=self.content)
        self.options = Options(input_mode='storyboard', auto_reference=False,
                               duration_rule='count', shot_count=1, total_seconds=4)
        self.project = self.projects.create('', self.options.model_dump(),
            {'title': 'Prompt compiler', 'characters': [{'id': 'hero', 'name': 'Hero', 'visual_description': 'A woman in a yellow coat.'}],
             'shots': [{'uid': 'one', 'summary': 'Look through the window.', 'duration': 4,
                        'characters': ['hero'], 'dialogue': [], 'mode': 'T2VA'}]})
        self.app = FastAPI()
        async def handle(request, exc):
            return JSONResponse(error_body(exc.code, str(exc), details=exc.details,
                                           next_actions=exc.next_actions), status_code=exc.status)
        self.app.add_exception_handler(ContractError, handle)
        install_prompt_routes(self.app, lambda: self.services)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.url = f'/api/v2/projects/{self.project.name}/shots/one/compile'

    def sections(self, mode='T2VA'):
        if mode == 'Ref2VA':
            return {key: '[Shot 1] A woman waits beside a window.' if key == 'detailed_description' else 'Quiet room.'
                    for key in REF_FIELDS}
        return {'integrated_multimodal_description': '[Shot 1] A woman waits beside a window.',
                'overall_soundscape': 'Quiet room. No dialogue.', 'non_diegetic_music': 'N/A'}

    def picture(self):
        data = io.BytesIO()
        Image.new('RGB', (8, 8), 'yellow').save(data, format='PNG')
        return self.assets.add_image(self.project.name, base64.b64encode(data.getvalue()).decode(), 'Hero', 'hero')

    def set_shot(self, **changes):
        story = self.projects.get(self.project.name)['story']
        story['shots'][0].update(changes)
        self.projects.save_story(self.project.name, story)

    def test_base_three_sections_return_revision_without_writes_or_provider(self):
        before = {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        revision = self.projects.revision(self.project.name)
        with patch('app.providers.LLMClient.generate', side_effect=AssertionError('provider called')), \
                patch.object(self.content, 'call', side_effect=AssertionError('text generated')), \
                patch.object(self.assets, 'materialize', side_effect=AssertionError('upload called')), \
                patch.object(self.db, 'enqueue', side_effect=AssertionError('queued')):
            response = self.client.post(self.url, json={'sections': self.sections()})
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(value['uid'], 'one')
        self.assertEqual(value['revision'], revision)
        self.assertEqual(value['mode'], 'T2VA')
        self.assertAlmostEqual(value['aligned_seconds'], 107 / 24)
        self.assertEqual(value['reference_labels'], [])
        self.assertTrue(value['prompt'].startswith(BASE_FIELDS[0] + ':'))
        self.assertEqual(before, {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob('*') if path.is_file()})
        self.assertEqual(self.db.jobs(), [])

    def test_reference_six_sections_use_actual_image_labels(self):
        asset = self.picture()
        self.set_shot(mode='Ref2VA', bindings={'images': [asset['id']]})
        sections = self.sections('Ref2VA')
        sections['subject_definitions'] = 'Hero from <Picture 1>, the only visible person.'
        response = self.client.post(self.url, json={'sections': sections})
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(value['mode'], 'Ref2VA')
        self.assertEqual(value['reference_labels'], [{'label': '<Picture 1>', 'source': 'image', 'asset_id': asset['id']}])
        offsets = [value['prompt'].index(field + ':') for field in REF_FIELDS]
        self.assertEqual(offsets, sorted(offsets))

    def test_keyframe_prefix_is_added_once_with_aligned_duration(self):
        asset = self.picture()
        self.set_shot(mode='L2VA', bindings={'last_frame': asset['id']})
        response = self.client.post(self.url, json={'sections': self.sections()})
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        expected = keyframe_prefix('L2VA', 107 / 24)
        self.assertEqual(value['prompt'].splitlines()[0], expected)
        self.assertEqual(value['prompt'].count(expected), 1)
        self.assertIn('4.46-second', expected)

    def test_missing_or_changed_dialogue_is_not_synthesized(self):
        self.set_shot(dialogue=[{'speaker': 'hero', 'text': '你好。'}])
        response = self.client.post(self.url, json={'sections': self.sections()})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['code'], 'PROMPT_INVALID')
        sections = self.sections()
        sections['integrated_multimodal_description'] += ' She says <d>[Chinese] 你好。</d>'
        self.assertEqual(self.client.post(self.url, json={'sections': sections}).status_code, 200)

    def test_missing_unknown_and_empty_sections_are_specific_errors(self):
        value = self.sections()
        value.pop('overall_soundscape')
        value['non_diegetic_music'] = ' '
        value['unexpected'] = 'not allowed'
        response = self.client.post(self.url, json={'sections': value})
        self.assertEqual(response.status_code, 422)
        error = response.json()
        self.assertEqual(error['code'], 'PROMPT_SECTIONS_INVALID')
        self.assertEqual(error['details'][0]['missing'], ['overall_soundscape'])
        self.assertEqual(error['details'][0]['unknown'], ['unexpected'])
        self.assertEqual(error['details'][0]['empty'], ['non_diegetic_music'])

    def test_existing_captured_reference_is_resolved_without_migration(self):
        self.options.auto_reference = True
        self.projects.save_options(self.project.name, self.options.model_dump())
        asset = self.picture()
        # Remove the explicit asset fallback so the renderer's captured source is used.
        write_json(self.project / 'assets.json', {})
        self.set_shot(mode='auto')
        write_json(self.project / 'references.json', {'hero': {'image': 'captured.png', 'shot_id': 0,
                   'local_file': asset['file'], 'sha256': 'stale-metadata'}})
        sections = self.sections('Ref2VA')
        sections['subject_definitions'] = 'Hero is defined by <Picture 1>.'
        before = (self.project / 'references.json').read_bytes()
        with patch('app.comfyio.upload_file', side_effect=AssertionError('upload called')):
            response = self.client.post(self.url, json={'sections': sections})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['mode'], 'Ref2VA')
        self.assertEqual((self.project / 'references.json').read_bytes(), before)

    def test_workflow_input_error_and_unknown_uid_are_actionable(self):
        self.options.profile = 'h3-audio-drive'
        self.projects.save_options(self.project.name, self.options.model_dump())
        response = self.client.post(self.url, json={'sections': self.sections()})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['code'], 'PROMPT_BINDINGS_INVALID')
        response = self.client.post(self.url.replace('/one/', '/unknown/'), json={'sections': self.sections()})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'SHOT_NOT_FOUND')


if __name__ == '__main__':
    unittest.main()
