"""
test_mentor_pipeline.py
========================
בודק את _parse_extraction_response ו-_idea_to_watchlist_row - הלוגיקה
הטהורה שלא תלויה ב-API חי או ברשת. כולל בדיקה מכוונת שתשובה שגויה
מ-Claude (JSON לא תקני) לא מקריסה את הצינור אלא מוחזרת כרשימה ריקה.
"""

import sys
import os
import unittest
import tempfile
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.mentor_pipeline import (
    _parse_extraction_response,
    _idea_to_watchlist_row,
    append_ideas_to_watchlist,
)


class TestParseExtractionResponse(unittest.TestCase):
    def test_clean_json_array(self):
        raw = '[{"Ticker": "NVDA", "Company_Name": "NVIDIA"}]'
        result = _parse_extraction_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Ticker"], "NVDA")

    def test_json_wrapped_in_markdown_fence(self):
        raw = '```json\n[{"Ticker": "AAPL"}]\n```'
        result = _parse_extraction_response(raw)
        self.assertEqual(result[0]["Ticker"], "AAPL")

    def test_malformed_json_returns_empty_list_not_crash(self):
        """זה בדיוק המקרה שהיה עלול 'להפיל' את כל הצינור בשקט אם לא נבדק."""
        raw = "מצטער, לא הצלחתי לחלץ נתונים ברורים מהתמלול הזה."
        result = _parse_extraction_response(raw)
        self.assertEqual(result, [])

    def test_json_object_not_array_returns_empty(self):
        raw = '{"Ticker": "NVDA"}'  # אובייקט בודד, לא מערך - לא בפורמט הנדרש
        result = _parse_extraction_response(raw)
        self.assertEqual(result, [])


class TestIdeaToWatchlistRow(unittest.TestCase):
    def test_full_idea_mapping(self):
        idea = {
            "Ticker": "nvda", "Company_Name": "NVIDIA Corp", "Sector": "Technology",
            "Support_Key": 118.0, "Resistance_Key": 140.0, "Pattern_Technical": "Gap Fill",
        }
        row = _idea_to_watchlist_row(idea, "Raz_Gamliel")
        self.assertEqual(row["Ticker"], "NVDA")  # אותיות גדולות
        self.assertEqual(row["Source_Tag"], "Raz_Gamliel_Mentor")
        self.assertEqual(row["Current_Price"], "")  # נשאר ריק בכוונה - יגיע חי
        self.assertEqual(row["Days_To_Earnings"], "")  # נשאר ריק בכוונה
        self.assertEqual(row["Key_Support"], 118.0)

    def test_missing_optional_fields_become_empty_string_not_none(self):
        """None בתוך שורת CSV נכתב כ-'None' מילולי - חייב לצאת מחרוזת ריקה."""
        idea = {"Ticker": "XYZ"}
        row = _idea_to_watchlist_row(idea, "Assaf_Marciano")
        self.assertEqual(row["Company_Name"], "")
        self.assertEqual(row["Key_Support"], "")


class TestAppendToWatchlist(unittest.TestCase):
    def test_skips_ideas_without_ticker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_watchlist.csv")
            ideas = [{"Ticker": "NVDA"}, {"Company_Name": "No ticker here"}, {"Ticker": ""}]
            added = append_ideas_to_watchlist(ideas, "Test_Mentor", csv_path=path)
            self.assertEqual(added, 1)  # רק NVDA - השאר בלי טיקר תקין

    def test_creates_header_on_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_watchlist.csv")
            append_ideas_to_watchlist([{"Ticker": "AAPL"}], "Test_Mentor", csv_path=path)
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Ticker"], "AAPL")
            self.assertEqual(rows[0]["Source_Tag"], "Test_Mentor_Mentor")


if __name__ == "__main__":
    unittest.main(verbosity=2)
