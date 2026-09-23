"""
live_similarity.py
==================
שכבת הדמיון החיה והמקצועית. מחליפה את הדמיון הישן (tools/similarity.py,
שנשאר לצורכי הקורס ולבדיקות עבודה 3) בגרסה שכל נתוניה חיים:

1. מאפיינים חיים עשירים לכל מניה (tools/live_features.py): מומנטום, מגמה,
   RSI, תנודתיות, יחס סיכון/סיכוי חי, בטא, שווי, סקטור/תעשייה, דוחות,
   ותבנית + הטווחים (5m..1W) שבהם היא מופיעה. "אין תבנית" (None) הוא ערך לגיטימי.
2. קבוצות מאפיינים עם משקלים גלויים (config/similarity_config.py). קבוצה שחסר
   בה נתון נושרת מהחישוב והמשקלים מנורמלים מחדש - לא משלימים ערך מומצא.
3. קורלציית תשואות יומיות היסטורית - מדד סטטיסטי ל"מתנהגות דומה".
4. תיעדוף לפי מה שעבד בעבר (tools/pattern_stats.py): ה-Edge ההיסטורי של תבנית
   המועמדת (תוחלת ב-R מבדיקת עבר) משולב בדירוג הסופי:
      rank_score = (1 - EDGE_WEIGHT) * similarity + EDGE_WEIGHT * historical_edge

הדמיון הוא כלי איתור בלבד: לעסקה עצמה עדיין נדרשים analyze_multi_timeframe ו-evaluate_trade.
"""

from config.similarity_config import EDGE_WEIGHT, GROUP_WEIGHTS

NUMERIC_GROUPS: dict[str, list[str]] = {
    "technical_state": [
        "ret_5d", "ret_20d", "ret_60d", "dist_sma20_pct", "dist_sma50_pct", "dist_sma200_pct",
        "rsi_1d", "rsi_1h", "macd_hist_pct", "channel_pos", "risk_reward", "trend_alignment", "rel_volume_1d",
    ],
    "risk_profile": ["atr_pct_1d", "atr_pct_1h", "beta"],
    "fundamentals": ["log_market_cap", "pe_ratio"],
    "earnings": ["days_to_earnings"],
}


def _ranges(universe: dict[str, dict]) -> dict[str, tuple[float, float]]:
    """טווח (min,max) לכל מאפיין מספרי על פני כל המניות - לנרמול מרחקים ל-[0,1]."""
    ranges: dict[str, tuple[float, float]] = {}
    for feats in universe.values():
        for k, v in feats["numeric"].items():
            if v is None:
                continue
            lo, hi = ranges.get(k, (v, v))
            ranges[k] = (min(lo, v), max(hi, v))
    return ranges


def numeric_group_similarity(a: dict, b: dict, keys: list[str], ranges: dict) -> float | None:
    """1 - מרחק L1 ממוצע מנורמל על המאפיינים ששני הצדדים מכירים. None אם אין אף אחד."""
    diffs = []
    for k in keys:
        va, vb = a["numeric"].get(k), b["numeric"].get(k)
        if va is None or vb is None or k not in ranges:
            continue
        lo, hi = ranges[k]
        diffs.append(0.0 if hi == lo else abs(va - vb) / (hi - lo))
    return round(1 - sum(diffs) / len(diffs), 4) if diffs else None


def _pattern_tokens(feats: dict) -> set[str]:
    return {f"{p}@{tf}" for p, tfs in feats["pattern_timeframes"].items() for tf in tfs}


def pattern_similarity(a: dict, b: dict) -> float:
    """
    60%: אותה תבנית ראשית (שתיהן None נחשב התאמה מלאה - "בלי תבנית" הוא מצב).
    40%: Jaccard על כל צמדי (תבנית@טווח) - נותן קרדיט לתבנית זהה שמופיעה באותם טווחים.
    """
    same_primary = 1.0 if a["primary_pattern"] == b["primary_pattern"] else 0.0
    ta, tb = _pattern_tokens(a), _pattern_tokens(b)
    jaccard = 1.0 if not ta and not tb else len(ta & tb) / len(ta | tb)
    return round(0.6 * same_primary + 0.4 * jaccard, 4)


def sector_similarity(a: dict, b: dict) -> float | None:
    if not a.get("sector") or not b.get("sector"):
        return None
    industry = 1.0 if a.get("industry") and a.get("industry") == b.get("industry") else 0.0
    return round(0.6 * (1.0 if a["sector"] == b["sector"] else 0.0) + 0.4 * industry, 4)


