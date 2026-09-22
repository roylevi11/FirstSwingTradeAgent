"""
test_similarity.py
===================
בודק את tools/similarity.py מול מערך הנתונים המקורי מעבודה 3 (8 מניות).

הערה חשובה לשקיפות: הציונים המספריים המדויקים (כמו 0.985 שדווח בעבודה 3)
תלויים בפרטי מימוש שלא צוינו במלואם בשיחה עם Gemini (סדר הפיצ'רים המדויק,
שיטת הדילוג/Bucketing לקרבת דוחות בג'קארד וכו'). לכן הבדיקות כאן בודקות
את **הממצאים האיכותיים** שכן מתועדים ומאוששים באופן חד-משמעי, ולא דורשות
התאמה מדויקת ל-4 ספרות אחרי הנקודה של מימוש AI Studio.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.watchlist import WatchlistEntry
from tools.similarity import find_similar_stocks, find_valid_alternative, jaccard_similarity


def _work3_entries():
    """משחזר בדיוק את watchlist_v2.csv מעבודה 3."""
    return [
        WatchlistEntry("NVDA", True, "NVIDIA Corp", "Technology", 128.40, 118.00, 140.00, 76, "Inside Bar Consolidation", "Core"),
        WatchlistEntry("AMD", True, "AMD", "Technology", 155.00, 142.00, 170.00, 45, "Inside Bar Consolidation", "Core"),
        WatchlistEntry("AAPL", True, "Apple Inc", "Technology", 220.50, 215.00, 232.00, 28, "Breakout Confirmation", "Core"),
        WatchlistEntry("MSFT", True, "Microsoft", "Technology", 415.00, 405.00, 430.00, 35, "Pullback to Support", "Core"),
        WatchlistEntry("TSLA", True, "Tesla", "Consumer Cyclical", 250.00, 240.00, 260.00, 45, "Range Bound", "Core"),
        WatchlistEntry("AMZN", True, "Amazon", "Consumer Cyclical", 185.00, 175.00, 205.00, 30, "Breakout Confirmation", "Core"),
        WatchlistEntry("XOM", True, "Exxon", "Energy", 115.00, 110.00, 125.00, 60, "Pullback to Support", "Core"),
        WatchlistEntry("CVX", True, "Chevron", "Energy", 150.00, 144.00, 162.00, 55, "Pullback to Support", "Core"),
    ]


class TestSimilarityEngine(unittest.TestCase):
    def test_amd_is_top_cosine_match_for_nvda(self):
        """עבודה 3: AMD היא המניה הכי דומה ל-NVDA בדמיון קוסינוס (כולל סקטור)."""
        results = find_similar_stocks("NVDA", method="cosine", include_sector=True, entries=_work3_entries())
        self.assertEqual(results[0].ticker, "AMD")

    def test_amd_perfect_jaccard_match(self):
        """עבודה 3: AMD מקבלת ציון ג'קארד מושלם של 1.00 מול NVDA (זהות בסקטור+תבנית)."""
        entries = _work3_entries()
        nvda = next(e for e in entries if e.ticker == "NVDA")
        amd = next(e for e in entries if e.ticker == "AMD")
        self.assertEqual(jaccard_similarity(nvda, amd), 1.0)

    def test_amd_is_top_jaccard_match(self):
        results = find_similar_stocks("NVDA", method="jaccard", entries=_work3_entries())
        self.assertEqual(results[0].ticker, "AMD")
        self.assertEqual(results[0].score, 1.0)

    def test_removing_sector_improves_xom_ranking(self):
        """עבודה 3: הסרת תכונת הסקטור משפרת את דירוג XOM בדמיון קוסינוס (ממצא מרכזי)."""
        entries = _work3_entries()
        with_sector = find_similar_stocks("NVDA", method="cosine", include_sector=True, top_n=10, entries=entries)
        without_sector = find_similar_stocks("NVDA", method="cosine", include_sector=False, top_n=10, entries=entries)

        xom_score_with = next(r.score for r in with_sector if r.ticker == "XOM")
        xom_score_without = next(r.score for r in without_sector if r.ticker == "XOM")
        self.assertGreater(xom_score_without, xom_score_with)

        xom_rank_with = [r.ticker for r in with_sector].index("XOM")
        xom_rank_without = [r.ticker for r in without_sector].index("XOM")
        self.assertLess(xom_rank_without, xom_rank_with)  # מספר קטן יותר = מקום גבוה יותר בדירוג

    def test_find_valid_alternative_matches_work3_narrative(self):
        """
        עבודה 3, תרחיש לפני/אחרי: NVDA נפסלת (R:R 1.12). AMD הכי דומה אך גם
        נפסלת (R:R 1.15). האלטרנטיבה התקינה שנמצאת בפועל היא AAPL (R:R 2.09).
        """
        alt = find_valid_alternative("NVDA", min_risk_reward=2.0, entries=_work3_entries())
        self.assertIsNotNone(alt)
        self.assertEqual(alt.ticker, "AAPL")
        self.assertGreaterEqual(alt.risk_reward_ratio, 2.0)

    def test_no_valid_alternative_returns_none(self):
        """אם אף מניה לא עומדת בסף - מוחזר None, לא ניחוש/ברירת מחדל שרירותית."""
        alt = find_valid_alternative("NVDA", min_risk_reward=99.0, entries=_work3_entries())
        self.assertIsNone(alt)

    def test_unknown_ticker_returns_empty(self):
        results = find_similar_stocks("NOSUCHTICKER", entries=_work3_entries())
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
