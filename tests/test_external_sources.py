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

    def test_stocktwits_sentiment_counts(self):
        payload = {"symbol": {"watchlist_count": 5}, "messages": [
            {"body": "a", "entities": {"sentiment": {"basic": "Bullish"}}},
            {"body": "b", "entities": {"sentiment": {"basic": "Bullish"}}},
            {"body": "c", "entities": {"sentiment": {"basic": "Bearish"}}},
            {"body": "d", "entities": {"sentiment": None}},
        ]}
        r = x.parse_stocktwits(payload)
        self.assertEqual((r["bullish"], r["bearish"]), (2, 1))
        self.assertAlmostEqual(r["bullish_share_of_tagged"], 0.67, places=2)

    def test_tradingview_label_mapping(self):
        d = [0.0] * len(x._TV_COLUMNS)
        d[x._TV_COLUMNS.index("Recommend.All")] = 0.4
        r = x.parse_tradingview({"data": [{"s": "NASDAQ:NVDA", "d": d}]})
        self.assertEqual(r["recommendation_all"], "Buy")
        self.assertIsNone(x.parse_tradingview({"data": []}))

    def test_network_failure_is_reported_not_hidden(self):
        with mock.patch.object(x, "_http", side_effect=OSError("boom")):
            r = x.fetch_stocktwits("NVDA")
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


if __name__ == "__main__":
    unittest.main()
