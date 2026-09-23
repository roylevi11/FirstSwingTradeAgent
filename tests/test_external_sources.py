"""
test_external_sources.py
========================
בדיקות offline (ללא רשת וללא Claude API) למפרקי המקורות החינמיים,
ולכלל "המחיר תמיד חי" ב-watchlist/similarity.
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import external_sources as x
from tools.watchlist import WatchlistEntry, fetch_watchlist_entry
from tools.similarity import find_similar_stocks

FINVIZ_HTML = """
<div class="snapshot-td-label">P/E</div></td><td class="snapshot-td2"><div class="snapshot-td-content"><b>28.36</b></div></td>
<table id="news-table"><tr onclick="x">
<td width="130" align="right"> Today 01:02PM </td>
<td><a class="tab-link-news" href="https://e.com/a?x=1&amp;y=2" target="_blank"> Nvidia &amp; friends </a>
<span>(Reuters)</span></td></tr></table>
"""


class TestParsers(unittest.TestCase):
    def test_finviz_news_and_snapshot(self):
        r = x.parse_finviz(FINVIZ_HTML)
        self.assertEqual(r["news"][0]["headline"], "Nvidia & friends")
        self.assertEqual(r["news"][0]["source"], "Reuters")
        self.assertEqual(r["news"][0]["url"], "https://e.com/a?x=1&y=2")
        self.assertEqual(r["snapshot"]["P/E"], "28.36")

    def test_network_failure_is_reported_not_hidden(self):
        with mock.patch.object(x, "_http", side_effect=OSError("boom")):
            r = x.fetch_finviz("NVDA")
        self.assertFalse(r["available"])
        self.assertIn("boom", r["error"])


class TestLivePrice(unittest.TestCase):
    def test_watchlist_uses_live_price_and_flags_stale_levels(self):
        with mock.patch("tools.market_data.fetch_live_price", return_value=337.7):
            e = fetch_watchlist_entry("AAPL")
        self.assertEqual(e.current_price, 337.7)  # לא 220.50 מהקובץ
        self.assertEqual(e.price_source, "live")
        self.assertEqual(e.levels_status, "PRICE_ABOVE_RESISTANCE")

    def test_live_price_unavailable_does_not_fall_back_to_csv(self):
        with mock.patch("tools.market_data.fetch_live_price", return_value=None):
            e = fetch_watchlist_entry("AAPL")
        self.assertIsNone(e.current_price)

    def test_similarity_ignores_rr_when_price_outside_levels(self):
        entries = [
            WatchlistEntry("A", True, "A", "Tech", 100.0, 90.0, 130.0, 40, "P", "t"),
            WatchlistEntry("B", True, "B", "Tech", 300.0, 90.0, 130.0, 40, "P", "t"),  # מחיר מעל ההתנגדות
        ]
        res = find_similar_stocks("A", entries=entries)
        self.assertIsNone(res[0].risk_reward_ratio)


class TestLiveSimilarityInputs(unittest.TestCase):
    def test_live_enrichment_replaces_every_csv_analysis_field(self):
        """בשכבת הדמיון מהקובץ נשארת רק זהות המניה; כל השאר נגזר חי."""
        from tools import watchlist as w
        from tools.multi_timeframe import TimeframeSnapshot
        from tools.earnings import EarningsInfo

        snap = TimeframeSnapshot("1D", 300, 250.0, 240.0, 270.0, ["Breakout Confirmation", "Range Bound"], {})
        w._LIVE_CACHE.clear()
        with mock.patch("tools.multi_timeframe.analyze_timeframe", return_value=snap),              mock.patch("tools.earnings.fetch_earnings_calendar", return_value=EarningsInfo("TSLA", "2026-10-20", 20, True)),              mock.patch("tools.market_data.fetch_live_price", return_value=251.5):
            entries = w.load_all_watchlist_entries(live=True)
        tsla = next(e for e in entries if e.ticker == "TSLA")
        self.assertEqual(tsla.current_price, 251.5)      # לא 250.00 מהקובץ
        self.assertEqual((tsla.key_support, tsla.key_resistance), (240.0, 270.0))
        self.assertEqual(tsla.technical_pattern, "Breakout Confirmation")  # לא Range Bound מהקובץ
        self.assertEqual(tsla.days_to_earnings, 20)      # לא 45 מהקובץ
        self.assertEqual(tsla.sector, "Consumer Cyclical")  # זהות נשמרת
        self.assertEqual(tsla.data_source, "live")
        w._LIVE_CACHE.clear()

    def test_failed_live_data_is_none_not_csv_fallback(self):
        from tools import watchlist as w
        from tools.earnings import EarningsInfo

        w._LIVE_CACHE.clear()
        with mock.patch("tools.multi_timeframe.analyze_timeframe", side_effect=RuntimeError("no data")),              mock.patch("tools.earnings.fetch_earnings_calendar", return_value=EarningsInfo("X", None, None, False)),              mock.patch("tools.market_data.fetch_live_price", return_value=None):
            entries = w.load_all_watchlist_entries(live=True)
        nvda = next(e for e in entries if e.ticker == "NVDA")
        self.assertIsNone(nvda.current_price)
        self.assertIsNone(nvda.key_support)
        self.assertIsNone(nvda.technical_pattern)
        self.assertIsNone(nvda.days_to_earnings)
        w._LIVE_CACHE.clear()


if __name__ == "__main__":
    unittest.main()
