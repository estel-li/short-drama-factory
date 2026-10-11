import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import av
from PIL import Image

import pipeline
from app.assets import Assets
from app.config import ConfigStore
from app.content import BASE_FIELDS, Content, assemble_prompt
from app.continuity import extract_last_frame, materialize_frame, planned_frame, predecessor, validate_links
from app.database import Database
from app.projects import Projects
from app.schemas import Options, Shot
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class FirstFrameTests(unittest.TestCase):
    def setup(self, folder, count=2):
        root = Path(folder)
        write_json(root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        config = ConfigStore(root)
        db = Database(root / 'data/test.sqlite3')
        projects = Projects(config, db)
        options = Options(duration_rule='count', total_seconds=count * 4, shot_count=count, auto_reference=False)
        project = projects.create('同一书房，同一段连续动作。', options.model_dump())
        write_json(project / 'outline.json', {'premise': '同一书房连续动作'})
        return project, projects, Content(config, Skills(), projects), options, Assets(config, projects)

    def video(self, path, color='red', count=107):
        path.parent.mkdir(parents=True, exist_ok=True)
        width, height = pipeline.canvas(pipeline.CONFIG['profiles']['draft']['megapixels'], '9:16')
        pipeline.ffmpeg(['-f', 'lavfi', '-i', f'color=c={color}:s={width}x{height}:r=24',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                         '-c:v', 'libx264', '-bf', '2', '-c:a', 'aac', '-frames:v', str(count), '-t', str(count/24), path])
        return path

    def story(self):
        prompt = assemble_prompt({name: '[Shot 1] A quiet study.' for name in BASE_FIELDS}, 'T2VA', 107/24)
        return {'title': '首帧验证', 'characters': [], 'shots': [
            {'scene': '书房', 'continuity_group': 'study_day', 'summary': '看桌面', 'prompt': prompt},
            {'scene': '书房', 'continuity_group': 'study_day', 'summary': '接续移动', 'use_previous_last_frame': True,
             'first_frame_reason': '同机位连续动作', 'prompt': assemble_prompt({name:'[Shot 1] <Picture 1> continues.' for name in BASE_FIELDS}, 'I2VA', 107/24)}]}

    def test_defaults_strict_boolean_and_scene_boundaries(self):
        self.assertIs(Shot().use_previous_last_frame, False)
        for value in ('false', 'true', 0, 1):
            with self.assertRaises(ValueError): Shot(use_previous_last_frame=value)
        story = self.story()
        validate_links(story['shots'])
        with self.assertRaisesRegex(ValueError, '第一镜'): validate_links([story['shots'][1]])
        for key, value in [('scene', '街道'), ('continuity_group', 'study_night')]:
            invalid = copy.deepcopy(story['shots'])
            invalid[1][key] = value
            with self.assertRaisesRegex(ValueError, '同场景'): validate_links(invalid)
        story['shots'][1]['use_previous_last_frame'] = False
        story['shots'][1]['scene'] = '街道'
        validate_links(story['shots'])

    def test_ai_batch_boundary_and_locked_predecessor(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options, assets = self.setup(folder, 7)
            calls = []
            def generate(project, stage, options, data, schema, validate, status, cancel):
                calls.append(data)
                self.assertIn('use_previous_last_frame', data['instructions'])
                self.assertIs(schema['$defs']['Shot']['properties']['use_previous_last_frame']['default'], False)
                shots = [{'scene': '书房', 'continuity_group': 'continuous', 'summary': str(data['start_shot'] + i),
                          'use_previous_last_frame': data['start_shot'] + i > 1} for i in range(data['required_shots'])]
                return validate({'title': 'test', 'shots': shots}), {}
            content.call = generate
            result = content.storyboard(project, options, lambda s: None, lambda: False)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1]['previous_shots'][-1]['summary'], '6')
            self.assertTrue(result['shots'][6]['use_previous_last_frame'])
            result['shots'][0]['locked'] = True
            locked = projects.save_story(project.name, result)['shots'][0]
            again = content.storyboard(project, options, lambda s: None, lambda: False, reset=True)
            self.assertEqual(again['shots'][0], locked)

    def test_extract_exact_last_displayed_frame_with_b_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            clip = project / 'changing.mp4'
            pipeline.ffmpeg(['-f', 'lavfi', '-i', 'testsrc2=size=160x96:rate=24', '-c:v', 'libx264', '-bf', '3', '-frames:v', '29', clip])
            with av.open(str(clip)) as media:
                frames = list(media.decode(video=0))
                expected = frames[-1].to_image().tobytes()
            previous, shot = {'id': 1, 'uid': 'previous'}, {'id': 2, 'uid': 'current'}
            frame = extract_last_frame(project, shot, previous, clip)
            with Image.open(project / frame['file']) as image:
                self.assertEqual(image.tobytes(), expected)
            self.assertEqual(frame['frame_index'], 28)
            self.assertEqual((frame['width'], frame['height']), (160, 96))
            with patch('app.continuity.av.open', side_effect=AssertionError('cached extraction must be reused')):
                self.assertEqual(extract_last_frame(project, shot, previous, clip), frame)
            (project / frame['file']).write_bytes(b'corrupt')
            repaired = extract_last_frame(project, shot, previous, clip)
            self.assertEqual(repaired['sha256'], frame['sha256'])
            with self.assertRaises(ValueError): extract_last_frame(project, shot, previous, project.parent / 'outside.mp4')

    def test_prompt_planning_before_pixels_and_resume_without_llm(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options, assets = self.setup(folder)
            story = self.story()
            for shot in story['shots']: shot['prompt'] = ''
            story = projects.save_story(project.name, story)
            shot = story['shots'][1]
            # Existing user binding IDs are retained but ignored while the feature is on.
            shot['bindings'] = {'images': ['nonexistent'], 'last_frame': 'nonexistent'}
            virtual = assets.resolve(project, shot, story)
            self.assertEqual(set(virtual), {'first_frame'})
            options.h3_mode = 'Ref2VA'
            options.stages['prompt'].skill = 'h3-ref2va'
            calls = []
            def generate(project, stage, options, data, schema, validate, status, cancel, mode):
                calls.append(data)
                self.assertEqual(mode, 'I2VA')
                self.assertIn('first_frame_continuity', data)
                sid = 'h3-i2va'
                return validate({name:'[Shot 1] <Picture 1> continues moving.' for name in BASE_FIELDS}), {
                    'skill':content.skills.get(sid, full=False), 'input_hash':__import__('app.storage',fromlist=['digest']).digest(data),
                    'settings_hash':__import__('app.content',fromlist=['prompt_settings_hash']).prompt_settings_hash(options)}
            content.call = generate
            text = content.prompt_shot(project, story, shot, options, virtual, lambda s: None, lambda: False)
            self.assertTrue(text.startswith('For the target video, at 0.00'))
            actual = copy.deepcopy(virtual)
            actual['first_frame'].update(sha256='pixel-hash', file='assets/generated.png', comfy_file='uploaded.png')
            content.prompt_shot(project, story, shot, options, actual, lambda s: None, lambda: False)
            self.assertEqual(len(calls), 1)
            self.assertEqual(shot['compiled_mode'], 'I2VA')
            story['shots'][0]['action'] = 'different ending state'
            content.prompt_shot(project, story, shot, options, actual, lambda s: None, lambda: False)
            self.assertEqual(len(calls), 2)

    def test_false_flag_does_not_change_existing_prompt_snapshot_input(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options, assets = self.setup(folder)
            story = projects.save_story(project.name, {'title': 'old', 'shots': [{'summary': 'old'}]})
            shot = story['shots'][0]
            calls = []
            def generate(project, stage, options, data, schema, validate, status, cancel, mode):
                from app.storage import digest
                from app.content import prompt_settings_hash
                calls.append(data)
                return validate({name:'[Shot 1] quiet room' for name in BASE_FIELDS}), {
                    'skill':content.skills.get('h3-t2va', full=False), 'input_hash':digest(data), 'settings_hash':prompt_settings_hash(options)}
            content.call = generate
            shot.pop('use_previous_last_frame')
            shot.pop('first_frame_reason')
            content.prompt_shot(project, story, shot, options, {}, lambda s: None, lambda: False)
            shot.update(use_previous_last_frame=False, first_frame_reason='')
            content.prompt_shot(project, story, shot, options, {}, lambda s: None, lambda: False)
            self.assertEqual(len(calls), 1)

    def test_runner_sequential_graph_resume_and_upstream_invalidation(self):
        original = copy.deepcopy(pipeline.CONFIG)
        try:
            with tempfile.TemporaryDirectory() as folder:
                project, projects, content, options, assets = self.setup(folder)
                pipeline.CONFIG['comfy_dir'] = str(Path(folder) / 'comfy')
                pipeline.CONFIG['mode'] = 'existing'
                story = projects.save_story(project.name, self.story())
                source = self.video(Path(folder) / 'comfy/output/test.mp4')
                submitted = []
                def api(path, data=None):
                    if path == '/queue': return {'queue_running': [], 'queue_pending': []}
                    if path == '/prompt':
                        submitted.append(copy.deepcopy(data['prompt']))
                        return {'prompt_id': str(len(submitted))}
                    return {}
                def runner():
                    value = pipeline.Runner(project)
                    value.encode = lambda graph, shot, signature: graph
                    value.sample = lambda graph, shot, signature: graph
                    value.wait = lambda prompt_id: {'filename':'test.mp4','subfolder':'','type':'output'}
                    return value
                with patch('pipeline.ensure_comfy'), patch('pipeline.validate_graph'), patch('pipeline.api', side_effect=api), patch('pipeline.assemble', return_value=project/'成片.mp4'):
                    first = runner()
                    first.run()
                    self.assertEqual(len(submitted), 2)
                    graph = submitted[1]
                    self.assertEqual(graph['7']['class_type'], 'MiniMaxH3ImageToVideo')
                    self.assertIn('first_frame', graph['7']['inputs'])
                    self.assertNotIn('last_frame', graph['7']['inputs'])
                    frame = read_json(project / 'state.json')['shots']['2']['first_frame']
                    self.assertEqual(frame['source_clip_sha256'], hashlib.sha256(Path(read_json(project/'state.json')['shots']['1']['clip']).read_bytes()).hexdigest())
                    self.assertTrue((Path(pipeline.CONFIG['comfy_dir']) / 'input' / graph['71']['inputs']['image']).is_file())
                    runner().run()
                    self.assertEqual(len(submitted), 2, 'resume should reuse both clips')
                    previous_clip = Path(read_json(project/'state.json')['shots']['1']['clip'])
                    self.video(previous_clip, color='blue')
                    runner().run()
                    self.assertEqual(len(submitted), 3, 'changing previous video must rerender dependent shot only')
                    self.assertNotEqual(submitted[-1]['71']['inputs']['image'], graph['71']['inputs']['image'])
                    story['shots'][1]['locked'] = True
                    projects.save_story(project.name, story)
                    self.video(previous_clip, color='green')
                    with self.assertRaisesRegex(RuntimeError, '已锁定'): runner().run()
        finally:
            pipeline.CONFIG.clear()
            pipeline.CONFIG.update(original)

    def test_disabled_modes_keep_original_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options, assets = self.setup(folder)
            for mode, bindings in [('T2VA',{}), ('I2VA',{'first_frame':{}}), ('FL2VA',{'first_frame':{'id':'a'},'last_frame':{'id':'b'}}),
                                   ('L2VA',{'last_frame':{'id':'a'}}), ('Ref2VA',{'images':[{'id':'a'}]})]:
                if mode == 'I2VA': bindings = {'first_frame':{'id':'a'}}
                self.assertEqual(content.mode({'mode':mode, 'use_previous_last_frame':False}, options, bindings), mode)
            with self.assertRaisesRegex(ValueError, '不能降级'):
                options.missing_reference = 'text'
                content.mode({'use_previous_last_frame':True}, options, {})

    def test_reorder_uses_immediate_previous_identity_and_rejects_first(self):
        with tempfile.TemporaryDirectory() as folder:
            project, projects, content, options, assets = self.setup(folder)
            story = self.story()
            story['shots'].insert(1, {'scene':'书房','continuity_group':'study_day','summary':'另一镜'})
            story = projects.save_story(project.name, story)
            current = story['shots'][2]
            self.assertEqual(predecessor(current, story)['uid'], story['shots'][1]['uid'])
            story['shots'][0], story['shots'][1] = story['shots'][1], story['shots'][0]
            reordered = projects.save_story(project.name, story)
            self.assertEqual(predecessor(current, reordered)['uid'], reordered['shots'][1]['uid'])
            reordered['shots'].insert(0, reordered['shots'].pop(2))
            with self.assertRaisesRegex(ValueError, '第一镜'): projects.save_story(project.name, reordered)

    def test_remote_upload_sends_exact_frame_and_does_not_store_token(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            clip = self.video(project/'clip.mp4')
            asset = extract_last_frame(project, {'id':2,'uid':'current'}, {'id':1,'uid':'previous'}, clip)
            def upload(url, files, data, headers, timeout):
                self.assertEqual(url, 'https://comfy.test/upload/image')
                self.assertEqual(hashlib.sha256(files['image'][1].read()).hexdigest(), asset['sha256'])
                self.assertEqual(headers['Authorization'], 'Bearer test-local-token')
                self.assertEqual(data['type'], 'input')
                class Response:
                    def raise_for_status(self): pass
                    def json(self): return {'subfolder':'uploaded/frames','name':'frame.png'}
                return Response()
            with patch('app.continuity.requests.post', side_effect=upload):
                result = materialize_frame(project, asset, {'mode':'remote','comfy_url':'https://comfy.test','comfy_auth_token':'test-local-token'})
            self.assertEqual(result['comfy_file'], 'uploaded/frames/frame.png')
            self.assertNotIn('test-local-token', str(result))
            self.assertNotIn('test-local-token', (project/'assets/first_frames.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
