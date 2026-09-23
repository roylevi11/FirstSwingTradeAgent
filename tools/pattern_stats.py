"""
pattern_stats.py
================
"דוגמאות עבר שעבדו לפי סטטיסטיקה": בדיקת עבר (backtest) של גלאי התבניות
שלנו על היסטוריה יומית של ~1,100 מניות S&P 500 + נאסד"ק (שווי מעל $2B),
דרך `python -m tools.pattern_stats`. לכל תבנית (וגם ל-"NONE" -
ימים בלי תבנית, כקו בסיס) מחושב מה קרה בפועל אחרי כל הופעה:

  כניסה  = סגירת יום האיתות
  סטופ   = שפל 20 הימים שקדמו לאיתות (אותה שיטת Donchian של analyze_multi_timeframe)
  יעד    = כניסה + BACKTEST_TARGET_R * סיכון
  אופק   = BACKTEST_HORIZON_DAYS ימי מסחר. אם סטופ ויעד באותו נר - מניחים סטופ
           קודם (הנחה שמרנית). אם אף אחד לא נפגע - תוצאה = שינוי הסגירה באופק, ביחידות R.

התוצר: לכל תבנית - מספר מקרים, אחוז הצלחה (R>0), תוחלת ב-R, ואחוז פגיעה
ביעד. ה-Edge הוא תוחלת התבנית ביחס לקו הבסיס, מנורמלת ל-[0,1].

מגבלות (מתועדות בכוונה - זו לא הבטחת רווח):
- Survivorship Bias: רשימות המדדים הנוכחיות (מניות שכבר "שרדו"). מדגם רשימת המעקב בלבד
  התברר כמוטה עוד יותר - הוא הפך את הסימן של Pullback/Range Bound (ראו README).
- מקרים סמוכים חופפים (אותה תבנית כמה ימים ברצף): לכן ה-Edge נמדד זוגית פר-מניה (paired_excess)
  ומדווח t-stat על פני מניות, לא על פני ימים.
- ללא עמלות/החלקה. נתונים תוך-יומיים זמינים רק ~60 יום, ולכן הסטטיסטיקה יומית בלבד.
פחות מ-BACKTEST_MIN_SAMPLES מקרים -> Edge ניטרלי (0.5) ומסומן insufficient_sample.
"""

import json
import os
import time

from config.similarity_config import (
    BACKTEST_HORIZON_DAYS,
    BACKTEST_MIN_SAMPLES,
    BACKTEST_PERIOD,
    BACKTEST_TARGET_R,
    EDGE_SCALE_R,
    STATS_MAX_AGE_DAYS,
    STATS_MIN_TICKERS,
)
from tools.multi_timeframe import calc_support_resistance
from tools.patterns import detect_patterns

STATS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pattern_stats.json")
NONE_LABEL = "NONE"
_WARMUP = 60  # מספר נרות מינימלי לפני שמתחילים לאתר תבניות


def simulate_trade(candles: list, i: int, horizon: int, target_r: float) -> float | None:
    """
    תוצאת עסקה היפותטית שנפתחת בסגירת הנר i, ביחידות R (סיכון = 1R).
    None אם אי אפשר להגדיר עסקה (אין סיכון חיובי או אין מספיק נרות קדימה).
    """
    if i + horizon >= len(candles):
        return None
    entry = candles[i]["close"]
    stop, _ = calc_support_resistance(candles[: i + 1])
    if stop is None or stop >= entry:
        return None
    risk = entry - stop
    target = entry + target_r * risk

    for k in range(i + 1, i + 1 + horizon):
        bar = candles[k]
        if bar["low"] <= stop:  # גם אם היעד באותו נר - שמרנית: סטופ קודם
            return -1.0
        if bar["high"] >= target:
            return target_r
    return (candles[i + horizon]["close"] - entry) / risk


def collect_dated_outcomes(candles: list, horizon: int = BACKTEST_HORIZON_DAYS, target_r: float = BACKTEST_TARGET_R) -> dict[str, list[tuple[str, float]]]:
    """עובר על כל הנרות ומחזיר {תבנית: [(תאריך, תוצאת R)]} (+ NONE לימים בלי תבנית)."""
    outcomes: dict[str, list[tuple[str, float]]] = {}
    for i in range(_WARMUP, len(candles) - horizon):
        window = candles[: i + 1]
        support, _ = calc_support_resistance(window)
        found = detect_patterns(window[-60:], support_level=support)
        result = simulate_trade(candles, i, horizon, target_r)
        if result is None:
            continue
        for name in (found or [NONE_LABEL]):
            outcomes.setdefault(name, []).append((candles[i]["date"], result))
    return outcomes


def collect_outcomes(candles: list, horizon: int = BACKTEST_HORIZON_DAYS, target_r: float = BACKTEST_TARGET_R) -> dict[str, list[float]]:
    """כמו collect_dated_outcomes, בלי תאריכים: {תבנית: [תוצאות R]}."""
    return {k: [r for _, r in v] for k, v in collect_dated_outcomes(candles, horizon, target_r).items()}


