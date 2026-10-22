"""Durable discovery and progress cursors without providers, GPUs, or a server."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.database import Database


class JobQueryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Database(Path(temp.name) / 'jobs.sqlite3')

    def test_old_job_is_retrievable_after_more_than_one_hundred_jobs(self):
        first = self.db.enqueue('old-project', 'render', {'limit': 1})
        for number in range(205):
            self.db.enqueue(f'new-project-{number}', 'outline')
        self.assertNotIn(first, [job['id'] for job in self.db.jobs()])
        # A new Database instance can resolve the persisted record directly.
        job = Database(self.db.path).job(first)
        self.assertEqual(job['id'], first)
        self.assertEqual(json.loads(job['payload']), {'limit': 1})
        self.assertEqual(job['project_id'], 'old-project')
        self.assertIsNone(self.db.job('missing'))

    def test_pagination_is_complete_and_deterministic_with_same_second_timestamps(self):
        with patch('app.database.now', return_value='2026-10-22T00:00:00'):
            ids = [self.db.enqueue(f'project-{number}', 'render') for number in range(205)]
        seen, cursor = [], None
        while True:
            page = self.db.jobs_page(limit=37, before=cursor)
            self.assertLessEqual(len(page['items']), 37)
            self.assertTrue(all('cursor' not in item for item in page['items']))
            seen.extend(item['id'] for item in page['items'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual(seen, list(reversed(ids)))
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(self.db.jobs_page(before=1), {'items': [], 'next_cursor': None})

    def test_filtered_pages_do_not_skip_matching_projects_or_statuses(self):
        ids = []
        for number in range(9):
            jid = self.db.enqueue('wanted', 'render')
            self.db.update(jid, 'done' if number % 2 == 0 else 'error')
            ids.append(jid)
            other = self.db.enqueue('other', 'render')
            self.db.update(other, 'done')
        result, cursor = [], None
        while True:
            page = self.db.jobs_page(limit=2, before=cursor, project_id='wanted', status='done')
            result.extend(item['id'] for item in page['items'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual(result, list(reversed(ids[::2])))

    def test_cursor_follows_events_for_only_the_requested_job(self):
        first = self.db.enqueue('first', 'render')
        other = self.db.enqueue('other', 'render')
        self.db.claim()
        self.db.update(first, message='encoding', event={'current_stage': 'encoding', 'progress': 20})
        self.db.update(other, 'done')
        self.db.update(first, 'done', 'finished')
        first_page = self.db.job_events(first, limit=2)
        second_page = self.db.job_events(first, after=first_page['next_cursor'], limit=2)
        combined = first_page['items'] + second_page['items']
        self.assertEqual([item['job_id'] for item in combined], [first] * 4)
        self.assertEqual([item['data'].get('status') for item in combined], ['queued', 'running', None, 'done'])
        self.assertEqual(combined[-1]['data']['previous_status'], 'running')
        self.assertEqual(combined[-1]['data']['message'], 'finished')
        self.assertTrue(all(isinstance(item['data'], dict) and item['timestamp'] for item in combined))
        cursor = second_page['next_cursor']
        self.assertEqual(self.db.job_events(first, after=cursor), {'items': [], 'next_cursor': cursor})
        self.assertEqual(self.db.job_events('missing'), {'items': [], 'next_cursor': 0})

    def test_terminal_events_without_callback_and_repeated_status_is_not_duplicate(self):
        for status in ('done', 'error', 'paused', 'review'):
            jid = self.db.enqueue(status, 'render')
            self.db.update(jid, status, 'finished')
            self.db.update(jid, status, 'unchanged')
            events = self.db.job_events(jid)['items']
            self.assertEqual(len(events), 2)
            self.assertEqual(events[-1]['data']['status'], status)
        self.db.update('missing', 'done', event={'message': 'no orphan'})
        self.assertEqual(self.db.job_events('missing')['items'], [])

    def test_events_only_store_safe_progress_and_filter_historical_blobs(self):
        jid = self.db.enqueue('safe', 'render')
        private = {'message': 'api_key=very-private Bearer super-secret',
                   'current_stage': 'sampling', 'shots': {'dialogue': 'private script'},
                   'prompt': 'private prompt', 'token': 'private token',
                   'output': {'nested': 'untrusted'}, 'percent': 50}
        self.db.update(jid, event=private)
        with self.db.connect() as connection:
            raw = connection.execute('SELECT data FROM events WHERE job_id=? ORDER BY id DESC LIMIT 1', (jid,)).fetchone()[0]
            self.assertNotIn('private', raw)
            self.assertNotIn('super-secret', raw)
            # Old releases stored arbitrary renderer state, and invalid rows must
            # not prevent all subsequent events from being read.
            connection.execute('INSERT INTO events(job_id,timestamp,data) VALUES(?,?,?)', (jid, 'old', json.dumps(private)))
            connection.execute('INSERT INTO events(job_id,timestamp,data) VALUES(?,?,?)', (jid, 'bad', 'not json'))
        events = self.db.job_events(jid)['items']
        self.assertEqual(events[1]['data'], events[2]['data'])
        self.assertEqual(events[1]['data']['percent'], 50)
        self.assertEqual(events[1]['data']['current_stage'], 'sampling')
        self.assertIn('[redacted]', events[1]['data']['message'])
        self.assertEqual(events[-1]['data'], {})

    def test_cancel_and_recover_record_terminal_transitions(self):
        queued = self.db.enqueue('queued', 'render')
        self.db.cancel('queued')
        self.assertEqual(self.db.job_events(queued)['items'][-1]['data']['status'], 'paused')
        running = self.db.enqueue('running', 'render')
        self.assertEqual(self.db.claim()['id'], running)
        self.db.cancel('running')
        self.db.cancel('running')
        self.db.recover()
        events = self.db.job_events(running)['items']
        self.assertEqual([item['data']['status'] for item in events], ['queued', 'running', 'running', 'paused'])
        self.assertEqual(self.db.job(running)['status'], 'paused')

    def test_batch_cancel_and_requeue_keep_durable_ids(self):
        ids = self.db.enqueue_many([('ep-1', 'render', {'series_id': 'series'}),
                                    ('ep-2', 'render', {'series_id': 'series'})], 'batch')
        self.assertEqual(self.db.cancel_series('series', queued_only=True, batch_id='batch'), ['ep-1', 'ep-2'])
        for jid in ids:
            self.assertEqual(self.db.job_events(jid)['items'][-1]['data']['status'], 'paused')
        image = self.db.enqueue('__image_i', 'image-optimize', {'image_id': 'i'})
        self.db.update(image, 'done')
        newer = self.db.enqueue('newer', 'render')
        self.assertEqual(self.db.jobs_page(limit=1)['items'][0]['id'], newer)
        self.db.requeue_image(image, '__image_i', 'i', 'image-generate')
        self.assertEqual(self.db.job(image)['kind'], 'image-generate')
        self.assertEqual(self.db.jobs_page(limit=1)['items'][0]['id'], image)
        self.assertEqual(self.db.job_events(image)['items'][-1]['data']['status'], 'queued')

    def test_invalid_limits_cursors_and_filters_fail_without_sql_errors(self):
        for limit in (0, -1, 201, True, 1.5, '20', None):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    self.db.jobs_page(limit=limit)
                with self.assertRaises(ValueError):
                    self.db.job_events('id', limit=limit)
        for before in (0, -1, True, 1.5, '1', 2**63):
            with self.subTest(before=before), self.assertRaises(ValueError):
                self.db.jobs_page(before=before)
        for after in (-1, True, 1.5, '1', None, 2**63):
            with self.subTest(after=after), self.assertRaises(ValueError):
                self.db.job_events('id', after=after)
        for status in ('', 'unknown', 0, []):
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.db.jobs_page(status=status)
        for project in ('', ' ', 1):
            with self.subTest(project=project), self.assertRaises(ValueError):
                self.db.jobs_page(project_id=project)


if __name__ == '__main__':
    unittest.main()
