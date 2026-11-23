import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from storage import (
    DataError, add_task, load_json, save_json, update_json,
    validate_event, validate_availability, save_feedback,
)


class TestStorage(unittest.TestCase):
    def test_save_load_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'data.json'
            save_json(path, [{"title": "控制系統"}])
            self.assertEqual(load_json(path), [{"title": "控制系統"}])

    def test_corrupt_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'broken.json'
            path.write_text('{ bad json', encoding='utf-8')
            with self.assertRaises(DataError):
                save_json(path, [{"x": 1}])
            self.assertEqual(path.read_text(encoding='utf-8'), '{ bad json')

    def test_atomic_update(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'items.json'
            update_json(path, lambda rows: rows + [1])
            update_json(path, lambda rows: rows + [2])
            self.assertEqual(load_json(path), [1, 2])

    def test_class_validation(self):
        item = dict(event_id='e1', user_id='u', title='控制系統', event_type='class',
                    prompt_template='class_feedback', weekday=2, start_time='13:00',
                    end_time='15:00', offset_minutes=10, enabled=True)
        self.assertEqual(validate_event(item), item)
        with self.assertRaises(DataError):
            validate_event({**item, 'start_time':'16:00'})

    def test_availability_overlap(self):
        slot = dict(availability_id='s1', user_id='u', date='2026-11-23', start_time='13:00', available_minutes=60)
        with self.assertRaises(DataError):
            validate_availability({**slot, 'availability_id':'s2', 'start_time':'13:30'}, [slot])

    def test_add_task(self):
        item = dict(task_id='t1', user_id='u', subject='Python', title='作業', deadline='2026-12-01',
                    estimated_minutes=60, status='pending', preferred_availability_id='')
        self.assertEqual(len(add_task([], item)), 1)
        with self.assertRaises(DataError):
            add_task([item], item)

    def test_feedback_dedup_in_same_file(self):
        row = dict(feedback_id='f1', user_id='u', event_id='e1', class_date='2026-11-20',
                   received_at='2026-11-20T16:00:00+08:00', content='了解 Routh 的第一欄',
                   source='push', reminder_id='r1', webhook_event_id='w1')
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'feedback.json'
            self.assertTrue(save_feedback(row, p))
            self.assertFalse(save_feedback(row, p))
            self.assertEqual(len(load_json(p)), 1)


if __name__ == '__main__':
    unittest.main()
