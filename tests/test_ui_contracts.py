import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import ConfigStore
from app.database import Database
from app.projects import Projects
from app.schemas import Options, durations
from app.storage import ROOT, read_json, write_json


class UIContractsTests(unittest.TestCase):
    def test_workbench_assets_do_not_reuse_stale_cached_modules(self):
        from app import api
        from fastapi.testclient import TestClient
        client = TestClient(api.app, base_url='http://127.0.0.1')
        for path in ('/', '/web/main.js', '/web/options.js?v=2.3.1', '/web/style.css'):
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            if response.headers.get('etag'):
                conditional = client.get(path, headers={'If-None-Match': response.headers['etag']})
                self.assertEqual(conditional.headers['Cache-Control'], 'no-store')

    def test_irrelevant_duration_controls_do_not_block_selected_rule(self):
        plan = durations(Options(duration_rule='count', shot_seconds=12, total_seconds=8, shot_count=2))
        self.assertEqual(plan['durations'], [4, 4])
        self.assertEqual(durations(Options(duration_rule='manual', shot_seconds=12, manual_durations=[4, 6]))['durations'], [4, 6])
        with self.assertRaises(ValueError): durations(Options(duration_rule='total', shot_seconds=12))

    def setup_project(self, folder):
        root=Path(folder)
        write_json(root/'config.default.json', read_json(ROOT/'config.default.json'))
        config=ConfigStore(root)
        db=Database(root/'data/test.sqlite3')
        projects=Projects(config, db)
        project=projects.create('A study scene', {}, None)
        return projects,db,project

    def test_project_busy_is_authoritative_for_queued_and_running_jobs(self):
        with tempfile.TemporaryDirectory() as folder:
            projects,db,project=self.setup_project(folder)
            self.assertFalse(projects.get(project.name)['busy'])
            db.enqueue(project.name,'plan')
            self.assertTrue(projects.get(project.name)['busy'])
            self.assertTrue(next(p for p in projects.list() if p['id']==project.name)['busy'])
            job=db.claim();self.assertTrue(projects.get(project.name)['busy'])
            db.update(job['id'],'review','done');self.assertFalse(projects.get(project.name)['busy'])

    def test_settings_change_does_not_keep_completed_status_or_stale_final(self):
        with tempfile.TemporaryDirectory() as folder:
            projects,db,project=self.setup_project(folder)
            projects.save_story(project.name, {'title':'story','shots':[{'summary':'one'}]})
            write_json(project/'state.json',{'status':'complete','shots':{}})
            (project/'成片.mp4').write_bytes(b'previous video')
            options=projects.options(project).model_dump();options['seed']+=1
            projects.save_options(project.name,options)
            state=read_json(project/'state.json')
            self.assertEqual(state['status'],'ready');self.assertTrue(state['updated_at'])
            self.assertFalse((project/'成片.mp4').exists())

    def test_story_validation_is_read_only_and_errors_do_not_echo_input(self):
        from app import api
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            projects,db,project=self.setup_project(folder)
            story=projects.save_story(project.name, {'title':'story','shots':[{'summary':'one'}]})
            before=(project/'分镜.json').read_bytes()
            with patch.object(api,'projects',projects):
                client=TestClient(api.app, base_url='http://127.0.0.1')
                response=client.post('/api/projects/'+project.name+'/validate-story',json={'story':{'title':'new','shots':[{'summary':'new'}]}})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.json()['shots'][0]['uid'])
                response=client.post('/api/projects/'+project.name+'/validate-story',json={'story':{'title':'new','characters':{'private':'do-not-echo'},'shots':[{}]}})
                self.assertEqual(response.status_code,400)
                self.assertIn('人物列表',response.json()['error'])
                self.assertNotIn('do-not-echo',response.json()['error'])
            self.assertEqual((project/'分镜.json').read_bytes(),before)

    def test_refresh_keeps_readable_draft_and_episode_titles(self):
        with tempfile.TemporaryDirectory() as folder:
            projects,db,project=self.setup_project(folder)
            projects.refresh()
            self.assertEqual(projects.get(project.name)['title'],'A study scene')
            write_json(project/'episode.json',{'series_title':'远方来信','number':1,'plan':{'title':'第一集：来信'}})
            projects.refresh()
            self.assertEqual(projects.get(project.name)['title'],'远方来信 · 第一集：来信')
            self.assertEqual(next(p for p in projects.list() if p['id']==project.name)['title'],'远方来信 · 第一集：来信')

    def test_outline_edit_archives_stale_final_and_preserves_locked_story(self):
        from app import api
        with tempfile.TemporaryDirectory() as folder:
            projects,db,project=self.setup_project(folder)
            old={'title':'old','premise':'old premise','beats':[{'description':'old beat'}],'ending':''}
            write_json(project/'outline.json',old)
            story=projects.save_story(project.name, {'title':'old','shots':[{'summary':'locked','locked':True}]})
            write_json(project/'state.json', {'status':'complete','stages':{'outline':{'status':'done'},'storyboard':{'status':'done'},'prompt':{'status':'done'}},'shots':{}})
            (project/'成片.mp4').write_bytes(b'previous video')
            (project/'字幕.srt').write_text('old subtitle',encoding='utf-8')
            class Worker:
                def invalidate(self, folder, names, reason):
                    for name in names:
                        value=read_json(folder/name)
                        projects.version(folder,reason,value)
                        if any(s.get('locked') for s in value['shots']):write_json(folder/'storyboard_locked.json',value)
                        (folder/name).unlink()
            new={**old,'premise':'edited premise'}
            with patch.object(api,'projects',projects),patch.object(api,'worker',Worker()):
                self.assertEqual(api.outline_save(project.name,new),new)
            self.assertFalse((project/'成片.mp4').exists())
            self.assertFalse((project/'字幕.srt').exists())
            self.assertEqual(next((project/'takes').rglob('成片.mp4')).read_bytes(),b'previous video')
            self.assertEqual(read_json(project/'storyboard_locked.json'),story)
            state=read_json(project/'state.json')
            self.assertEqual(state['status'],'review');self.assertNotIn('storyboard',state['stages']);self.assertNotIn('prompt',state['stages'])


if __name__ == '__main__': unittest.main()
