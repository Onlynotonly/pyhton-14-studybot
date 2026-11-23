import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from tracker import calculate_response_rate
from exporter import export_learning_markdown
from ai_assistant import validate_ai_suggestions, AIError, extract_output_text


FEEDBACK = dict(feedback_id='f1', user_id='u', event_id='e1', class_date='2026-11-20',
                received_at='2026-11-20T16:00:00+08:00', content='今天不懂 Routh Criterion',
                source='push', reminder_id='r1', webhook_event_id='w1')
REMINDERS = [dict(reminder_id='r1', user_id='u', kind='class_feedback', status='sent', class_date='2026-11-20'),
             dict(reminder_id='r2', user_id='u', kind='class_feedback', status='sent', class_date='2026-11-21')]

class TestStats(unittest.TestCase):
    def test_unique_response_ids(self):
        report = calculate_response_rate(REMINDERS, [FEEDBACK, {**FEEDBACK, 'feedback_id':'f2'}], 'u')
        self.assertEqual(report, {'sent': 2, 'answered': 1, 'rate': 50.0})

    def test_manual_not_counted(self):
        row = {**FEEDBACK, 'reminder_id': '', 'source': 'selected'}
        self.assertEqual(calculate_response_rate(REMINDERS, [row], 'u')['answered'], 0)

    def test_zero(self):
        self.assertIsNone(calculate_response_rate([], [], 'u')['rate'])

class TestExport(unittest.TestCase):
    def test_export_redacts_and_uses_source_id(self):
        content = 'Email test@example.com 手機 0912345678 不懂極點'
        payload = {'events':[dict(event_id='e1', user_id='u', title='電子學',weekday=2,start_time='13:00',end_time='15:00',offset_minutes=10)],
                   'tasks':[dict(task_id='t1',user_id='u',subject='電子學',title='Ch12',deadline='2026-12-01',estimated_minutes=60,status='pending')],
                   'availability':[], 'plan':[], 'reminders':REMINDERS,
                   'feedback':[{**FEEDBACK,'content': content, 'line_user_id':'SECRET_LINE_ID'}]}
        md = export_learning_markdown(payload, datetime(2026,11,23,tzinfo=ZoneInfo('Asia/Taipei')), 'u')
        self.assertIn('電子學',md)
        self.assertIn('f1',md)
        self.assertIn('Ch12',md)
        self.assertNotIn('SECRET_LINE_ID',md)
        self.assertNotIn('test@example.com',md)
        self.assertNotIn('0912345678',md)

class TestAI(unittest.TestCase):
    def test_ai_sources_checked(self):
        d = dict(summary='ok', suggestions=[dict(topic='控制', unresolved_question='不懂', suggested_task='複習',source_feedback_id='f1')])
        self.assertEqual(validate_ai_suggestions(d,{'f1'}),d)
        with self.assertRaises(AIError):
            validate_ai_suggestions(d,{'unknown'})

    def test_response_parse(self):
        text = extract_output_text({'output':[{'type':'message','content':[{'type':'output_text','text':'{"summary":"ok","suggestions":[]}'}]}]})
        self.assertEqual(json.loads(text)['summary'],'ok')

if __name__=='__main__':
    unittest.main()
