"""
test_live_similarity.py
=======================
בדיקות offline (ללא רשת וללא Claude API) לשכבת הדמיון החיה: בחירת תבנית
וטווח, "None" כערך לגיטימי, נרמול קבוצות חסרות, בדיקת העבר, ושילוב ה-Edge בדירוג.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.live_features import select_primary_pattern
from tools.live_similarity import combine, pattern_similarity, rank_candidates, numeric_group_similarity
from tools.pattern_stats import NONE_LABEL, apply_paired_edges, edge_for, paired_excess, simulate_trade, summarize


def _bar(o, h, l, c, v=1000):
    return {"date": "d", "open": o, "high": h, "low": l, "close": c, "volume": v}


def _feats(ticker, pattern=None, tf=None, tfs=None, sector="Tech", **numeric):
    base_numeric = {k: None for k in (
        "ret_5d", "ret_20d", "ret_60d", "dist_sma20_pct", "dist_sma50_pct", "dist_sma200_pct", "rsi_1d",
        "rsi_1h", "macd_hist_pct", "channel_pos", "risk_reward", "trend_alignment", "rel_volume_1d",
        "atr_pct_1d", "atr_pct_1h", "beta", "log_market_cap", "pe_ratio", "days_to_earnings")}
    base_numeric.update(numeric)
    return {
        "ticker": ticker, "price": 100.0, "support_1d": 90.0, "resistance_1d": 120.0,
        "primary_pattern": pattern, "primary_pattern_timeframe": tf, "pattern_timeframes": tfs or {},
        "patterns_by_timeframe": {}, "sector": sector, "industry": None, "numeric": base_numeric, "missing": [],
    }


class TestPatternTimeframes(unittest.TestCase):
    def test_none_is_a_legitimate_state(self):
        primary, tf, by_pattern = select_primary_pattern({"1D": [], "1h": [], "5m": []})
        self.assertIsNone(primary)
        self.assertIsNone(tf)
        self.assertEqual(by_pattern, {})

    def test_higher_timeframe_wins_and_all_timeframes_are_recorded(self):
        primary, tf, by_pattern = select_primary_pattern(
            {"5m": ["Range Bound"], "1h": ["Range Bound", "Inside Bar Consolidation"], "1D": ["Breakout Confirmation"]}
        )
        self.assertEqual((primary, tf), ("Breakout Confirmation", "1D"))
        self.assertEqual(by_pattern["Range Bound"], ["1h", "5m"])

    def test_both_without_pattern_count_as_a_match(self):
        self.assertEqual(pattern_similarity(_feats("A"), _feats("B")), 1.0)

    def test_same_pattern_on_same_timeframe_beats_different_timeframe(self):
        a = _feats("A", "Range Bound", "1D", {"Range Bound": ["1D"]})
        same = _feats("B", "Range Bound", "1D", {"Range Bound": ["1D"]})
        other_tf = _feats("C", "Range Bound", "5m", {"Range Bound": ["5m"]})
        self.assertGreater(pattern_similarity(a, same), pattern_similarity(a, other_tf))


class TestCombine(unittest.TestCase):
    def test_missing_group_is_dropped_and_weights_renormalized(self):
        full = {"technical_state": 1.0, "risk_profile": 1.0, "fundamentals": 1.0, "earnings": 1.0,
                "pattern": 1.0, "sector": 1.0, "behavior_correlation": 1.0}
        self.assertEqual(combine(full), 1.0)
        without_corr = dict(full, behavior_correlation=None)
        self.assertEqual(combine(without_corr), 1.0)  # לא יורד ל-0.8 - לא מנחשים ערך לקבוצה החסרה

    def test_numeric_group_ignores_missing_features(self):
        a, b = _feats("A", beta=1.0, atr_pct_1d=None), _feats("B", beta=1.0, atr_pct_1d=2.0)
        ranges = {"beta": (0.5, 1.5), "atr_pct_1d": (1.0, 3.0)}
        self.assertEqual(numeric_group_similarity(a, b, ["atr_pct_1d", "beta"], ranges), 1.0)


class TestBacktest(unittest.TestCase):
    def _flat(self, n=30):
        return [_bar(100, 101, 99, 100) for _ in range(n)]

    def test_target_hit_gives_target_r(self):
        candles = self._flat() + [_bar(100, 100, 100, 100)] + [_bar(100, 130, 100, 125)] + self._flat(15)
        # סטופ = שפל 20 הימים = 99 (סיכון 1), יעד 2R = 102: הנר אחרי הכניסה פוגע ביעד בלי לגעת בסטופ
        self.assertEqual(simulate_trade(candles, 30, horizon=10, target_r=2.0), 2.0)

    def test_stop_hit_first_is_minus_one_even_if_target_same_bar(self):
        candles = self._flat() + [_bar(100, 100, 100, 100)] + [_bar(100, 130, 50, 100)] + self._flat(15)
        self.assertEqual(simulate_trade(candles, 30, horizon=10, target_r=2.0), -1.0)

    def test_no_trade_when_not_enough_forward_bars(self):
        self.assertIsNone(simulate_trade(self._flat(31), 30, horizon=10, target_r=2.0))


class TestEdgeAndRanking(unittest.TestCase):
    def test_small_sample_is_neutral_and_flagged(self):
        stats = summarize({NONE_LABEL: [0.0] * 50, "Rare": [2.0] * 3})
        self.assertEqual(stats["Rare"]["edge"], 0.5)
        self.assertTrue(stats["Rare"]["insufficient_sample"])

    def test_edge_relative_to_baseline(self):
        stats = summarize({NONE_LABEL: [0.0] * 50, "Good": [1.0] * 50, "Bad": [-1.0] * 50})
        self.assertEqual(stats["Good"]["edge"], 1.0)
        self.assertEqual(stats["Bad"]["edge"], 0.0)
        self.assertEqual(edge_for(None, {"patterns": stats})["edge"], 0.5)  # None -> קו הבסיס

    def test_historical_edge_breaks_a_similarity_tie(self):
        stats = {"patterns": summarize({NONE_LABEL: [0.0] * 50, "Good": [1.0] * 50, "Bad": [-1.0] * 50})}
        universe = {
            "BASE": _feats("BASE", "Range Bound", "1D", {"Range Bound": ["1D"]}, beta=1.0),
            "GOOD": _feats("GOOD", "Good", "1D", {"Good": ["1D"]}, beta=1.0),
            "BAD": _feats("BAD", "Bad", "1D", {"Bad": ["1D"]}, beta=1.0),
        }
        ranking = rank_candidates("BASE", universe, {}, stats, top_n=2)
        self.assertEqual([r["ticker"] for r in ranking], ["GOOD", "BAD"])
        self.assertEqual(ranking[0]["similarity"], ranking[1]["similarity"])  # שוויון דמיון טהור

    def test_min_risk_reward_filters_out_missing_or_low(self):
        stats = {"patterns": {}}
        universe = {
            "BASE": _feats("BASE"),
            "LOW": _feats("LOW", risk_reward=1.0),
            "NONE": _feats("NONE"),
            "OK": _feats("OK", risk_reward=3.0),
        }
        ranking = rank_candidates("BASE", universe, {}, stats, min_risk_reward=2.0)
        self.assertEqual([r["ticker"] for r in ranking], ["OK"])


class TestPairedEdge(unittest.TestCase):
    def test_paired_excess_controls_for_ticker_drift(self):
        """מניה A בעלת סחף חיובי גדול, B שלילי: הפער נמדד בתוך כל מניה, לא על פני הכל."""
        per_ticker = {
            "A": {NONE_LABEL: [1.0] * 10, "P": [1.1] * 10},
            "B": {NONE_LABEL: [-1.0] * 10, "P": [-0.9] * 10},
        }
        res = paired_excess(per_ticker, "P")
        self.assertAlmostEqual(res["mean_excess_r"], 0.1, places=4)
        self.assertEqual(res["tickers"], 2)

    def test_too_few_tickers_gives_no_estimate(self):
        self.assertIsNone(paired_excess({"A": {NONE_LABEL: [1.0] * 10, "P": [1.0] * 10}}, "P")["mean_excess_r"])

    def test_apply_paired_edges_uses_scale_and_min_tickers(self):
        report = {
            "patterns": {"Bad": {"edge": 0.5, "insufficient_sample": True}, "Thin": {"edge": 0.5, "insufficient_sample": True}},
            "significance": {
                "Bad": {"tickers": 500, "mean_excess_r": -0.15, "t_stat": -9.0},
                "Thin": {"tickers": 5, "mean_excess_r": 0.5, "t_stat": 3.0},
            },
        }
        out = apply_paired_edges(report)["patterns"]
        self.assertEqual(out["Bad"]["edge"], 0.0)          # -0.15R = הקצה התחתון
        self.assertEqual(out["Thin"]["edge"], 0.5)         # מעט מדי מניות - נשאר ניטרלי


if __name__ == "__main__":
    unittest.main()
