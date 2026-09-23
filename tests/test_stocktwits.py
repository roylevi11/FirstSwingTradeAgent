"""
test_stocktwits.py
===================
בודק את _summarize_messages עם רשימות הודעות מדומות שמחקות את פורמט
ה-JSON האמיתי של StockTwits. לא בודק קריאת רשת אמיתית.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.stocktwits_sentiment import _summarize_messages, _sentiment_of


def _msg(sentiment=None):
    entities = {"sentiment": {"basic": sentiment}} if sentiment else {}
    return {"id": 1, "body": "test", "entities": entities}


class TestStockTwitsSentiment(unittest.TestCase):
    def test_all_bullish(self):
        messages = [_msg("Bullish") for _ in range(5)]
        result = _summarize_messages(messages)
        self.assertEqual(result["bullish_count"], 5)
        self.assertEqual(result["bearish_count"], 0)
        self.assertEqual(result["bullish_ratio"], 1.0)

    def test_mixed_sentiment(self):
        messages = [_msg("Bullish")] * 3 + [_msg("Bearish")] * 2
        result = _summarize_messages(messages)
        self.assertEqual(result["message_volume"], 5)
        self.assertEqual(result["bullish_count"], 3)
        self.assertEqual(result["bearish_count"], 2)
        self.assertEqual(result["bullish_ratio"], 0.6)  # 3/5

    def test_untagged_messages_excluded_from_ratio_not_counted_as_zero(self):
        """הודעה בלי תיוג סנטימנט לא נספרת בכלל ביחס - לא 'מזיקה' לציון, לא נחשבת בריש."""
        messages = [_msg("Bullish"), _msg(None), _msg(None), _msg(None)]
        result = _summarize_messages(messages)
        self.assertEqual(result["message_volume"], 4)
        self.assertEqual(result["tagged_count"], 1)
        self.assertEqual(result["bullish_ratio"], 1.0)  # 1/1 מהמתויגות, לא 1/4

    def test_no_tagged_messages_ratio_is_none(self):
        """אם אף הודעה לא תויגה - אין נתון, לא 0.5 'ניטרלי' מומצא."""
        messages = [_msg(None), _msg(None)]
        result = _summarize_messages(messages)
        self.assertIsNone(result["bullish_ratio"])

    def test_sentiment_of_missing_entities(self):
        self.assertIsNone(_sentiment_of({"id": 1, "body": "no entities key"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
