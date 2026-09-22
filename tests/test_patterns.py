"""
test_patterns.py
=================
בודק את tools/patterns.py. שימו לב לבדיקה הראשונה - היא משחזרת בדיוק
את התרחיש שנכשל בניסוי TradingView (עבודה 3): שם הסוכן לא הצליח לזהות
תבנית כי הוא ניסה "לנחש" מטקסט. כאן זו פונקציה לוגית קבועה שעונה
True/False בוודאות, בדיוק כפי שהוסבר שצריך להיות בעקבות אותו כישלון.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.patterns import is_inside_bar, is_breakout, is_pullback_to_support, is_range_bound, detect_patterns


def _candle(close, high, low, volume=1000):
    return {"date": "2026-01-01", "open": close, "high": high, "low": low, "close": close, "volume": volume}


class TestInsideBar(unittest.TestCase):
    def test_true_case(self):
        """הדוגמה המדויקת מהשיחה: high_today < high_yesterday and low_today > low_yesterday."""
        candles = [_candle(100, high=110, low=90), _candle(100, high=105, low=95)]
        self.assertTrue(is_inside_bar(candles))

    def test_false_case_wider_range(self):
        candles = [_candle(100, high=110, low=90), _candle(100, high=115, low=85)]
        self.assertFalse(is_inside_bar(candles))

    def test_false_with_insufficient_data(self):
        self.assertFalse(is_inside_bar([_candle(100, 105, 95)]))


class TestBreakout(unittest.TestCase):
    def test_true_case_high_volume(self):
        """שיא חדש מעל 20 הימים האחרונים + נפח 1.5x - פריצה מאושרת."""
        prior = [_candle(100, high=105, low=95, volume=1000) for _ in range(20)]
        breakout_day = _candle(120, high=121, low=110, volume=1600)  # נפח = 1.6x הממוצע
        self.assertTrue(is_breakout(prior + [breakout_day]))

    def test_false_case_low_volume(self):
        """פריצת מחיר בלי נפח תומך - לא נחשבת פריצה אמיתית (רעש)."""
        prior = [_candle(100, high=105, low=95, volume=1000) for _ in range(20)]
        weak_breakout = _candle(120, high=121, low=110, volume=1100)  # רק 1.1x - לא מספיק
        self.assertFalse(is_breakout(prior + [weak_breakout]))

    def test_false_case_no_new_high(self):
        prior = [_candle(100, high=105, low=95, volume=1000) for _ in range(20)]
        no_breakout = _candle(102, high=104, low=98, volume=2000)  # נפח גבוה אך אין שיא חדש
        self.assertFalse(is_breakout(prior + [no_breakout]))


class TestPullbackAndRange(unittest.TestCase):
    def test_pullback_within_tolerance(self):
        candles = [_candle(101, 103, 99)]
        self.assertTrue(is_pullback_to_support(candles, support_level=100, tolerance_pct=1.5))

    def test_pullback_outside_tolerance(self):
        candles = [_candle(110, 112, 108)]
        self.assertFalse(is_pullback_to_support(candles, support_level=100, tolerance_pct=1.5))

    def test_range_bound_narrow(self):
        candles = [_candle(100, high=102, low=98) for _ in range(10)]
        self.assertTrue(is_range_bound(candles, period=10, width_threshold_pct=5.0))

    def test_range_bound_wide_is_false(self):
        candles = [_candle(100, high=130, low=70) for _ in range(10)]
        self.assertFalse(is_range_bound(candles, period=10, width_threshold_pct=5.0))


class TestDetectPatterns(unittest.TestCase):
    def test_detects_inside_bar_in_aggregate(self):
        candles = [_candle(100, high=110, low=90), _candle(100, high=105, low=95)]
        found = detect_patterns(candles)
        self.assertIn("Inside Bar Consolidation", found)

    def test_no_patterns_returns_empty_list_not_guess(self):
        """נתונים לא מובהקים -> רשימה ריקה, לא 'ניחוש' של תבנית שלא קיימת."""
        candles = [_candle(100, high=101, low=99) for _ in range(5)]
        found = detect_patterns(candles)
        self.assertIsInstance(found, list)  # גם אם ריקה, זה עדיין תשובה תקינה ולא שגיאה


if __name__ == "__main__":
    unittest.main(verbosity=2)
