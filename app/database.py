from __future__ import annotations

import json
import hashlib
import math
import re
import sqlite3
import uuid
from contextlib import contextmanager

from .contracts import ContractError, safe_message
from .storage import ROOT, now


JOB_STATUSES = frozenset({'queued', 'running', 'review', 'done', 'error', 'paused'})
EVENT_FIELDS = frozenset({
    'type', 'status', 'previous_status', 'message', 'current_stage', 'stage',
    'current_shot', 'shot_id', 'shot_uid', 'total_shots', 'completed',
    'progress', 'percent', 'bytes', 'total', 'file', 'output', 'cancel_requested',
})


def _event_data(value):
    """Keep progress metadata; never copy provider transcripts or project state."""
    if not isinstance(value, dict):
        return {}
    return {key: safe_message(item) if isinstance(item, str) else item
            for key, item in value.items()
            if key in EVENT_FIELDS and (item is None or isinstance(item, (str, int, float, bool)))
            and (not isinstance(item, float) or math.isfinite(item))}


def _page_number(value, name, minimum=1, maximum=200):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} 必须是 {minimum} 到 {maximum} 之间的整数。')
    return value


def _operation_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', key):
        raise ContractError('INVALID_IDEMPOTENCY_KEY', '请求标识必须是 1 到 128 位 ASCII 字母、数字或 _ . : -。', status=422)
    return key


def _canonical_json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractError('INVALID_OPERATION_DATA', '操作数据必须是有效 JSON。', status=422) from exc


