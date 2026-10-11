import copy
import itertools
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.config import ConfigStore
from app.assets import Assets
from app.content import BASE_FIELDS, REF_FIELDS, Content, assemble_prompt, prompt_valid
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.providers import Cancelled, LLMClient, ProviderError
from app.schemas import Options, Provider
from app.series import Series
from app.storage import ROOT, read_json, write_json


class RetryTests(unittest.TestCase):
    def client(self, handler, stream=False):
        provider = Provider(id='cloud', name='test', base_url='https://example.test', model='test', stream=stream)
        client = LLMClient(provider)
        client.client = lambda: httpx.Client(transport=httpx.MockTransport(handler))
        return client

    def test_default_three_retries_and_permanent_errors(self):
        for status, expected in [(503, 4), (429, 4), (401, 1), (402, 1), (400, 1)]:
            calls = []
            client = self.client(lambda request: calls.append(request) or httpx.Response(status))
            with patch('app.providers.time.monotonic', side_effect=itertools.count(0, 50)):
                with self.assertRaises(ProviderError): client.generate([{'role':'user','content':'test'}])
            self.assertEqual(len(calls), expected)

    def test_network_recovery_and_stream_partial_is_discarded(self):
        calls = []
        def handler(request):
            calls.append(request)
            if len(calls) == 1: raise httpx.ReadTimeout('test', request=request)
            if len(calls) == 2:
                return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n')
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"complete"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
        client = self.client(handler, True)
        with patch('app.providers.time.monotonic', side_effect=itertools.count(0, 10)):
            result = client.generate([{'role':'user','content':'test'}])
        self.assertEqual(result['text'], 'complete')
        self.assertEqual(len(calls), 3)

    def test_retry_wait_can_be_cancelled(self):
        client = self.client(lambda request: httpx.Response(503))
        cancel = iter([False, True])
        with self.assertRaises(Cancelled):
            client.generate([{'role':'user','content':'test'}], cancel=lambda:next(cancel))

    def test_sections_are_assembled_and_mode_confusion_rejected(self):
        sections = {name: '正文' for name in REF_FIELDS}
        sections['detailed_description'] = '[Shot 1] <Picture 1> girl'
        value = assemble_prompt(sections, 'Ref2VA', 6.58)
        self.assertEqual(prompt_valid(value, 'Ref2VA', {'images':[{}]}), value)
        with self.assertRaisesRegex(ValueError, '当前 Ref2VA'):
            assemble_prompt({name:'I2VA body' for name in BASE_FIELDS}, 'Ref2VA', 6.58)
        for mode in ('I2VA', 'L2VA', 'FL2VA'):
            value = assemble_prompt({name:'[Shot 1] action' for name in BASE_FIELDS},mode,107/24)
            prompt_valid(value,mode,{},strict_keyframes=True,seconds=107/24)

    def test_format_repair_honors_setting_and_saves_causes(self):
        with tempfile.TemporaryDirectory() as folder:
            config = ConfigStore(folder)
            skills = type('Skills', (), {'render':lambda self,*args:('format rules',{'id':'outline-hook'})})()
            content = Content(config, skills, None)
            responses = [{'text':'{}','model':'test','usage':{}}]*3 + [{'text':'{"ok":true}','model':'test','usage':{}}]
            def validate(value):
                if value.get('ok') is not True: raise ValueError('missing ok')
                return value
            with patch.object(LLMClient, 'generate', side_effect=responses) as request:
                value, snapshot = content.call(Path(folder), 'outline', Options(), {}, {}, validate, lambda _:None, lambda:False)
            self.assertTrue(value['ok']);self.assertEqual(request.call_count,4)
            self.assertEqual(snapshot['format_attempts'],4)
            self.assertEqual(len(list((Path(folder)/'requests').glob('*_validation*.json'))),3)
            self.assertLessEqual(len(request.call_args.args[0]),4)