def summarize(outcomes: dict[str, list[float]], target_r: float = BACKTEST_TARGET_R) -> dict:
    """סטטיסטיקה לכל תבנית + Edge מנורמל ביחס לקו הבסיס (NONE)."""
    stats: dict[str, dict] = {}
    for name, rs in outcomes.items():
        n = len(rs)
        stats[name] = {
            "n": n,
            "win_rate": round(sum(1 for r in rs if r > 0) / n, 3) if n else None,
            "avg_r": round(sum(rs) / n, 3) if n else None,
            "target_hit_rate": round(sum(1 for r in rs if r >= target_r) / n, 3) if n else None,
        }

    base = stats.get(NONE_LABEL, {}).get("avg_r")
    for name, st in stats.items():
        if st["n"] < BACKTEST_MIN_SAMPLES or st["avg_r"] is None or base is None:
            st["edge"] = 0.5
            st["insufficient_sample"] = True
        else:
            # +EDGE_SCALE_R מעל קו הבסיס -> 1.0; -EDGE_SCALE_R מתחתיו -> 0.0; שווה לבסיס -> 0.5
            st["edge"] = round(max(0.0, min(1.0, 0.5 + (st["avg_r"] - base) / (2 * EDGE_SCALE_R))), 3)
            st["insufficient_sample"] = False
    return stats


def load_pattern_stats() -> dict:
    """
    קורא את הסטטיסטיקה של הריצה האחרונה של בדיקת העבר הרחבה (data/pattern_stats.json,
    נוצר ע"י `python -m tools.pattern_stats`). לא מחשבים בזמן ריצה: ההרצה המלאה על
    ~1,100 מניות נמשכת כ-4 דקות. אם הקובץ חסר - Edge ניטרלי (0.5) לכל התבניות והערה,
    ולא חוזרים לבדיקה על רשימת המעקב בלבד (הוכח שהיא מוטה - ראו README).
    """
    if not os.path.isfile(STATS_PATH):
        return {"patterns": {}, "caveat": "אין בדיקת עבר: הרץ python -m tools.pattern_stats. Edge ניטרלי לכל התבניות."}
    with open(STATS_PATH, encoding="utf-8") as f:
        stats = json.load(f)
    age_days = (time.time() - os.path.getmtime(STATS_PATH)) / 86400
    if age_days > STATS_MAX_AGE_DAYS:
        stats["stale"] = True
    return stats


def edge_for(pattern: str | None, stats: dict) -> dict:
    """ה-Edge של תבנית (None -> NONE). תבנית לא מוכרת/ללא מדגם -> ניטרלי 0.5."""
    entry = stats.get("patterns", {}).get(pattern or NONE_LABEL)
    if not entry:
        return {"edge": 0.5, "insufficient_sample": True, "n": 0}
    return {"edge": entry["edge"], "insufficient_sample": entry["insufficient_sample"], "n": entry["n"],
            "win_rate": entry["win_rate"], "avg_r": entry["avg_r"]}


# ---------------------------------------------------------------------------
# בדיקת עבר רחבה: S&P 500 + נאסד"ק (שווי שוק מעל 2 מיליארד$, כמו MIN_MARKET_CAP_USD)
# ---------------------------------------------------------------------------

UNIVERSE_FILTERS = [
    {"Index": "S&P 500"},
    {"Exchange": "NASDAQ", "Market Cap.": "+Mid (over $2bln)"},
]
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "backtest_report.json")


def fetch_universe_tickers(filters_list: list[dict] | None = None) -> list[str]:
    """טיקרים מ-Finviz (screener.ashx - מותר ב-robots.txt). איחוד ללא כפילויות; ריק אם נכשל."""
    from tools.finviz_screener import run_momentum_screen

    tickers: dict[str, None] = {}
    for f in (filters_list or UNIVERSE_FILTERS):
        try:
            for st in run_momentum_screen(f, limit=5000):
                if st.ticker and st.ticker.isalpha():  # מדלג על סימולים עם נקודה/מקף (מניות סדרה ב')
                    tickers[st.ticker] = None
        except Exception:
            continue
    return list(tickers)


def fetch_daily_batch(tickers: list[str], period: str = BACKTEST_PERIOD, chunk: int = 100) -> dict[str, list[dict]]:
    """מוריד היסטוריה יומית בהורדות מקובצות (yf.download) ומחזיר {טיקר: נרות}."""
    import yfinance as yf

    result: dict[str, list[dict]] = {}
    for i in range(0, len(tickers), chunk):
        part = tickers[i : i + chunk]
        try:
            df = yf.download(part, period=period, interval="1d", group_by="ticker", progress=False, auto_adjust=False, threads=True)
        except Exception:
            continue
        for t in part:
            try:
                sub = df[t].dropna(subset=["Close"])
            except Exception:
                continue
            if sub.empty:
                continue
            result[t] = [
                {"date": d.strftime("%Y-%m-%d"), "open": float(r["Open"]), "high": float(r["High"]),
                 "low": float(r["Low"]), "close": float(r["Close"]), "volume": int(r["Volume"] or 0)}
                for d, r in sub.iterrows()
            ]
    return result