def _operation_row(row):
    if row is None:
        return None
    return {**dict(row), 'result': json.loads(row['result']) if row['result'] is not None else None}


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
                CREATE INDEX IF NOT EXISTS event_job_cursor ON events(job_id,id);
                CREATE TABLE IF NOT EXISTS operations(
                    key TEXT PRIMARY KEY, scope TEXT NOT NULL, request_hash TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL CHECK(status IN ('pending','completed')),
                    result TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
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

    @staticmethod
    def _event(db, jid, data, timestamp=None):
        db.execute('INSERT INTO events(job_id,timestamp,data) VALUES(?,?,?)',
                   (jid, timestamp or now(), json.dumps(_event_data(data), ensure_ascii=False)))

    @staticmethod
    def _reserve_operation(db, key, scope, payload):
        _operation_key(key)
        if not isinstance(scope, str) or not scope.strip() or len(scope) > 128:
            raise ContractError('INVALID_OPERATION_SCOPE', '操作范围必须是 1 到 128 位非空字符串。', status=422)
        request_hash = hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()
        row = db.execute('SELECT * FROM operations WHERE key=?', (key,)).fetchone()
        if row:
            if row['scope'] != scope or row['request_hash'] != request_hash:
                raise ContractError('IDEMPOTENCY_CONFLICT', '请求标识已用于不同操作或不同请求内容。', status=409,
                                    next_actions=['use_new_request_key'])
            return _operation_row(row)
        timestamp = now()
        db.execute('INSERT INTO operations(key,scope,request_hash,operation_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                   (key, scope, request_hash, uuid.uuid4().hex, 'pending', timestamp, timestamp))
        return _operation_row(db.execute('SELECT * FROM operations WHERE key=?', (key,)).fetchone())

    def reserve_operation(self, key, scope, payload):
        """Persist an operation identity before effects, without storing request text."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._reserve_operation(db, key, scope, payload)

    def operation(self, key):
        _operation_key(key)
        with self.connect() as db:
            return _operation_row(db.execute('SELECT * FROM operations WHERE key=?', (key,)).fetchone())

    @staticmethod
    def _save_operation(db, key, result, complete):
        _operation_key(key)
        if not isinstance(result, dict):
            raise ContractError('INVALID_OPERATION_DATA', '操作回执结果必须是 JSON 对象。', status=422)
        encoded = _canonical_json(result)
        row = db.execute('SELECT * FROM operations WHERE key=?', (key,)).fetchone()
        if row is None:
            raise ContractError('OPERATION_NOT_FOUND', '操作回执不存在。', status=404)
        # Completion is immutable. Pending recovery data may be completed, but
        # cannot be silently replaced by a competing writer's different plan.
        if row['status'] == 'completed' or (not complete and row['result'] is not None):
            if row['result'] != encoded:
                raise ContractError('IDEMPOTENCY_CONFLICT', '此操作已保存不同的回执结果。', status=409)
            return _operation_row(row)
        db.execute('UPDATE operations SET status=?,result=?,updated_at=? WHERE key=?',
                   ('completed' if complete else 'pending', encoded, now(), key))
        return _operation_row(db.execute('SELECT * FROM operations WHERE key=?', (key,)).fetchone())

    def stage_operation(self, key, result):
        """Persist immutable recovery metadata before a non-database effect."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._save_operation(db, key, result, complete=False)

    def complete_operation(self, key, result):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._save_operation(db, key, result, complete=True)

    def enqueue_operation(self, key, scope, request_payload, project_id, kind, job_payload=None):
        """A receipt and its queued job commit together, or neither commits."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            receipt = self._reserve_operation(db, key, scope, request_payload)
            if receipt['status'] == 'completed':
                return receipt['result']
            if db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (project_id,)).fetchone():
                raise ContractError('PROJECT_BUSY', '此项目已有排队或执行中的任务。', status=409,
                                    retryable=True, next_actions=['watch', 'stop'])
            jid, timestamp = uuid.uuid4().hex, now()
            db.execute('INSERT INTO jobs(id,project_id,kind,payload,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                       (jid, project_id, kind, _canonical_json(job_payload or {}), 'queued', timestamp, timestamp))
            self._event(db, jid, {'type': 'status_changed', 'status': 'queued', 'previous_status': None}, timestamp)
            result = {'job_id': jid, 'id': project_id, 'operation_id': receipt['operation_id'], 'request_key': key}
            self._save_operation(db, key, result, complete=True)
            return result

    def _requeue_job(self, db, jid):
        row = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
        if row is None:
            raise ContractError('JOB_NOT_FOUND', '任务不存在。', status=404)
        if row['status'] not in ('paused', 'error', 'review'):
            raise ContractError('JOB_NOT_RESUMABLE', '仅暂停、失败或等待审核的任务可以续跑。', status=409,
                                next_actions=['inspect'])
        if db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (row['project_id'],)).fetchone():
            raise ContractError('PROJECT_BUSY', '此项目已有排队或执行中的任务。', status=409,
                                retryable=True, next_actions=['watch', 'stop'])
        timestamp = now()
        db.execute("UPDATE jobs SET rowid=(SELECT COALESCE(MAX(rowid),0)+1 FROM jobs),status='queued',cancel_requested=0,message='继续原任务',created_at=?,updated_at=? WHERE id=?",
                   (timestamp, timestamp, jid))
        self._event(db, jid, {'type': 'status_changed', 'status': 'queued', 'previous_status': row['status'],
                              'message': '继续原任务'}, timestamp)
        return dict(row)

    def requeue_job(self, jid):
        """Resume the original durable job, preserving payload and attempt count."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._requeue_job(db, jid)
        return jid

    def requeue_operation(self, key, scope, request_payload, jid):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            receipt = self._reserve_operation(db, key, scope, request_payload)
            if receipt['status'] == 'completed':
                return receipt['result']
            row = self._requeue_job(db, jid)
            result = {'job_id': jid, 'id': row['project_id'], 'operation_id': receipt['operation_id'], 'request_key': key}
            self._save_operation(db, key, result, complete=True)
            return result

    def enqueue(self, project_id, kind, payload=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (project_id,)).fetchone():
                raise ValueError('此项目已有排队或执行中的任务。')
            jid = uuid.uuid4().hex
            db.execute('INSERT INTO jobs(id,project_id,kind,payload,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                       (jid, project_id, kind, json.dumps(payload or {}), 'queued', now(), now()))
            self._event(db, jid, {'type': 'status_changed', 'status': 'queued', 'previous_status': None})
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
                self._event(db, jid, {'type': 'status_changed', 'status': 'queued', 'previous_status': None})
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
            self._event(db, jid, {'type': 'status_changed', 'status': 'queued', 'previous_status': row['status']})
        return jid

    def recover(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id,cancel_requested FROM jobs WHERE status='running'").fetchall()
            db.execute("UPDATE jobs SET status=CASE WHEN cancel_requested=1 THEN 'paused' ELSE 'queued' END,message='服务重启，等待从持久化阶段恢复',updated_at=? WHERE status='running'", (now(),))
            for row in rows:
                self._event(db, row['id'], {'type': 'status_changed', 'previous_status': 'running',
                                          'status': 'paused' if row['cancel_requested'] else 'queued',
                                          'message': '服务重启，等待从持久化阶段恢复'})

    def claim(self, allowed_ids=None):
        allowed = None if allowed_ids is None else tuple(allowed_ids)
        if allowed == ():
            return None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            where = '' if allowed is None else ' AND id IN (' + ','.join('?' for _ in allowed) + ')'
            row = db.execute("SELECT * FROM jobs WHERE status='queued' AND cancel_requested=0" + where + ' ORDER BY created_at,rowid LIMIT 1',
                             allowed or ()).fetchone()
            if not row:
                return None
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated_at=? WHERE id=?", (now(), row['id']))
            self._event(db, row['id'], {'type': 'status_changed', 'status': 'running', 'previous_status': 'queued'})
            return dict(row)

    def update(self, jid, status=None, message='', event=None):
        if status is not None and (not isinstance(status, str) or status not in JOB_STATUSES):
            raise ValueError('未知任务状态。')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM jobs WHERE id=?', (jid,)).fetchone()
            if not row:
                return
            timestamp = now()
            db.execute('UPDATE jobs SET status=COALESCE(?,status),message=?,updated_at=? WHERE id=?', (status, message, timestamp, jid))
            changed = status is not None and status != row['status']
            if event is not None or changed:
                data = _event_data(event)
                if message:
                    data['message'] = message
                if changed:
                    data.update(type='status_changed', status=status, previous_status=row['status'])
                self._event(db, jid, data, timestamp)

    def jobs(self, limit=100):
        with self.connect() as db:
            return [dict(x) for x in db.execute('SELECT * FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT ?', (limit,))]

    def job(self, jid):
        """Resolve a durable ID regardless of how many newer jobs exist."""
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
            return dict(row) if row else None

    def jobs_page(self, limit=100, before=None, project_id=None, status=None):
        """Page newest-first by SQLite rowid, not second-resolution timestamps.

        This is a live listing. Image phase requeue moves its existing job to a new
        rowid at the queue tail; use job(id) to follow an already discovered job.
        """
        _page_number(limit, 'limit')
        conditions, params = [], []
        if before is not None:
            _page_number(before, 'before', maximum=2**63 - 1)
            conditions.append('rowid < ?')
            params.append(before)
        if project_id is not None:
            if not isinstance(project_id, str) or not project_id.strip():
                raise ValueError('project_id 必须是非空字符串。')
            conditions.append('project_id = ?')
            params.append(project_id)
        if status is not None:
            if not isinstance(status, str) or status not in JOB_STATUSES:
                raise ValueError('未知任务状态。')
            conditions.append('status = ?')
            params.append(status)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        with self.connect() as db:
            rows = db.execute('SELECT rowid AS cursor, * FROM jobs' + where + ' ORDER BY rowid DESC LIMIT ?',
                              (*params, limit + 1)).fetchall()
        items = [{key: row[key] for key in row.keys() if key != 'cursor'} for row in rows[:limit]]
        return {'items': items, 'next_cursor': rows[limit - 1]['cursor'] if len(rows) > limit else None}

    def job_events(self, jid, after=0, limit=100):
        """Read forward from an event cursor, sanitizing historical event blobs too."""
        _page_number(limit, 'limit')
        _page_number(after, 'after', minimum=0, maximum=2**63 - 1)
        with self.connect() as db:
            rows = db.execute('SELECT id,job_id,timestamp,data FROM events WHERE job_id=? AND id>? ORDER BY id LIMIT ?',
                              (jid, after, limit)).fetchall()
        items = []
        for row in rows:
            try:
                data = json.loads(row['data'])
            except (ValueError, TypeError):
                data = {}
            items.append({**dict(row), 'data': _event_data(data)})
        return {'items': items, 'next_cursor': items[-1]['id'] if items else after}

    def cancel_series(self, sid, queued_only=False, batch_id=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id,project_id,payload,status,cancel_requested FROM jobs WHERE status IN ('queued','running')").fetchall()
            cancelled = []
            for row in rows:
                payload = json.loads(row['payload'])
                if payload.get('series_id') != sid or (batch_id and payload.get('series_batch') != batch_id):
                    continue
                condition = "AND status='queued'" if queued_only else ''
                cursor = db.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=? WHERE id=? " + condition, (now(), row['id']))
                if cursor.rowcount:
                    cancelled.append(row['project_id'])
                    if not row['cancel_requested']:
                        self._event(db, row['id'], {'type': 'cancel_requested', 'cancel_requested': True,
                                                  'previous_status': row['status'],
                                                  'status': 'paused' if row['status'] == 'queued' else row['status']})
            return cancelled

    def busy(self, pid):
        with self.connect() as db:
            return bool(db.execute("SELECT id FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchone())

    def cancel(self, pid):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id,status,cancel_requested FROM jobs WHERE project_id=? AND status IN ('queued','running')", (pid,)).fetchall()
            db.execute("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=? WHERE project_id=? AND status IN ('queued','running')", (now(), pid))
            for row in rows:
                if not row['cancel_requested']:
                    self._event(db, row['id'], {'type': 'cancel_requested', 'cancel_requested': True,
                                              'previous_status': row['status'],
                                              'status': 'paused' if row['status'] == 'queued' else row['status']})

    def cancelled(self, jid):
        with self.connect() as db:
            row = db.execute('SELECT cancel_requested FROM jobs WHERE id=?', (jid,)).fetchone()
            return bool(row and row[0])