class SeriesTests(unittest.TestCase):
    def setup_series(self, folder, content=None):
        config = ConfigStore(folder)
        settings = config.get()
        settings['environment']['profiles'] = {'draft':{'label':'draft','megapixels':.4,'steps':4}}
        config.save(settings)
        db = Database(Path(folder)/'queue.sqlite3')
        projects = Projects(config,db)
        return Series(config,db,projects,content), projects, db

    def test_batch_order_atomicity_idempotency_and_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            series, projects, db = self.setup_series(folder)
            sid,_ = series.create({'mode':'manual','episodes':[{'input':'第一集'},{'input':'第二集'}]})
            value=series.get(sid);pids=[e['project_id'] for e in value['episodes']]
            self.assertEqual(len(set(pids)),2)
            ids=series.enqueue_batch(sid,kind='plan',batch_id='batch-one')
            self.assertEqual(series.enqueue_batch(sid,kind='plan',batch_id='batch-one'),ids)
            with self.assertRaises(ValueError):series.enqueue_batch(sid,kind='all')
            self.assertEqual(len(db.jobs()),2)
            first=db.claim();self.assertEqual(first['project_id'],pids[0])
            db.recover();self.assertEqual(db.claim()['id'],first['id'])
            db.update(first['id'],'done');self.assertEqual(db.claim()['project_id'],pids[1])
            series.stop(sid);self.assertTrue(db.cancelled(ids[1]))
            self.assertTrue((projects.path(pids[1])/'.stop').exists())

    def test_automatic_planning_resumes_without_duplicate_episodes(self):
        calls=[]
        character={'id':'girl','name':'女孩','visual_description':'blue dress','voice_description':'soft'}
        def call(*args):
            data,validate=args[3],args[5];numbers=data['required_numbers'];calls.append(numbers)
            if len(calls)==2:raise ProviderError('transient test failure')
            plan={'title':'雨伞','premise':'归家','characters':[character],'episodes':[{'number':n,'title':f'第{n}集','premise':f'推进{n}', 'beats':[{'description':f'事件{n}'}], 'ending':f'结束{n}','characters':['girl']} for n in numbers]}
            return validate(plan),{}
        with tempfile.TemporaryDirectory() as folder:
            series,projects,db=self.setup_series(folder,type('Content',(),{'call':staticmethod(call)})())
            sid,_=series.create({'mode':'auto','input':'整剧故事','episode_count':7})
            with self.assertRaises(ProviderError):series.plan(sid,lambda _:None,lambda:False)
            self.assertEqual(series.get(sid)['completed_plans'],6)
            series.plan(sid,lambda _:None,lambda:False)
            value=series.get(sid);pids=[e['project_id'] for e in value['episodes']]
            series.plan(sid,lambda _:None,lambda:False)
            self.assertEqual(calls,[list(range(1,7)),[7],[7]])
            self.assertEqual([e['project_id'] for e in series.get(sid)['episodes']],pids)
            context=read_json(projects.path(pids[-1])/'episode.json')
            self.assertEqual(context['characters'],[character]);self.assertEqual(context['number'],7)
            self.assertEqual(len(context['previous_plans']),2)
            real=Content(series.config,None,projects)
            previous=real.episode_context(projects.path(pids[-1]))
            self.assertEqual(previous['previous_episode_outlines'][-1]['premise'],'推进6')

    def test_episode_validation_has_no_partial_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            series,projects,db=self.setup_series(folder)
            before = {s['id'] for s in series.list()}
            for count in (None,0,101,3.5):
                with self.assertRaises(ValueError):series.create({'mode':'auto','input':'整剧','episode_count':count})
            with self.assertRaises(ValueError):series.create({'mode':'manual','episodes':[{'input':'有效'},{'input':''}]})
            self.assertEqual({s['id'] for s in series.list()}, before)

    def test_shared_reference_is_copied_and_resolved_in_next_episode(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            series,projects,db=self.setup_series(folder)
            sid,_=series.create({'mode':'manual','characters':[{'id':'girl','name':'女孩','visual_description':'blue dress'}],
                                 'episodes':[{'input':'第一集'},{'input':'第二集'}]})
            pids=[e['project_id'] for e in series.get(sid)['episodes']]
            first,second=map(projects.path,pids)
            (first/'assets').mkdir();Image.new('RGB',(8,8),'blue').save(first/'assets/girl.png')
            write_json(first/'references.json',{'girl':{'local_file':'assets/girl.png','shot_id':1}})
            series.inherit_references(second)
            result=Assets(series.config,projects).resolve(second,{'characters':['girl']},{})
            self.assertEqual(len(result['images']),1)
            copied=second/result['images'][0]['file']
            self.assertEqual(copied.read_bytes(),(first/'assets/girl.png').read_bytes())
            series.inherit_references(second)
            self.assertEqual(len(read_json(second/'assets.json')),1)

    def test_worker_enforces_each_batch_failure_policy(self):
        for policy in ('continue','stop'):
            with tempfile.TemporaryDirectory() as folder:
                series,projects,db=self.setup_series(folder)
                worker=Worker(db,series.config,projects,None,None)
                sid,_=worker.series.create({'mode':'manual','fail_policy':policy,'episodes':[{'input':'第一集'},{'input':'第二集'}]})
                pids=[e['project_id'] for e in worker.series.get(sid)['episodes']]
                ids=worker.series.enqueue_batch(sid,kind='plan')
                def execute(job):
                    if job['project_id']==pids[0]:raise ProviderError('simulated exhausted retries')
                    write_json(projects.path(job['project_id'])/'state.json',{'status':'ready','message':'规划完成'})
                    return 'done'
                worker.execute=execute
                with patch('app.jobs.ROOT',Path(folder)):
                    try:
                        worker.start();deadline=time.monotonic()+5
                        while time.monotonic()<deadline and any(j['status'] in ('queued','running') for j in db.jobs()):time.sleep(.02)
                    finally:
                        worker.shutdown.set();worker.wake.set();worker.thread.join(2)
                statuses={j['id']:j['status'] for j in db.jobs()}
                self.assertEqual(statuses[ids[0]],'error')
                self.assertEqual(statuses[ids[1]],'done' if policy=='continue' else 'paused')
                if policy=='stop':self.assertEqual(worker.series.get(sid)['episodes'][1]['status'],'paused')


if __name__ == '__main__':
    unittest.main()