def paired_excess(per_ticker: dict[str, dict[str, list[float]]], pattern: str, min_obs: int = 5) -> dict:
    """
    הפרש תוחלת (תבנית פחות ימים-בלי-תבנית) לכל מניה בנפרד, ואז ממוצע והסטטיסטי t על פני המניות.
    זה מנטרל את הסחף הכללי של כל מניה ומפחית את בעיית המקרים החופפים
    (יחידת המדידה היא מניה, לא יום).
    """
    diffs = []
    for outcomes in per_ticker.values():
        a, b = outcomes.get(pattern, []), outcomes.get(NONE_LABEL, [])
        if len(a) >= min_obs and len(b) >= min_obs:
            diffs.append(sum(a) / len(a) - sum(b) / len(b))
    k = len(diffs)
    if k < 2:
        return {"tickers": k, "mean_excess_r": None, "t_stat": None}
    mean = sum(diffs) / k
    var = sum((d - mean) ** 2 for d in diffs) / (k - 1)
    se = (var / k) ** 0.5
    return {"tickers": k, "mean_excess_r": round(mean, 4), "t_stat": round(mean / se, 2) if se else None}


def run_universe_backtest(candles_by_ticker: dict[str, list[dict]]) -> dict:
    """
    דוח מחקר מלא: סטטיסטיקה כוללת, פיצול חצי ראשון/שני של התקופה (בדיקת עקביות מחוץ למדגם),
    והמובהקות (paired t-stat על פני מניות) לכל תבנית.
    """
    pooled: dict[str, list[float]] = {}
    halves: dict[str, dict[str, list[float]]] = {"first_half": {}, "second_half": {}}
    per_ticker: dict[str, dict[str, list[float]]] = {}

    all_dates = sorted({c["date"] for cs in candles_by_ticker.values() for c in cs})
    midpoint = all_dates[len(all_dates) // 2] if all_dates else ""

    for t, candles in candles_by_ticker.items():
        if len(candles) < _WARMUP + BACKTEST_HORIZON_DAYS + 20:
            continue
        for name, dated in collect_dated_outcomes(candles).items():
            per_ticker.setdefault(t, {}).setdefault(name, []).extend(r for _, r in dated)
            for d, r in dated:
                pooled.setdefault(name, []).append(r)
                halves["first_half" if d < midpoint else "second_half"].setdefault(name, []).append(r)

    overall = summarize(pooled)
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "period": BACKTEST_PERIOD,
        "horizon_days": BACKTEST_HORIZON_DAYS,
        "target_r": BACKTEST_TARGET_R,
        "tickers_used": len(per_ticker),
        "split_date": midpoint,
        "patterns": overall,
        "first_half": summarize(halves["first_half"]),
        "second_half": summarize(halves["second_half"]),
        "significance": {name: paired_excess(per_ticker, name) for name in overall if name != NONE_LABEL},
        "caveat": "רשימת המדדים הנוכחית (Survivorship Bias), מקרים חופפים, ללא עמלות/החלקה - אינדיקציה, לא הבטחה.",
    }
    return report


def apply_paired_edges(report: dict) -> dict:
    """
    מחליף את ה-Edge של כל תבנית במדד הזוגי (excess R פר-מניה מול ימים בלי תבנית) כשיש מספיק
    מניות: זו יחידת המדידה הנכונה כי היא מנטרלת סחף מניה ומפחיתה חפיפת מקרים. התבנית NONE = 0.5.
    """
    for name, sig in report["significance"].items():
        st = report["patterns"][name]
        excess = sig.get("mean_excess_r")
        if excess is not None and sig["tickers"] >= STATS_MIN_TICKERS:
            st["edge"] = round(max(0.0, min(1.0, 0.5 + excess / (2 * EDGE_SCALE_R))), 3)
            st["edge_basis"] = "paired_excess_r"
            st["paired_excess_r"] = excess
            st["t_stat"] = sig["t_stat"]
            st["insufficient_sample"] = False
    return report


def write_runtime_stats(report: dict) -> None:
    """מפיק את הקובץ הקל שהדמיון קורא (data/pattern_stats.json) מדוח המחקר המלא."""
    slim = {k: report[k] for k in ("generated_at", "period", "horizon_days", "target_r", "tickers_used", "split_date", "patterns", "caveat")}
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=2)


def main() -> None:
    """python -m tools.pattern_stats : בדיקת עבר מלאה על S&P 500 + נאסד"ק, שומרת דוח + סטטיסטיקה."""
    tickers = fetch_universe_tickers()
    print(f"universe: {len(tickers)} tickers")
    report = apply_paired_edges(run_universe_backtest(fetch_daily_batch(tickers)))
    report["universe_size_requested"] = len(tickers)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    write_runtime_stats(report)
    print(f"done: {report['tickers_used']} tickers used; wrote {REPORT_PATH} and {STATS_PATH}")


if __name__ == "__main__":
    main()
