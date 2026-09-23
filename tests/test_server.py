"""
test_server.py
===============
בודק את server/app.py עם Flask test client (לא פותח שרת אמיתי, לא
דורש רשת) - קריאות לטלגרם מדומות (monkeypatch) כדי לבדוק את לוגיקת
ה-DB/webhook בבידוד.
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))


class TestServer(unittest.TestCase):
    def setUp(self):
        # DB זמני נפרד לכל בדיקה, כדי לא לגעת בקובץ האמיתי
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
        os.environ["TELEGRAM_CHAT_ID"] = "12345"

        import importlib
        import app as server_app
        importlib.reload(server_app)
        server_app.DB_PATH = os.path.join(self.tmpdir, "test_trades.db")
        server_app.init_db()
        self.server_app = server_app
        self.client = server_app.app.test_client()

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_approved_trades_empty_initially(self):
        resp = self.client.get("/approved-trades.json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    @patch("app.edit_telegram_message")
    @patch("app.answer_callback")
    def test_webhook_approve_updates_status(self, mock_answer, mock_edit):
        import sqlite3
        conn = sqlite3.connect(self.server_app.DB_PATH)
        conn.execute(
            "INSERT INTO trades (id, ticker, memo_text, status, created_at) VALUES (1,'NVDA','memo text','pending','2026-01-01')"
        )
        conn.commit()
        conn.close()

        payload = {
            "callback_query": {
                "id": "cbid1",
                "data": "approve:1",
                "message": {"chat": {"id": 12345}, "message_id": 999},
            }
        }
        resp = self.client.post("/webhook", json=payload)
        self.assertEqual(resp.status_code, 200)

        conn = sqlite3.connect(self.server_app.DB_PATH)
        status = conn.execute("SELECT status FROM trades WHERE id=1").fetchone()[0]
        conn.close()
        self.assertEqual(status, "approved")
        mock_edit.assert_called_once()
        mock_answer.assert_called_once()

    @patch("app.edit_telegram_message")
    @patch("app.answer_callback")
    def test_webhook_reject_updates_status(self, mock_answer, mock_edit):
        import sqlite3
        conn = sqlite3.connect(self.server_app.DB_PATH)
        conn.execute(
            "INSERT INTO trades (id, ticker, memo_text, status, created_at) VALUES (2,'AAPL','memo','pending','2026-01-01')"
        )
        conn.commit()
        conn.close()

        payload = {"callback_query": {"id": "cbid2", "data": "reject:2",
                                       "message": {"chat": {"id": 12345}, "message_id": 1000}}}
        self.client.post("/webhook", json=payload)

        conn = sqlite3.connect(self.server_app.DB_PATH)
        status = conn.execute("SELECT status FROM trades WHERE id=2").fetchone()[0]
        conn.close()
        self.assertEqual(status, "rejected")

    def test_approved_trades_only_returns_approved(self):
        import sqlite3
        conn = sqlite3.connect(self.server_app.DB_PATH)
        conn.execute("INSERT INTO trades (ticker, memo_text, status, created_at) VALUES ('NVDA','m1','approved','2026-01-01')")
        conn.execute("INSERT INTO trades (ticker, memo_text, status, created_at) VALUES ('AAPL','m2','pending','2026-01-01')")
        conn.execute("INSERT INTO trades (ticker, memo_text, status, created_at) VALUES ('TSLA','m3','rejected','2026-01-01')")
        conn.commit()
        conn.close()

        resp = self.client.get("/approved-trades.json")
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["ticker"], "NVDA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
