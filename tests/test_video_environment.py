import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from app.config import ConfigStore
from app.storage import ROOT,read_json,write_json
from app.video_environment import VideoWorkflowEnvironment,WorkflowDownloadRequired


class VideoEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        write_json(self.root/'config.default.json',read_json(ROOT/'config.default.json'))
        self.config=ConfigStore(self.root)
        self.environment=VideoWorkflowEnvironment(self.config)
        self.probe=patch.object(self.environment,'probe',return_value={});self.probe.start()
        self.addCleanup(self.probe.stop);self.addCleanup(self.temp.cleanup)
        self.content=b'test-pdd-model'
        for f in self.environment.manifest['models'].values():
            f.update(size=len(self.content),sha256=hashlib.sha256(self.content).hexdigest())

    def existing(self):
        for role in ('pdd_fl','pdd_ref','upscaler'):
            f=self.environment.manifest['models'][role]
            path=self.root/'models/video-workflows'/f['category']/f['name']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.content)
        for plugin in self.environment.manifest['plugins'].values():
            folder=self.root/'data/comfy-runtime/custom_nodes'/plugin['name']
            folder.mkdir(parents=True,exist_ok=True);(folder/'__init__.py').write_text('# fixture',encoding='utf-8')
            write_json(folder/'factory-source.json',{'revision':plugin['revision']})

    def test_download_is_not_started_without_matching_plan_consent(self):
        plan=self.environment.plan('pdd-8')
        self.assertTrue(plan['requires_confirmation'])
        with patch('app.video_environment.Downloader.fetch') as fetch:
            with self.assertRaises(WorkflowDownloadRequired):
                self.environment.prepare('pdd-8',lambda *a,**k:None,lambda:False)
            fetch.assert_not_called()

    def test_local_models_are_verified_and_reused_without_network_download(self):
        self.existing()
        plan=self.environment.plan('pdd-upscale')
        self.assertFalse(plan['requires_confirmation'])
        self.assertEqual({f['action'] for f in plan['models']},{'verify'})
        with patch('app.video_environment.Downloader.fetch') as fetch:
            self.environment.prepare('pdd-upscale',lambda *a,**k:None,lambda:False)
            fetch.assert_not_called()
        self.assertTrue((self.root/'data/video-workflow-paths.yaml').is_file())
        self.assertEqual({f['action'] for f in self.environment.plan('pdd-upscale')['models']},{'verified'})

    def test_failed_local_checksum_requires_new_download_consent(self):
        self.existing()
        f=self.environment.manifest['models']['pdd_fl']
        (self.root/'models/video-workflows'/f['category']/f['name']).write_bytes(b'x'*len(self.content))
        with patch('app.video_environment.Downloader.fetch') as fetch:
            with self.assertRaises(WorkflowDownloadRequired) as error:
                self.environment.prepare('pdd-8',lambda *a,**k:None,lambda:False)
            self.assertTrue(error.exception.plan['requires_confirmation'])
            fetch.assert_not_called()

    def test_native_recipe_needs_no_optional_assets_and_unknown_profile_is_rejected(self):
        self.assertTrue(self.environment.plan('draft')['ready'])
        with self.assertRaises(ValueError):self.environment.plan('../outside')

    def test_receipts_do_not_require_write_access_to_shared_model_folders(self):
        self.existing()
        for f in self.environment.manifest['models'].values():
            if f['category']!='pdd_acc':continue
            target=self.root/'models/video-workflows'/f['category']/f['name']
            before=target.read_bytes()
            self.assertEqual(before,self.content)
        with patch('app.video_environment.Downloader.verified',side_effect=PermissionError('read-only shared models')):
            self.environment.prepare('pdd-upscale',lambda *a,**k:None,lambda:False)
        self.assertEqual(len(list((self.root/'data/video-model-verification').glob('*.json'))),3)
        self.assertFalse(list((self.root/'models').rglob('*.verified.json')))


if __name__=='__main__':unittest.main()
