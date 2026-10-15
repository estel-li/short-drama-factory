import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import api
from app.content import REF_FIELDS
from app.finishing import publish
from app.quality import render_contract
from app.storage import write_json, digest
from app.templates import listing,save_template,selected
from tests import test_ui_contracts as contracts


class ProductionContractsTests(unittest.TestCase):
    def test_template_requires_its_own_reference_base(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            prompt='\n'.join(name+':\n'+('<Subject 1> A' if i==0 else '[Shot 1] <Picture 1> <Picture 2> <Picture 3> <d>[Chinese]你好</d>' if name=='detailed_description' else 'N/A') for i,name in enumerate(REF_FIELDS))
            bindings={'images':[{'id':str(i),'type':'image','name':'scene' if i else 'A','sha256':str(i+1)*64,**({'character':'a'} if i==0 else {})} for i in range(3)]}
            shot={'id':1,'uid':'s1','characters':['a'],'duration':4,'prompt':prompt,'dialogue':[{'text':'你好'}],'compiled_mode':'Ref2VA','compiled_bindings':bindings}
            story={'characters':[{'id':'a','name':'A','visual_description':'red coat'}],'shots':[shot]}
            write_json(project/'state.json',{'shots_by_uid':{'s1':{'status':'done','render_contract':render_contract(story,shot)}}})
            value=save_template(project,story,shot,'单人三图基准');shot['prompt_template_id']=value['id']
            self.assertEqual(selected(project,shot,'Ref2VA',bindings)['sections']['subject_definitions'],'<Subject 1> A')
            self.assertEqual(len(listing(project)),1)
            changed=copy.deepcopy(bindings);changed['images'][2]['sha256']='f'*64
            with self.assertRaises(ValueError):selected(project,shot,'Ref2VA',changed)
            with self.assertRaises(ValueError):selected(project,shot,'I2VA',bindings)
            changed=copy.deepcopy(bindings);changed['images'][0]['character']='b'
            with self.assertRaises(ValueError):selected(project,shot,'Ref2VA',changed)

    def test_failed_preparation_preserves_all_existing_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'candidate';folder.mkdir()
            (root/'成片.mp4').write_bytes(b'old film');(root/'成片_字幕版.mp4').write_bytes(b'old captions')
            (folder/'成片.mp4').write_bytes(b'new film')
            with patch('app.finishing.shutil.copy2',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):publish(root,folder,['成片.mp4'])
            self.assertEqual((root/'成片.mp4').read_bytes(),b'old film')
            self.assertEqual((root/'成片_字幕版.mp4').read_bytes(),b'old captions')

    def test_quality_and_pilot_api_validate_before_queueing(self):
        with tempfile.TemporaryDirectory() as directory:
            projects,db,project=contracts.UIContractsTests().setup_project(directory)
            story=projects.save_story(project.name,{'title':'review','shots':[{'summary':'one'}]})
            calls=[]
            class Worker:
                def enqueue(self,*args):calls.append(args);return 'test-job'
            with patch.object(api,'projects',projects),patch.object(api,'worker',Worker()):
                client=TestClient(api.app, base_url='http://127.0.0.1');base='/api/projects/'+project.name
                self.assertTrue(client.get(base+'/quality').json()['preflight']['ready'])
                self.assertEqual(client.post(base+'/stage/render',json={'limit':True}).status_code,400)
                self.assertEqual(client.post(base+'/stage/render',json={'limit':0}).status_code,400)
                self.assertEqual(client.post(base+'/stage/render',json={'limit':1}).status_code,202)
                self.assertEqual(calls[-1][2]['limit'],1)
                self.assertEqual(client.post(base+'/finish',json={'edit_preset':'invalid'}).status_code,400)
                self.assertEqual(client.post(base+'/finish',json={'edit_preset':'compact','notes':[]}).status_code,400)
                self.assertEqual(client.post(base+'/edits/version-one/rebuild').status_code,400)
                self.assertEqual(len(calls),1)
                clip=project/'clip.mp4';clip.write_bytes(b'fixture for route provenance')
                write_json(project/'state.json',{'shots_by_uid':{story['shots'][0]['uid']:{'status':'done','clip':str(clip),'render_contract':render_contract(story,story['shots'][0])}}})
                self.assertEqual(client.post(base+'/finish',json={'edit_preset':'compact','notes':[]}).status_code,202)
                self.assertEqual(calls[-1][1],'finish')
                recipe={'version':1,'story':story,'width':160,'height':256,'settings':{},'sources':[]}
                write_json(project/'edits/version-one/recipe.json',recipe)
                write_json(project/'edits/version-one/completed.json',{'files':{}})
                write_json(project/'edits/version-one/媒体验收.json',{'recipe_hash':digest(recipe)})
                self.assertEqual(client.post(base+'/edits/version-one/rebuild').status_code,202)
                self.assertEqual(calls[-1][1],'rebuild-edit')


if __name__=='__main__':unittest.main()
