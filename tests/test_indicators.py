"""
test_indicators.py
===================
בודק את tools/indicators.py עם נתונים סינתטיים שהתוצאה שלהם ידועה
מראש בוודאות (חשבון פשוט, או תכונות מתמטיות חד-משמעיות כמו "RSI=100
כשכל השינויים חיוביים") - לא תלוי ברשת.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.indicators import calc_sma, calc_ema, calc_rsi, calc_atr, calc_relative_volume


def _candle(close, high=None, low=None, volume=1000):
    return {
        "date": "2026-01-01",
        "open": close,
        "high": high if high is not None else close + 1,
        "low": low if low is not None else close - 1,
        "close": close,
        "volume": volume,
    }


class TestIndicators(unittest.TestCase):
    def test_sma_simple_average(self):
        candles = [_candle(c) for c in [10, 20, 30, 40, 50]]
        self.assertEqual(calc_sma(candles, 3), 40.0)  # (30+40+50)/3

    def test_sma_insufficient_data_returns_none(self):
        candles = [_candle(c) for c in [10, 20]]
        self.assertIsNone(calc_sma(candles, 5))

    def test_ema_weighs_recent_prices_more(self):
        # רצף לא-ליניארי (מאיץ כלפי מעלה) - כדי ש-EMA (שנותן משקל גבוה יותר
        # לנרות אחרונים) יסטה בבירור מעל ה-SMA הפשוט
        candles = [_candle(c) for c in [10, 10, 10, 10, 10, 12, 15, 19, 24, 30]]
        ema = calc_ema(candles, 5)
        sma = calc_sma(candles, 5)
        self.assertGreater(ema, sma)
        self.assertLessEqual(ema, candles[-1]["close"])

    def test_rsi_all_gains_is_100(self):
        """מגמה עולה טהורה (כל שינוי חיובי) -> אין הפסדים בכלל -> RSI = 100."""
        candles = [_candle(c) for c in range(10, 40)]  # עולה כל יום
        self.assertEqual(calc_rsi(candles, period=14), 100.0)

    def test_rsi_all_losses_is_0(self):
        """מגמה יורדת טהורה -> אין רווחים בכלל -> RSI = 0."""
        candles = [_candle(c) for c in range(40, 10, -1)]  # יורד כל יום
        self.assertEqual(calc_rsi(candles, period=14), 0.0)

    def test_atr_constant_range(self):
        """אם כל נר יש טווח High-Low קבוע של 10, ואין פערים בין נרות - ATR אמור להתכנס ל-10."""
        candles = [_candle(close=100, high=105, low=95) for _ in range(20)]
        atr = calc_atr(candles, period=14)
        self.assertAlmostEqual(atr, 10.0, places=1)

    def test_relative_volume_double(self):
        """20 ימים בנפח 1000, יום אחרון בנפח 2000 -> נפח יחסי = 2.0."""
        candles = [_candle(c, volume=1000) for c in range(1, 21)] + [_candle(21, volume=2000)]
        self.assertEqual(calc_relative_volume(candles, period=20), 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
