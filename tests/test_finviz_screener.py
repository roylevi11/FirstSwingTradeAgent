"""
test_finviz_screener.py
========================
בודק רק את _row_to_screened_stock - לוגיקת ההמרה שלנו, עם נתונים
מדומים שמחקים את הפורמט שמחזירה finvizfinance. לא בודק את הספרייה
עצמה או קריאת רשת אמיתית - זה ידרוש הרצה אצלך (ראו README).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.finviz_screener import _row_to_screened_stock, ScreenedStock


class TestRowConversion(unittest.TestCase):
    def test_typical_row(self):
        row = {"Ticker": "nvda", "Company": "NVIDIA Corp", "Sector": "Technology",
               "Price": "224.57", "Change": "4.03%", "Volume": "45000000"}
        result = _row_to_screened_stock(row)
        self.assertEqual(result.ticker, "NVDA")  # תמיד אותיות גדולות
        self.assertEqual(result.company_name, "NVIDIA Corp")
        self.assertEqual(result.price, 224.57)
        self.assertEqual(result.change_pct, 4.03)  # ה-% הוסר
        self.assertEqual(result.volume, 45000000)
        self.assertEqual(result.source_tag, "Finviz_Screen")  # תיוג אוטומטי לשכבת הדמיון

    def test_missing_fields_become_none_not_crash(self):
        """שדה חסר או '-' (כפי ש-Finviz מציג נתון לא זמין) -> None, לא שגיאה ולא ניחוש."""
        row = {"Ticker": "XYZ", "Company": "", "Sector": None, "Price": "-", "Change": "-", "Volume": ""}
        result = _row_to_screened_stock(row)
        self.assertEqual(result.ticker, "XYZ")
        self.assertIsNone(result.company_name)
        self.assertIsNone(result.price)
        self.assertIsNone(result.change_pct)
        self.assertIsNone(result.volume)

    def test_negative_change_parsed_correctly(self):
        row = {"Ticker": "ABC", "Change": "-2.15%"}
        result = _row_to_screened_stock(row)
        self.assertEqual(result.change_pct, -2.15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
