import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import api
from app.finishing import load_recipe, readiness
from app.processes import run_process
from app.providers import Cancelled
from app.review import evidence, images_at
from app.skills import Skills
from app.storage import digest, read_json, write_json
from app.transfer import Transfer
from tests import test_ui_contracts as contracts


class ReadinessTests(unittest.TestCase):
    def test_engine_startup_keeps_all_writes_inside_workbench(self):
        import pipeline, requests
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'workbench';node=root/'nodes/ComfyUI-DramaFactory';node.mkdir(parents=True)
            (node/'__init__.py').write_text('NODE_CLASS_MAPPINGS = {}',encoding='utf-8')
            readonly=Path(directory)/'readonly-install'
            config={'comfy_url':'http://127.0.0.1:8188','python':sys.executable,'comfy_dir':str(readonly)}
            process=Mock();process.poll.return_value=None
            with patch.object(pipeline,'ROOT',root),patch.object(pipeline,'CONFIG',config),patch('pipeline.requests.get',side_effect=[requests.ConnectionError(),Mock()]),patch('pipeline.socket.socket') as socket,patch('pipeline.subprocess.Popen',return_value=process) as launch:
                socket.return_value.__enter__.return_value.connect_ex.return_value=1
                pipeline.ensure_comfy()
            args=launch.call_args.args[0];env=launch.call_args.kwargs['env']
            self.assertEqual(Path(args[args.index('--base-directory')+1]),root/'data/comfy-runtime')
            source_paths=root/'data/comfy-runtime/source_model_paths.yaml'
            self.assertTrue(source_paths.is_file())
            self.assertIn(str(readonly/'models'),source_paths.read_text(encoding='utf-8'))
            for name in ('TEMP','TMP','TMPDIR','NUMBA_CACHE_DIR','DRAMA_FACTORY_CACHE_DIR'):
                self.assertTrue(Path(env[name]).is_relative_to(root))
                self.assertTrue(Path(env[name]).is_dir())
            for flag in ('--input-directory','--output-directory','--temp-directory','--user-directory'):
                self.assertTrue(Path(args[args.index(flag)+1]).is_relative_to(root))
            self.assertIn('ComfyUI-DramaFactory-Runtime',args)
            self.assertTrue(args[args.index('--database-url')+1].endswith('/data/comfy-runtime/user/comfyui.db'))
            self.assertFalse(readonly.exists())

    def test_comfy_cache_uses_writable_runtime_and_rejects_escape(self):
        import ast
        from app.storage import ROOT
        source=ast.parse((ROOT/'nodes/ComfyUI-DramaFactory/__init__.py').read_text(encoding='utf-8'))
        functions=[node for node in source.body if isinstance(node,ast.FunctionDef) and node.name in ('cache_path','latent_path')]
        scope={'Path':Path,'os':os}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'node-cache','exec'),scope)
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'DRAMA_FACTORY_CACHE_DIR':directory}):
            for name in ('cache_path','latent_path'):
                self.assertTrue(scope[name]('drama/project/shot.safetensors').is_relative_to(Path(directory).resolve()))
                with self.assertRaises(ValueError):scope[name]('../../outside.safetensors')

    def test_video_download_uses_server_output_and_stops_before_writing(self):
        from app.comfyio import download_file
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def raise_for_status(self):pass
            def iter_content(self,size):yield b'actual server video'
        with tempfile.TemporaryDirectory() as directory,patch('app.comfyio.requests.get',return_value=Response()) as get:
            target=Path(directory)/'clip.mp4'
            item={'filename':'clip.mp4','subfolder':'custom','type':'output'}
            download_file(item,target,'http://localhost:8188','local-token')
            self.assertEqual(target.read_bytes(),b'actual server video')
            self.assertEqual(get.call_args.kwargs['params'],item)
            self.assertTrue(get.call_args.kwargs['stream'])
            checks=iter((False,False,True))
            with self.assertRaises(Cancelled):download_file(item,target,'http://localhost:8188',cancel=lambda:next(checks))
            self.assertEqual(target.read_bytes(),b'actual server video')
            self.assertFalse(list(Path(directory).glob('*.part')))

    def test_invalid_storyboard_does_not_create_ghost_project(self):
        with tempfile.TemporaryDirectory() as folder:
            projects, db, original = contracts.UIContractsTests().setup_project(folder)
            before = {p.name for p in original.parent.iterdir()}
            indexed = {p['id'] for p in projects.list()}
            for value in ('{broken', '{"title":"missing shots"}'):
                with self.assertRaises(ValueError):projects.create(value, {'input_mode':'storyboard'})
            self.assertEqual(before, {p.name for p in original.parent.iterdir()})
            self.assertEqual({p['id'] for p in projects.list()}, indexed)

    def test_render_contract_accepts_numeric_normalization_and_legacy_digest(self):
        from app.quality import render_contract, render_contract_matches, _render_data
        story={'characters':[],'shots':[]}
        shot={'uid':'s1','duration':4,'dialogue':[{'text':'原句'}]}
        old=digest(_render_data(story,shot))
        normalized={**shot,'duration':4.0}
        self.assertEqual(render_contract(story,shot),render_contract(story,normalized))
        self.assertTrue(render_contract_matches(old,story,normalized))
        self.assertFalse(render_contract_matches(old,story,{**normalized,'dialogue':[{'text':'改词'}]}))

    def test_missing_and_corrupt_projects_do_not_hide_healthy_projects(self):
        with tempfile.TemporaryDirectory() as folder:
            projects, db, healthy = contracts.UIContractsTests().setup_project(folder)
            corrupt = projects.create('坏记录', {})
            (corrupt/'state.json').write_text('{broken', encoding='utf-8')
            (corrupt/'分镜.json').write_text('{broken', encoding='utf-8')
            missing = Path(folder)/'offline-project';missing.mkdir();db.index(missing,'离线磁盘');missing.rmdir()
            projects.refresh()
            rows = {p['id']:p for p in projects.list()}
            self.assertTrue(rows[corrupt.name]['unavailable'])
            self.assertTrue(rows['offline-project']['unavailable'])
            self.assertFalse(rows[healthy.name].get('unavailable',False))
            self.assertEqual(projects.get(healthy.name)['title'],'A study scene')

    def test_saved_finishing_settings_validate_without_mutating_story_or_video(self):
        with tempfile.TemporaryDirectory() as folder:
            projects, db, project = contracts.UIContractsTests().setup_project(folder)
            story = projects.save_story(project.name, {'title':'故事','shots':[{'summary':'镜头'}]})
            original = (project/'分镜.json').read_bytes()
            (project/'成片.mp4').write_bytes(b'keep-current-film')
            with patch.object(api,'projects',projects):
                client=TestClient(api.app,base_url='http://localhost');base=f'/api/projects/{project.name}'
                payload={'edit_preset':'compact','review_interval':.25,'notes':[{'start':0,'end':1.5,'text':'说明'}],'masks':[]}
                self.assertEqual(client.post(base+'/finishing-settings',json=payload).status_code,200)
                self.assertEqual(projects.get(project.name)['finishing_settings'],payload)
                bad={**payload,'notes':payload['notes']*2}
                self.assertEqual(client.post(base+'/finishing-settings',json=bad).status_code,400)
                self.assertEqual(read_json(project/'finishing-settings.json'),payload)
                self.assertFalse(client.get(base+'/quality').json()['finishing']['ready'])
                db.enqueue(project.name,'render')
                self.assertEqual(client.post(base+'/finishing-settings',json=payload).status_code,400)
            self.assertEqual((project/'分镜.json').read_bytes(),original)
            self.assertEqual((project/'成片.mp4').read_bytes(),b'keep-current-film')

    def test_host_and_origin_are_checked_before_local_actions(self):
        client=TestClient(api.app,base_url='http://localhost')
        self.assertEqual(client.get('/').status_code,200)
        with patch.object(api.config,'set_key') as write_key:
            response=client.post('/api/key',json={'key':'fake'},headers={'host':'rebind.example','origin':'http://rebind.example'})
            self.assertEqual(response.status_code,403)
            response=client.post('/api/key',json={'key':'fake'},headers={'origin':'https://foreign.example'})
            self.assertEqual(response.status_code,403)
            write_key.assert_not_called()

    def test_cancel_terminates_and_reaps_only_owned_process(self):
        started=time.monotonic();children=[];real=subprocess.Popen
        def launch(*args,**kwargs):
            process=real(*args,**kwargs);children.append(process);return process
        with patch('app.processes.subprocess.Popen',side_effect=launch):
            with self.assertRaises(Cancelled):
                run_process([sys.executable,'-c','import time; time.sleep(10)'],capture_output=True,
                            cancel=lambda:time.monotonic()-started>.25,creationflags=0x08000000 if os.name=='nt' else 0)
        self.assertLess(time.monotonic()-started,3)
        self.assertIsNotNone(children[0].poll())

    def test_cpu_stop_never_requires_comfyui_connection(self):
        from app.jobs import Worker
        worker=object.__new__(Worker)
        worker.active={'project_id':'project','kind':'finish'}
        with patch('pipeline.api',side_effect=AssertionError('CPU stopping must not contact ComfyUI')):
            self.assertFalse(worker.interrupt_owned('project')['interrupted'])

    def test_review_pages_are_flushed_while_frames_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);seen=[];generated=0
            def frames(path,targets,cancel=None,on_image=None):
                nonlocal generated
                found={}
                for target in targets:
                    image=Image.new('RGB',(200,264))
                    if on_image:
                        generated+=1;on_image(target,image)
                    else:found[target]=image
                return found
            def sheet(items,path,columns):
                self.assertLessEqual(len(items),18)
                seen.append(generated);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'page')
            checks=[{'edited':{'frames':240},'preview_source':'source.mp4','plan':{'keep_frames':[[0,240]]}}]*20
            with patch('app.review.images_at',side_effect=frames),patch('app.review.sheet',side_effect=sheet):
                result=evidence(root,checks,[root/'clip.mp4']*20,.1)
            self.assertEqual(generated,2000)
            self.assertEqual(sum(p['items'] for p in result['pages'] if p['kind']=='frames'),2000)
            self.assertLess(seen[0],100)

    def test_portable_project_keeps_frozen_versions_and_saved_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            projects, db, project=contracts.UIContractsTests().setup_project(folder)
            story=projects.save_story(project.name,{'title':'迁移','shots':[{'summary':'one'}]})
            transfer=Transfer(projects.config,projects,Skills(Path(folder)/'skills'))
            settings={'edit_preset':'compact','review_interval':.25,'notes':[],'masks':[]}
            write_json(project/'finishing-settings.json',settings)
            write_json(project/'prompt_templates/tpl-test.json',{'id':'tpl-test','name':'样板','mode':'T2VA','cast':[],
                       'source_shot_uid':story['shots'][0]['uid'],'created_at':'2026-10-15 12:00:00','references':{},'sections':{}})
            source=project/'source_cache/source.mp4';source.parent.mkdir();source.write_bytes(b'original')
            recipe={'version':1,'story':story,'settings':settings,'sources':[{'file':'source_cache/source.mp4'}]}
            write_json(project/'edits/version-one/recipe.json',recipe)
            write_json(project/'edits/version-one/completed.json',{'files':{}})
            write_json(project/'edits/version-one/媒体验收.json',{'recipe_hash':digest(recipe)})
            (project/'edits/version-one/成片.mp4').write_bytes(b'film')
            (project/'edits/version-one/normal_000.mp4').write_bytes(b'unnecessary intermediate')
            write_json(project/'current_edit.json',{'id':'version-one'})
            full=transfer.export([project.name],True)
            with zipfile.ZipFile(full) as archive:
                self.assertFalse(any('normal_000' in name for name in archive.namelist()))
            restored=projects.path(transfer.import_package(full)['projects'][0])
            self.assertEqual(load_recipe(restored,'version-one'),recipe)
            self.assertEqual((restored/'source_cache/source.mp4').read_bytes(),b'original')
            self.assertEqual(read_json(restored/'finishing-settings.json'),settings)
            self.assertTrue((restored/'prompt_templates/tpl-test.json').exists())
            light=transfer.export([project.name],False)
            with zipfile.ZipFile(light) as archive:
                self.assertFalse(any('/edits/' in name or '/source_cache/' in name or name.endswith('/current_edit.json') for name in archive.namelist()))

    def test_streaming_export_detects_secret_across_chunk_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            projects,db,project=contracts.UIContractsTests().setup_project(folder)
            transfer=Transfer(projects.config,projects,Skills(Path(folder)/'skills'))
            projects.config.set_key('deepseek','boundary-private-token')
            source=project/'clip.mp4';source.write_bytes(b'x'*(1024*1024-8)+b'boundary-private-token')
            with zipfile.ZipFile(Path(folder)/'test.zip','w') as archive:
                with self.assertRaisesRegex(ValueError,'私密认证'):transfer.write_media(archive,'clip.mp4',source)


if __name__=='__main__':unittest.main()
