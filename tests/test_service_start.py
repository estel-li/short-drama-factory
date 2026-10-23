import os
import runpy
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json
from launcher import start


class ServiceStartTests(unittest.TestCase):
    def test_explicit_queue_only_claims_authorized_job_and_leaves_old_work_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / 'config.default.json', read_json(ROOT / 'config.default.json'))
            config = ConfigStore(root)
            db = Database(root / 'data/test.sqlite3')
            projects = Projects(config, db)
            content = Content(config, Skills(), projects)
            worker = Worker(db, config, projects, content, Assets(config, projects))
            old_queued = db.enqueue('old-queued', 'render')
            old_running = db.enqueue('old-running', 'render')
            db.update(old_running, 'running')
            new = db.enqueue('explicit-new', 'render')
            finished = threading.Event()
            executed = []
            def execute(job):
                executed.append(job['id'])
                worker.shutdown.set()
                finished.set()
                return 'done'
            with patch.object(worker, 'execute', side_effect=execute), patch.object(db, 'recover') as recover:
                try:
                    worker.start(recover=False)
                    worker.start(recover=True)  # A later call must not broaden an active gate.
                    self.assertEqual(worker.queue_mode, 'explicit')
                    worker.allow_job(new)
                    self.assertTrue(finished.wait(3), 'authorized job was not claimed')
                finally:
                    worker.shutdown.set()
                    worker.wake.set()
                    worker.thread.join(timeout=3)
                recover.assert_not_called()
            self.assertFalse(worker.thread.is_alive())
            self.assertEqual(executed, [new])
            self.assertEqual(db.job(old_queued)['status'], 'queued')
            self.assertEqual(db.job(old_running)['status'], 'paused')
            self.assertEqual(db.job(new)['status'], 'done')

    def test_launch_serve_only_sets_environment_and_does_not_open_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / 'runtime/python.exe'
            runtime.parent.mkdir()
            runtime.write_bytes(b'fixture')
            value = {'version': '4.0.0', 'application_root': str(root)}
            child = Mock()
            child.poll.return_value = None
            with patch.object(start, 'health', side_effect=[None, value]), \
                    patch.object(start.socket, 'socket') as socket, \
                    patch.object(start.subprocess, 'Popen', return_value=child) as popen, \
                    patch.object(start.webbrowser, 'open') as browser:
                socket.return_value.__enter__.return_value.connect_ex.return_value = 1
                self.assertEqual(start.launch(root, serve_only=True), value)
            self.assertEqual(popen.call_args.kwargs['env']['FACTORY_SERVE_ONLY'], '1')
            browser.assert_not_called()

    def test_direct_serve_entrypoint_honors_serve_only_and_port(self):
        with patch.dict(os.environ, {}, clear=False), \
                patch('sys.argv', ['launcher/serve.py', '--serve-only', '--port', '8787']), \
                patch('launcher.seed_resources.seed'), patch('uvicorn.run') as run:
            runpy.run_path(str(ROOT / 'launcher/serve.py'), run_name='__main__')
            self.assertEqual(os.environ['FACTORY_SERVE_ONLY'], '1')
            self.assertEqual(run.call_args.kwargs['port'], 8787)
            self.assertEqual(run.call_args.kwargs['host'], '127.0.0.1')


if __name__ == '__main__':
    unittest.main()
