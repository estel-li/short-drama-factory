"""Process ownership, not elapsed time, permits interrupted job recovery."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.database import Database
from app.jobs import Worker
from app.processes import InstanceLock
from app.projects import Projects
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


class WorkerRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_json(self.root / 'config.default.json', read_json(ROOT / 'config.default.json'))
        config = ConfigStore(self.root)
        self.db = Database(self.root / 'data/jobs.sqlite3')
        rooted = patch('app.projects.ROOT', self.root)
        rooted.start()
        self.addCleanup(rooted.stop)
        projects = Projects(config, self.db)
        self.worker = Worker(self.db, config, projects, Content(config, Skills(), projects), Assets(config, projects))

    def test_recovery_only_pauses_running_preserving_payload_attempts_and_queue(self):
        running = self.db.enqueue('interrupted', 'render', {'plan_id': 'original', 'agent_plan': True})
        queued = self.db.enqueue('older-queue', 'render')
        self.db.claim({running})
        before = self.db.job(running)
        self.assertEqual(self.worker.recover_orphaned_jobs(), [running])
        self.assertIsNone(self.worker.thread)
        self.assertIsNone(self.worker.instance_lock.file)
        after = self.db.job(running)
        self.assertEqual(after['status'], 'paused')
        self.assertEqual(after['attempts'], before['attempts'])
        self.assertEqual(after['payload'], before['payload'])
        self.assertEqual(json.loads(after['failure'])['code'], 'WORKER_INTERRUPTED')
        self.assertEqual(self.db.job(queued)['status'], 'queued')
        self.assertEqual(self.db.job(queued)['attempts'], 0)
        transitions = [row['data']['status'] for row in self.db.job_events(running)['items'] if row['data'].get('type') == 'status_changed']
        self.assertEqual(transitions, ['queued', 'running', 'paused'])
        self.assertEqual(self.worker.recover_orphaned_jobs(), [])

    def test_live_current_thread_is_never_recovered(self):
        jid = self.db.enqueue('current', 'render')
        self.db.claim({jid})
        self.worker.thread = Mock()
        self.worker.thread.is_alive.return_value = True
        with patch.object(self.worker.instance_lock, 'acquire') as acquire:
            self.assertEqual(self.worker.recover_orphaned_jobs(jid), [])
            acquire.assert_not_called()
        self.assertEqual(self.db.job(jid)['status'], 'running')

    def test_other_process_lock_prevents_recovery_until_owner_exits(self):
        jid = self.db.enqueue('another-process', 'render')
        self.db.claim({jid})
        script = ('import sys; from pathlib import Path; from app.processes import InstanceLock; '
                  'lock=InstanceLock(Path(sys.argv[1])); lock.acquire(); '
                  'print("locked", flush=True); sys.stdin.readline(); lock.release()')
        child = subprocess.Popen([sys.executable, '-c', script, str(self.worker.instance_lock.path)],
                                 cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            self.assertEqual(self.worker.recover_orphaned_jobs(jid), [])
            self.assertEqual(self.db.job(jid)['status'], 'running')
            child.communicate('\n', timeout=5)
            self.assertEqual(child.returncode, 0)
            self.assertEqual(self.worker.recover_orphaned_jobs(jid), [jid])
            self.assertEqual(self.db.job(jid)['status'], 'paused')
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

    def test_database_failure_releases_lock_and_does_not_start_work(self):
        with patch.object(self.db, 'pause_interrupted_jobs', side_effect=OSError('fixture disk error')):
            with self.assertRaises(OSError):
                self.worker.recover_orphaned_jobs()
            with self.assertRaises(OSError):
                self.worker.start(recover=False)
        self.assertIsNone(self.worker.thread)
        self.assertIsNone(self.worker.instance_lock.file)
        other = InstanceLock(self.worker.instance_lock.path)
        other.acquire()
        other.release()


if __name__ == '__main__':
    unittest.main()
