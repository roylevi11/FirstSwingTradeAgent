"""
test_multi_timeframe.py
========================
בודק את resample_candles ו-calc_support_resistance עם נתונים סינתטיים.
זהו החלק היחיד ב-multi_timeframe.py שניתן לבדוק בלי רשת - analyze_
multi_timeframe עצמו דורש yfinance חי ונבדק רק אצל המשתמש.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.multi_timeframe import resample_candles, calc_support_resistance


def _candle(close, high, low, volume=1000, date="2026-01-01"):
    return {"date": date, "open": close, "high": high, "low": low, "close": close, "volume": volume}


class TestResampleCandles(unittest.TestCase):
    def test_four_hourly_candles_become_one(self):
        """4 נרות של שעה -> נר אחד של 4 שעות, עם High/Low/Volume נכונים."""
        hourly = [
            _candle(100, high=102, low=99, volume=100),
            _candle(101, high=103, low=100, volume=150),
            _candle(99, high=101, low=97, volume=200),   # השפל הכי נמוך כאן
            _candle(105, high=106, low=104, volume=120),  # השיא הכי גבוה כאן
        ]
        result = resample_candles(hourly, factor=4)
        self.assertEqual(len(result), 1)
        bar = result[0]
        self.assertEqual(bar["open"], 100)     # מהנר הראשון
        self.assertEqual(bar["close"], 105)    # מהנר האחרון
        self.assertEqual(bar["high"], 106)     # המקסימום מכל הקבוצה
        self.assertEqual(bar["low"], 97)       # המינימום מכל הקבוצה
        self.assertEqual(bar["volume"], 570)   # הסכום

    def test_incomplete_trailing_group_dropped(self):
        """9 נרות בפקטור 4 -> קבוצה אחרונה לא שלמה (נר בודד) מושמטת, לא מוצגת כחלקית."""
        candles = [_candle(100 + i, high=101 + i, low=99 + i) for i in range(9)]
        result = resample_candles(candles, factor=4)
        self.assertEqual(len(result), 2)  # רק 2 קבוצות שלמות מתוך 9 (8 נרות בשימוש, 1 מושמט)

    def test_factor_one_returns_unchanged(self):
        candles = [_candle(100, 101, 99)]
        self.assertEqual(resample_candles(candles, factor=1), candles)

    def test_empty_input(self):
        self.assertEqual(resample_candles([], factor=4), [])


class TestSupportResistance(unittest.TestCase):
    def test_basic_donchian_channel(self):
        candles = [
            _candle(100, high=105, low=95),
            _candle(102, high=110, low=98),   # השיא הגלובלי כאן (110)
            _candle(98, high=101, low=90),    # השפל הגלובלי כאן (90)
        ]
        support, resistance = calc_support_resistance(candles, lookback=10)
        self.assertEqual(support, 90)
        self.assertEqual(resistance, 110)

    def test_lookback_window_limits_scope(self):
        """נר קיצוני מחוץ לחלון ה-lookback לא אמור להשפיע על התוצאה."""
        old_extreme = _candle(100, high=999, low=1)  # קיצוני אך ישן
        recent = [_candle(100, high=105, low=95) for _ in range(5)]
        candles = [old_extreme] + recent
        support, resistance = calc_support_resistance(candles, lookback=5)  # רק 5 האחרונים
        self.assertEqual(resistance, 105)  # לא 999
        self.assertEqual(support, 95)      # לא 1

    def test_insufficient_data_returns_none(self):
        support, resistance = calc_support_resistance([_candle(100, 101, 99)])
        self.assertIsNone(support)
        self.assertIsNone(resistance)


class TestTimeframeConfig(unittest.TestCase):
    def test_seven_timeframes_configured(self):
        from tools.multi_timeframe import TIMEFRAME_CONFIGS
        labels = [tf["label"] for tf in TIMEFRAME_CONFIGS]
        self.assertEqual(labels, ["5m", "15m", "30m", "1h", "4h", "1D", "1W"])

    def test_weekly_not_treated_as_intraday(self):
        """1W (yfinance interval '1wk') לא אמור להיתפס במגבלת 59 הימים של נתונים תוך-יומיים."""
        from tools.market_data import INTRADAY_INTERVALS
        self.assertNotIn("1wk", INTRADAY_INTERVALS)
        self.assertNotIn("1d", INTRADAY_INTERVALS)
        self.assertIn("60m", INTRADAY_INTERVALS)  # משמש גם עבור 1h וגם עבור 4h (resample)


if __name__ == "__main__":
    unittest.main(verbosity=2)