def combine(groups: dict[str, float | None]) -> float:
    """ממוצע משוקלל של הקבוצות הזמינות; משקלים מנורמלים מחדש על מה שקיים."""
    available = {g: s for g, s in groups.items() if s is not None}
    total = sum(GROUP_WEIGHTS[g] for g in available)
    return round(sum(GROUP_WEIGHTS[g] * s for g, s in available.items()) / total, 4) if total else 0.0


def similarity_between(base: dict, cand: dict, ranges: dict, corr: float | None) -> tuple[float, dict]:
    groups: dict[str, float | None] = {
        g: numeric_group_similarity(base, cand, keys, ranges) for g, keys in NUMERIC_GROUPS.items()
    }
    groups["pattern"] = pattern_similarity(base, cand)
    groups["sector"] = sector_similarity(base, cand)
    groups["behavior_correlation"] = None if corr is None else round((corr + 1) / 2, 4)
    return combine(groups), groups


def rank_candidates(
    base_ticker: str,
    universe: dict[str, dict],
    correlations: dict[str, dict[str, float]],
    stats: dict,
    top_n: int = 5,
    min_risk_reward: float | None = None,
) -> list[dict]:
    """
    ליבת הדירוג, ללא רשת (כל הקלטים מוזרקים) - כך אפשר לבדוק אותה בדיוק.
    universe חייב לכלול את base_ticker.
    """
    from tools.pattern_stats import edge_for

    base = universe[base_ticker]
    ranges = _ranges(universe)
    results = []
    for t, cand in universe.items():
        if t == base_ticker:
            continue
        sim, groups = similarity_between(base, cand, ranges, correlations.get(base_ticker, {}).get(t))
        edge = edge_for(cand["primary_pattern"], stats)
        rank_score = round((1 - EDGE_WEIGHT) * sim + EDGE_WEIGHT * edge["edge"], 4)
        rr = cand["numeric"].get("risk_reward")
        if min_risk_reward is not None and (rr is None or rr < min_risk_reward):
            continue
        results.append(
            {
                "ticker": t,
                "rank_score": rank_score,
                "similarity": sim,
                "historical_edge": edge,
                "components": groups,
                "primary_pattern": cand["primary_pattern"],
                "pattern_timeframe": cand["primary_pattern_timeframe"],
                "pattern_timeframes": cand["pattern_timeframes"],
                "risk_reward_ratio": rr,
                "price": cand["price"],
                "support_1d": cand["support_1d"],
                "resistance_1d": cand["resistance_1d"],
                "sector": cand["sector"],
                "missing_features": cand["missing"],
            }
        )
    results.sort(key=lambda r: r["rank_score"], reverse=True)
    return results[:top_n]


def find_similar_live(base_ticker: str, top_n: int = 5, min_risk_reward: float | None = None) -> dict:
    """נקודת הכניסה: כל הנתונים נשלפים חי (או ממטמון של 10 דקות), והדירוג מחושב."""
    from tools.live_features import build_features, load_universe_features, return_correlations
    from tools.pattern_stats import load_pattern_stats
    from tools.watchlist import load_all_watchlist_entries

    base_ticker = base_ticker.upper()
    identity = {e.ticker: e for e in load_all_watchlist_entries()}
    tickers = list(identity)

    universe = load_universe_features(tickers)
    if base_ticker not in universe:  # מניה מחוץ לרשימה יכולה להיות בסיס (לא מועמדת)
        universe[base_ticker] = build_features(base_ticker)

    corr = return_correlations(sorted(universe))
    stats = load_pattern_stats()
    ranking = rank_candidates(base_ticker, universe, corr, stats, top_n=top_n, min_risk_reward=min_risk_reward)
    for r in ranking:
        r["company_name"] = identity[r["ticker"]].company_name if r["ticker"] in identity else None

    base = universe[base_ticker]
    return {
        "base": {
            "ticker": base_ticker,
            "price": base["price"],
            "primary_pattern": base["primary_pattern"],
            "pattern_timeframe": base["primary_pattern_timeframe"],
            "pattern_timeframes": base["pattern_timeframes"],
            "sector": base["sector"],
        },
        "ranking": ranking,
        "weights": GROUP_WEIGHTS,
        "edge_weight": EDGE_WEIGHT,
        "pattern_stats_generated_at": stats.get("generated_at"),
        "caveat": stats.get("caveat"),
    }
