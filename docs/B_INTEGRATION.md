# 與莊育哲（B）整合的最小契約

此文件是交接資訊，不表示 B 的程式已完成。

## Repo 分工

- A 蕭博軒：`app.py`、`storage.py`、`tracker.py`、`exporter.py`、`ai_assistant.py`、`tests/`
- B 莊育哲：`scheduler.py`、`reminder_worker.py`、`line_bot.py`（需 Flask Webhook）
- 不要兩人同時修改 `main`；每人使用自己的 `feature/` 分支並開 Pull Request。

## B 要採用的既有函式

```python
from storage import data_path, load_json, update_json, save_feedback

# worker 更新 reminders.json 時，使用單檔交易式讀改寫：
update_json(data_path('reminders'), lambda reminders: reminders + [new_reminder])

# LINE 驗簽、辨識使用者及課次、確認輸入後，再儲存：
new_feedback = {
    'feedback_id': 'feedback_1',
    'user_id': 'demo_user_001',
    'event_id': 'event_001',
    'class_date': '2026-11-23',
    'reminder_id': '',    # 手動補登沒有關聯的成功提醒時留空
    'received_at': '2026-11-23T16:01:00+08:00',
    'content': '今天學了 PID，但不懂積分項的穩定性',
    'source': 'selected', # 或 'push'
    'webhook_event_id': 'unique_event_id_from_line',
}
newly_saved = save_feedback(new_feedback)
```

> 請勿用 `load_json` 後自行 `append` 再 `save_json` 來做併發修改；請用 `update_json`。`save_feedback` 將 webhook id 與筆記放同一檔案，避免分別寫入兩個 JSON 時被中斷。

## B 排程輸出

```python
from datetime import datetime

def make_plan(tasks: list, availability: list, previous_plan: list, now: datetime) -> list:
    return [
        {
            'user_id': 'demo_user_001',
            'task_id': 'task_001',
            'availability_id': 'slot_001',
            'status': 'scheduled',       # 或 unscheduled
            'source': 'auto',            # 或 manual
            'reason': '',
            'unscheduled_alerted': False,
        }
    ]
```

- 程式按 **使用者指定 → 最早 Deadline → 同期限較長任務 → Best Fit** 進行。
- 即使任務 `unscheduled`，仍須有 `user_id`、`task_id`、`status` 和 `reason`。
- Streamlit 會呼叫這個函式並將回傳值寫入 `plan.json`。如果你要讓 worker 發送未排入警示，請自己處理新增警示流程，避免 Web UI 重新整理重複提醒。
- `get_due_events` 與 `reminder_worker` 不應依賴有人打開 Streamlit。

## LINE 端課次定位

- 使用者先選「補筆記」→ 星期 → 時段 → 確認實際課次日期與課名 → 輸入文字。
- `event_id` 一定來自 `events.json` 而非自由文字猜測。
- 遇到尚未下課時，不要默默選到上週；應讓使用者看見正確日期並確認。
- `received_at` 使用含臺北時區的 ISO8601；同一 webhookEventId 重送不可重複寫入。
- `line_user_id` 等敏感欄位只寫入 users.json，不出現在 Markdown 匯出檔。

## 測試順序

1. A：`python -m unittest discover -s tests -v`（不依賴 B 端）
2. B：單獨測試 `make_plan()`、課次定位及 webhook 驗簽
3. 合併：建立課表和任務 → 排程 → worker Push → LINE 回覆 → Webhook save_feedback → Streamlit 回覆統計 → .md 匯出 → AI 建議人工確認
4. 如果 LINE、API Key 或常駐服務無法測試，明確標示未驗證，不展示為實際已成功整合。
