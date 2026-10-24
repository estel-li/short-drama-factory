import copy
import tempfile
import unittest
from pathlib import Path

from app.config import ConfigStore
from app.content import BASE_FIELDS, REF_FIELDS, Content, prompt_valid
from app.database import Database
from app.projects import Projects
from app.quality import dialogue_budget, fitted_duration, pack_dialogue, prompt_cast_valid, script_dialogue, story_report
from app.schemas import Options
from app.skills import Skills
from app.storage import read_json,write_json,ROOT


def prompt(lines):
    return '\n'.join(f'{field}:\n' + ('[Shot 1] ' + ' '.join('<d>[Chinese] ' + text + '</d>' for text in lines) if i == 0 else 'N/A') for i, field in enumerate(BASE_FIELDS))


class QualityTests(unittest.TestCase):
    def test_dialogue_is_exact_ordered_and_counted(self):
        dialogue = [{'text': '你好。'}, {'text': '你好。'}, {'text': '走吧！'}]
        prompt_valid(prompt(['你好。', '你好。', '走吧！']), 'T2VA', {}, dialogue)
        for lines in (['你好。', '走吧！'], ['你好。', '你好。', '走吧！', '再见。'], ['走吧！', '你好。', '你好。'], ['你好。你好。', '走吧！'], ['你好。', '你好。', '走！']):
            with self.assertRaises(ValueError): prompt_valid(prompt(lines), 'T2VA', {}, dialogue)
        with self.assertRaises(ValueError): prompt_valid(prompt(['多余台词']), 'T2VA', {}, [])
        with self.assertRaises(ValueError): prompt_valid(prompt(['你好。']).replace('</d>', ''), 'T2VA', {}, [{'text':'你好。'}])

    def test_packing_preserves_each_line_and_uses_the_budget(self):
        lines = [{'speaker':'王','text':'一二三四五六七八九十。'} for _ in range(49)]
        groups = pack_dialogue(lines)
        self.assertEqual([line for group in groups for line in group['dialogue']], lines)
        self.assertTrue(all(4 <= group['duration'] <= 8 and len(group['dialogue']) <= 3 for group in groups))
        self.assertEqual(len(groups), 17)
        budget = dialogue_budget(lines[:3])
        self.assertAlmostEqual(budget['required_seconds'], .4 + 30/5.6 + .6 + .55, places=4)
        self.assertGreater(fitted_duration(lines[:3], Options()), 4)
        self.assertEqual(fitted_duration([], Options(), 6), 6)
        long_line = [{'text':'长'*100}]
        self.assertEqual(pack_dialogue(long_line), [{'dialogue':long_line, 'duration':8}])
        self.assertEqual(fitted_duration(long_line, Options()), 8)
        self.assertEqual(fitted_duration(long_line, Options(allow_long_shots=True)), 15)

    def test_estimated_dialogue_overflow_is_advisory(self):
        line = {'speaker':'a', 'text':'快'*30}
        story = {'characters':[{'id':'a', 'name':'甲'}],
                 'shots':[{'id':1, 'uid':'s1', 'duration':4, 'characters':['a'], 'dialogue':[line]}]}
        report = story_report(story, Options())
        self.assertTrue(report['ready'])
        self.assertGreater(report['shots'][0]['required_seconds'], 4)
        self.assertEqual([(issue['kind'], issue['severity']) for issue in report['issues']],
                         [('dialogue_overflow', 'warning')])
        self.assertEqual(story['shots'][0]['dialogue'], [line])

    def test_identity_and_speaker_issues_are_not_hidden_by_valid_media(self):
        story = {'characters':[{'id':'wang','name':'小王','visual_description':'blue uniform, round glasses, short hair'},
                               {'id':'lin','name':'小林','visual_description':'blue uniform, round glasses, long hair'}],
                 'shots':[{'id':1,'uid':'s1','duration':4,'characters':['wang'],'dialogue':[{'speaker':'小林','text':'长'*30}]}]}
        report = story_report(story, Options())
        self.assertFalse(report['ready'])
        self.assertEqual({item['kind'] for item in report['issues']}, {'similar_cast','dialogue_overflow','offscreen_speaker'})
        with self.assertRaises(ValueError): prompt_cast_valid('',story,story['shots'][0],{'images':[{'character':'lin'}]},'Ref2VA')
        value = '\n'.join(field+':\n'+ ('<Subject 1> 小王; <Subject 2> 小林 fully_preserved' if i==0 else '[Shot 1] <Picture 1>') for i,field in enumerate(REF_FIELDS))
        with self.assertRaises(ValueError): prompt_cast_valid(value,story,story['shots'][0],{},'Ref2VA')

    def test_character_change_only_invalidates_its_dependent_prompts(self):
        with tempfile.TemporaryDirectory() as folder:
            config = ConfigStore(folder)
            # Seed a portable default config without borrowing machine settings.
            value=config.get();value['environment']['profiles']={'draft':{'label':'draft','megapixels':.4,'steps':4}};config.save(value)
            projects=Projects(config,Database(Path(folder)/'queue.sqlite3'))
            project=projects.create('story',{},None)
            story={'title':'story','characters':[{'id':'a','name':'A','visual_description':'red coat'}, {'id':'b','name':'B','visual_description':'blue dress'}],
                   'shots':[{'uid':'s1','characters':['a'],'prompt':prompt([])}, {'uid':'s2','characters':['b'],'prompt':prompt([])}]}
            original=projects.save_story(project.name,story)
            updated=copy.deepcopy(original);updated['characters'][0]['visual_description']='green coat, square glasses'
            result=projects.save_story(project.name,updated)
            self.assertEqual(result['shots'][0]['prompt'],'')
            self.assertNotIn('prompt_manual',result['shots'][0])
            self.assertEqual(result['shots'][1],original['shots'][1])

    def test_authoritative_49_lines_drive_real_storyboard_batches(self):
        source='\n'.join('[王] 一二三四五六七八九十。' for _ in range(49))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);write_json(root/'config.default.json',read_json(ROOT/'config.default.json'))
            config=ConfigStore(root);projects=Projects(config,Database(root/'queue.sqlite3'))
            options=Options(input_mode='script',dialogue_timing='fit')
            project=projects.create(source,options.model_dump())
            content=Content(config,Skills(),projects);calls=[]
            content.outline(project,options,lambda _:None,lambda:False)
            def call(project,stage,options,data,schema,validate,status,cancel):
                calls.append(data['required_shots'])
                return validate({'title':'台词预算','characters':[{'id':'wang','name':'王','visual_description':'red coat and square glasses'}],
                                 'shots':[{'characters':['wang'],'dialogue':[{'speaker':'wang','text':line['text']} for line in group['dialogue']]} for group in data['assigned_dialogue_groups']]}),{}
            content.call=call
            result=content.storyboard(project,options,lambda _:None,lambda:False)
            self.assertEqual(calls,[6,6,5])
            self.assertEqual(len(result['shots']),17)
            self.assertEqual([{'speaker':'王','text':line['text']} for shot in result['shots'] for line in shot['dialogue']],script_dialogue(source))
            self.assertTrue(all(4<=shot['duration']<=8 for shot in result['shots']))

    def test_storyboard_accepts_scene_timing_and_preserves_fixed_durations(self):
        base = {'duration_rule':'count', 'shot_count':1, 'total_seconds':4}
        cases = [
            ('scene', {**base, 'dialogue_timing':'fit'}, '4.25', 4.25),
            ('fixed', {**base, 'dialogue_timing':'fixed'}, 7, 4),
            ('manual', {'duration_rule':'manual', 'manual_durations':[4.5]}, 7, 4.5),
            ('estimate', base, None, fitted_duration([{'text':'快'*30}], Options())),
            ('long-shot', {**base, 'allow_long_shots':True}, 9, 9),
            ('unsupported-long-shot', base, 9, None),
        ]
        for name, settings, chosen, expected in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);write_json(root/'config.default.json',read_json(ROOT/'config.default.json'))
                config=ConfigStore(root);projects=Projects(config,Database(root/'queue.sqlite3'))
                options=Options(**settings);project=projects.create('决斗中快速反击',options.model_dump())
                content=Content(config,Skills(),projects)
                content.outline(project,options,lambda _:None,lambda:False)
                def call(project,stage,options,data,schema,validate,status,cancel):
                    self.assertTrue(data['dialogue_pacing']['advisory'])
                    shot={'characters':['a'], 'dialogue':[{'speaker':'a','text':'快'*30}]}
                    if chosen is not None:
                        shot['duration']=chosen
                    return validate({'title':'快速反击', 'characters':[{'id':'a','name':'甲','visual_description':'red coat'}],
                                     'shots':[shot]}),{}
                content.call=call
                if expected is None:
                    with self.assertRaisesRegex(ValueError, '超过单镜 8 秒'):
                        content.storyboard(project,options,lambda _:None,lambda:False)
                    continue
                result=content.storyboard(project,options,lambda _:None,lambda:False)
                self.assertEqual(result['shots'][0]['duration'], expected)
                self.assertEqual(result['shots'][0]['dialogue'][0]['text'], '快'*30)

    def test_long_original_line_is_not_rejected_by_text_estimate(self):
        source='[王] '+'长'*100
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);write_json(root/'config.default.json',read_json(ROOT/'config.default.json'))
            config=ConfigStore(root);projects=Projects(config,Database(root/'queue.sqlite3'))
            options=Options(input_mode='script',dialogue_timing='fit')
            project=projects.create(source,options.model_dump());content=Content(config,Skills(),projects)
            content.outline(project,options,lambda _:None,lambda:False)
            def call(project,stage,options,data,schema,validate,status,cancel):
                return validate({'title':'原句保留','characters':[{'id':'wang','name':'王','visual_description':'red coat'}],
                                 'shots':[{'characters':['wang'],'duration':7.5,
                                           'dialogue':[{'speaker':'wang','text':line['text']} for line in group['dialogue']]}
                                          for group in data['assigned_dialogue_groups']]}),{}
            content.call=call
            result=content.storyboard(project,options,lambda _:None,lambda:False)
            self.assertEqual(result['shots'][0]['duration'], 7.5)
            self.assertEqual(result['shots'][0]['dialogue'][0]['text'], '长'*100)
            report=read_json(project/'出片预检.json')
            self.assertTrue(report['ready'])
            self.assertTrue(any(issue['kind']=='dialogue_overflow' for issue in report['issues']))


if __name__ == '__main__': unittest.main()
