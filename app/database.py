from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager

from .storage import ROOT, now


class Database:
    def __init__(self, path=None):
        self.path = path or ROOT / 'data' / 'factory.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, path TEXT NOT NULL, title TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS series(id TEXT PRIMARY KEY, path TEXT NOT NULL, title TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                    status TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, cancel_requested INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS job_status ON jobs(status,created_at);
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, job_id TEXT, timestamp TEXT NOT NULL, data TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def index(self, project, title, touch=True):
        with self.connect() as db:
            update = 'path=excluded.path,title=excluded.title' + (',updated_at=excluded.updated_at' if touch else '')
            db.execute('INSERT INTO projects VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET ' + update,
                       (project.name, str(project), title, now()))

    def enqueue(self, project_id, kind, payload=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (project_id,)).fetchone():
                raise ValueError('此项目已有排队或执行中的任务。')
            jid = uuid.uuid4().hex
            db.execute('INSERT INTO jobs(id,project_id,kind,payload,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                       (jid, project_id, kind, json.dumps(payload or {}), 'queued', now(), now()))
            return jid

    def enqueue_many(self, entries, batch_id):
        """One transaction, persistent idempotency, and FIFO even within the same second."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute("SELECT id FROM jobs WHERE json_extract(payload,'$.series_batch')=? ORDER BY rowid", (batch_id,)).fetchall()
            if previous:
                return [row[0] for row in previous]
            pids = [entry[0] for entry in entries]
            if len(pids) != len(set(pids)):
                raise ValueError('批量任务包含重复项目。')
            for pid in pids:
                if db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone():
                    raise ValueError('所选分集已有任务排队或执行，请先停止或等待完成。')
            ids = []
            for pid, kind, payload in entries:
                jid = uuid.uuid4().hex
                db.execute('INSERT INTO jobs(id,project_id,kind,payload,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                           (jid, pid, kind, json.dumps({**payload, 'series_batch': batch_id}), 'queued', now(), now()))
                ids.append(jid)
            return ids

    def requeue_image(self, jid, owner, iid, kind):
        """Continue an image's CPU/GPU phases under its existing durable job ID."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
            if not row or row['project_id'] != owner or row['kind'] not in ('image-optimize', 'image-generate') or json.loads(row['payload']).get('image_id') != iid:
                raise ValueError('原图片任务记录不匹配，请刷新后重试。')
            if db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (owner,)).fetchone():
                raise ValueError('图片或所属项目仍在处理，请等待完成。')
            # A resumed phase joins the queue tail, while references keep the stable job ID.
            db.execute("UPDATE jobs SET rowid=(SELECT COALESCE(MAX(rowid),0)+1 FROM jobs),kind=?,status='queued',cancel_requested=0,message='继续原图片任务',created_at=?,updated_at=? WHERE id=?", (kind, now(), now(), jid))
        return jid

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status=CASE WHEN cancel_requested=1 THEN 'paused' ELSE 'queued' END,message='服务重启，等待从持久化阶段恢复',updated_at=? WHERE status='running'", (now(),))

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM jobs WHERE status='queued' AND cancel_requested=0 ORDER BY created_at,rowid LIMIT 1").fetchone()
            if not row:
                return None
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated_at=? WHERE id=?", (now(), row['id']))
            return dict(row)

    def update(self, jid, status=None, message='', event=None):
        with self.connect() as db:
            db.execute('UPDATE jobs SET status=COALESCE(?,status),message=?,updated_at=? WHERE id=?', (status, message, now(), jid))
            if event:
                db.execute('INSERT INTO events(job_id,timestamp,data) VALUES(?,?,?)', (jid, now(), json.dumps(event, ensure_ascii=False)))

    def jobs(self, limit=100):
        with self.connect() as db:
            return [dict(x) for x in db.execute('SELECT * FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT ?', (limit,))]

    def cancel_series(self, sid, queued_only=False, batch_id=None):
        with self.connect() as db:
            rows = db.execute("SELECT id,project_id,payload FROM jobs WHERE status IN ('queued','running')").fetchall()
            cancelled = []
            for row in rows:
                payload = json.loads(row['payload'])
                if payload.get('series_id') != sid or (batch_id and payload.get('series_batch') != batch_id):
                    continue
                condition = "AND status='queued'" if queued_only else ''
                cursor = db.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=? WHERE id=? " + condition, (now(), row['id']))
                if cursor.rowcount:
                    cancelled.append(row['project_id'])
            return cancelled

    def busy(self, pid):
        with self.connect() as db:
            return bool(db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone())

    def cancel(self, pid):
        with self.connect() as db:
            db.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=? WHERE project_id=? AND status IN ('queued','running')", (now(), pid))

    def cancelled(self, jid):
        with self.connect() as db:
            row = db.execute('SELECT cancel_requested FROM jobs WHERE id=?', (jid,)).fetchone()
            return bool(row and row[0])
