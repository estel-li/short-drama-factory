"""Transactional request receipts and authorized durable queue recovery."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from app.contracts import ContractError
from app.database import Database


class OperationDatabaseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Database(Path(temp.name) / 'operations.sqlite3')

    def test_reservation_is_canonical_and_persistent_without_storing_request(self):
        first = self.db.reserve_operation('client:one', 'project.create', {'b': 2, 'a': {'secret_text': 'private'}})
        reopened = Database(self.db.path)
        second = reopened.reserve_operation('client:one', 'project.create', {'a': {'secret_text': 'private'}, 'b': 2})
        self.assertEqual(first, second)
        self.assertEqual(first['status'], 'pending')
        self.assertIsNone(first['result'])
        self.assertEqual(len(first['operation_id']), 32)
        self.assertEqual(len(first['request_hash']), 64)
        self.assertNotIn('private', json.dumps(first))
        self.assertEqual(reopened.operation('client:one'), first)
        self.assertIsNone(reopened.operation('missing'))

    def test_same_key_different_content_or_scope_conflicts(self):
        self.db.reserve_operation('request', 'project.create', {'a': 1})
        for scope, payload in [('project.create', {'a': 2}), ('project.run', {'a': 1})]:
            with self.subTest(scope=scope), self.assertRaises(ContractError) as caught:
                self.db.reserve_operation('request', scope, payload)
            self.assertEqual(caught.exception.code, 'IDEMPOTENCY_CONFLICT')
            self.assertEqual(caught.exception.status, 409)

    def test_completed_result_survives_reopen_and_is_immutable(self):
        self.db.reserve_operation('request', 'create', {})
        result = {'id': 'p1', 'revision': 1, 'files': ['story.json']}
        completed = self.db.complete_operation('request', result)
        self.assertEqual(completed['status'], 'completed')
        self.assertEqual(completed['result'], result)
        self.assertEqual(Database(self.db.path).operation('request'), completed)
        self.assertEqual(self.db.complete_operation('request', dict(reversed(list(result.items())))), completed)
        with self.assertRaises(ContractError) as caught:
            self.db.complete_operation('request', {'id': 'different'})
        self.assertEqual(caught.exception.code, 'IDEMPOTENCY_CONFLICT')

    def test_pending_recovery_data_can_complete_but_not_be_overwritten(self):
        self.db.reserve_operation('request', 'story.update', {})
        staged = self.db.stage_operation('request', {'before_revision': 3, 'after_digest': 'abcd'})
        self.assertEqual(staged['status'], 'pending')
        self.assertEqual(Database(self.db.path).operation('request')['result'], staged['result'])
        self.assertEqual(self.db.stage_operation('request', staged['result']), staged)
        with self.assertRaises(ContractError):
            self.db.stage_operation('request', {'before_revision': 4})
        completed = self.db.complete_operation('request', {'id': 'project', 'revision': 4})
        self.assertEqual(completed['status'], 'completed')
        self.assertEqual(completed['result']['revision'], 4)

    def test_concurrent_reservations_return_one_operation_identity(self):
        barrier = threading.Barrier(8)

        def reserve(_):
            barrier.wait()
            return self.db.reserve_operation('parallel', 'create', {'input': 'one'})

        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(reserve, range(8)))
        self.assertEqual(len({value['operation_id'] for value in values}), 1)

    def test_concurrent_enqueue_replays_one_job_and_one_receipt(self):
        barrier = threading.Barrier(8)

        def enqueue(_):
            barrier.wait()
            return self.db.enqueue_operation('parallel', 'run', {'id': 'project'}, 'project', 'render', {'strict': True})

        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(enqueue, range(8)))
        self.assertTrue(all(value == values[0] for value in values))
        result = values[0]
        self.assertEqual(len(self.db.jobs()), 1)
        self.assertEqual(result['request_key'], 'parallel')
        self.assertEqual(result['id'], 'project')
        self.assertEqual(self.db.operation('parallel')['result'], result)
        self.assertEqual(json.loads(self.db.job(result['job_id'])['payload']), {'strict': True})
        self.assertEqual(len(self.db.job_events(result['job_id'])['items']), 1)

    def test_completed_enqueue_replays_before_current_busy_state(self):
        result = self.db.enqueue_operation('first', 'run', {'id': 'p'}, 'p', 'render')
        # Same active task already makes the project busy; replay succeeds.
        self.assertEqual(self.db.enqueue_operation('first', 'run', {'id': 'p'}, 'p', 'render'), result)
        self.db.update(result['job_id'], 'done')
        self.db.enqueue('p', 'outline')
        # A different newer active task must not invalidate the old receipt.
        self.assertEqual(self.db.enqueue_operation('first', 'run', {'id': 'p'}, 'p', 'render'), result)
        self.assertEqual(len(self.db.jobs()), 2)

    def test_existing_pending_reservation_can_enqueue_and_complete_atomically(self):
        reserved = self.db.reserve_operation('pending', 'run', {'id': 'p'})
        result = self.db.enqueue_operation('pending', 'run', {'id': 'p'}, 'p', 'render')
        self.assertEqual(result['operation_id'], reserved['operation_id'])
        self.assertEqual(self.db.operation('pending')['status'], 'completed')

    def test_failure_after_job_insert_rolls_back_job_receipt_and_event(self):
        with patch.object(self.db, '_save_operation', side_effect=RuntimeError('simulated full disk')):
            with self.assertRaises(RuntimeError):
                self.db.enqueue_operation('new', 'run', {}, 'p', 'render')
        self.assertIsNone(self.db.operation('new'))
        self.assertEqual(self.db.jobs(), [])
        with self.db.connect() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)

    def test_failure_preserves_preexisting_pending_reservation(self):
        reserved = self.db.reserve_operation('pending', 'run', {})
        with patch.object(self.db, '_event', side_effect=RuntimeError('event write failed')):
            with self.assertRaises(RuntimeError):
                self.db.enqueue_operation('pending', 'run', {}, 'p', 'render')
        self.assertEqual(self.db.operation('pending'), reserved)
        self.assertEqual(self.db.jobs(), [])
        result = self.db.enqueue_operation('pending', 'run', {}, 'p', 'render')
        self.assertEqual(result['operation_id'], reserved['operation_id'])

    def test_busy_new_request_has_no_partial_receipt_or_extra_job(self):
        self.db.enqueue('p', 'render')
        with self.assertRaises(ContractError) as caught:
            self.db.enqueue_operation('new', 'run', {}, 'p', 'render')
        self.assertEqual(caught.exception.code, 'PROJECT_BUSY')
        self.assertIsNone(self.db.operation('new'))
        self.assertEqual(len(self.db.jobs()), 1)

    def test_requeue_preserves_id_attempts_and_payload_and_joins_tail(self):
        jid = self.db.enqueue('p', 'render', {'strict': True})
        self.db.claim()
        self.db.cancel('p')
        self.db.update(jid, 'paused')
        tail = self.db.enqueue('other', 'outline')
        self.assertEqual(self.db.requeue_job(jid), jid)
        row = self.db.job(jid)
        self.assertEqual(row['status'], 'queued')
        self.assertEqual(row['attempts'], 1)
        self.assertEqual(row['cancel_requested'], 0)
        self.assertEqual(json.loads(row['payload']), {'strict': True})
        self.assertEqual(self.db.claim()['id'], tail)
        self.assertEqual(self.db.claim()['id'], jid)
        self.assertEqual(self.db.job(jid)['attempts'], 2)

    def test_requeue_operation_is_atomic_and_replayable_after_status_changes(self):
        jid = self.db.enqueue('p', 'render')
        self.db.update(jid, 'error')
        result = self.db.requeue_operation('resume', 'resume', {'job_id': jid}, jid)
        self.assertEqual(result['job_id'], jid)
        self.db.claim()
        self.db.update(jid, 'done')
        self.assertEqual(self.db.requeue_operation('resume', 'resume', {'job_id': jid}, jid), result)
        self.assertEqual(self.db.job(jid)['status'], 'done')
        with self.assertRaises(ContractError):
            self.db.requeue_job(jid)

    def test_requeue_rollback_retains_terminal_job(self):
        jid = self.db.enqueue('p', 'render')
        self.db.update(jid, 'review')
        with patch.object(self.db, '_save_operation', side_effect=RuntimeError('simulated full disk')):
            with self.assertRaises(RuntimeError):
                self.db.requeue_operation('resume', 'resume', {}, jid)
        self.assertEqual(self.db.job(jid)['status'], 'review')
        self.assertIsNone(self.db.operation('resume'))

    def test_requeue_checks_project_busy_and_missing_job(self):
        jid = self.db.enqueue('p', 'render')
        self.db.update(jid, 'error')
        self.db.enqueue('p', 'outline')
        with self.assertRaises(ContractError) as caught:
            self.db.requeue_job(jid)
        self.assertEqual(caught.exception.code, 'PROJECT_BUSY')
        with self.assertRaises(ContractError) as caught:
            self.db.requeue_job('missing')
        self.assertEqual(caught.exception.code, 'JOB_NOT_FOUND')

    def test_claim_restricts_authorized_ids_without_changing_old_queue(self):
        old = self.db.enqueue('old', 'render')
        selected = self.db.enqueue('selected', 'render')
        self.assertIsNone(self.db.claim(allowed_ids=set()))
        self.assertEqual(self.db.claim(allowed_ids={selected})['id'], selected)
        self.assertEqual(self.db.job(old)['status'], 'queued')
        self.assertEqual(self.db.job(old)['attempts'], 0)
        self.assertIsNone(self.db.claim(allowed_ids={selected}))
        self.assertEqual(self.db.claim()['id'], old)

    def test_invalid_keys_data_and_missing_completion_are_explicit(self):
        for key in ('', 'x' * 129, 'space key', '中文', '\n', None, 12):
            with self.subTest(key=key), self.assertRaises(ContractError) as caught:
                self.db.reserve_operation(key, 'create', {})
            self.assertEqual(caught.exception.code, 'INVALID_IDEMPOTENCY_KEY')
        with self.assertRaises(ContractError):
            self.db.reserve_operation('request', '', {})
        for payload in ({'value': float('nan')}, {'object': object()}):
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                self.db.reserve_operation('request', 'create', payload)
        with self.assertRaises(ContractError) as caught:
            self.db.complete_operation('missing', {})
        self.assertEqual(caught.exception.code, 'OPERATION_NOT_FOUND')


if __name__ == '__main__':
    unittest.main()
