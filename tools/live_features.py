"""
live_features.py
================
מאפיינים חיים עשירים לכל מניה בשכבת הדמיון. הכול נגזר מנתוני שוק חיים
(yfinance) על פני 7 טווחי זמן (5m עד 1W - הנר התוך-יומי האחרון הוא בפער
של דקות מהמציאות) + נתוני יסוד בסיסיים; מקובץ ה-CSV נלקחת רק זהות (טיקר/
שם/תג מקור).

עקרון: "None" הוא ערך לגיטימי - מניה בלי תבנית מזוהה נשמרת כ-primary_pattern=None,
ובנוסף patterns_by_timeframe מראה במפורש שבאף טווח לא זוהתה תבנית. כשיש תבנית
נשמר גם הטווח (או הטווחים) שבהם היא מופיעה.

נתון שאי אפשר לחשב -> None (ונרשם ב-missing), לא ממציאים ולא משלימים מהקובץ.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from config.similarity_config import CORRELATION_PERIOD
from tools.multi_timeframe import TIMEFRAME_CONFIGS, analyze_timeframe

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 600  # 10 דקות

# מהטווח הגבוה לנמוך: לבחירת ה"תבנית הראשית" נותנים עדיפות לטווחי הסווינג
TIMEFRAME_PRIORITY = ["1W", "1D", "4h", "1h", "30m", "15m", "5m"]


def _pct_return(closes: list[float], days: int) -> float | None:
    if len(closes) <= days or closes[-days - 1] == 0:
        return None
    return round((closes[-1] / closes[-days - 1] - 1) * 100, 3)


def _dist_pct(price: float | None, level: float | None) -> float | None:
    if price is None or not level:
        return None
    return round((price / level - 1) * 100, 3)


def select_primary_pattern(patterns_by_tf: dict[str, list[str]]) -> tuple[str | None, str | None, dict[str, list[str]]]:
    """
    מחזיר (תבנית ראשית, הטווח שלה, {תבנית: [טווחים שבהם היא מופיעה]}).
    אם אין תבנית באף טווח: (None, None, {}) - "אין תבנית" הוא ערך לגיטימי, לא נתון חסר.
    """
    by_pattern: dict[str, list[str]] = {}
    for tf in TIMEFRAME_PRIORITY:
        for p in patterns_by_tf.get(tf, []):
            by_pattern.setdefault(p, []).append(tf)
    for tf in TIMEFRAME_PRIORITY:
        if patterns_by_tf.get(tf):
            return patterns_by_tf[tf][0], tf, by_pattern
    return None, None, by_pattern


def derive_features(ticker: str, snaps: dict, closes_1d: list[float], live_price: float | None, info: dict, days_to_earnings: int | None) -> dict:
    """בונה את מילון המאפיינים משכבות הנתונים הגולמיות (מופרד מהרשת כדי שניתן יהיה לבדוק)."""
    daily = snaps.get("1D")
    price = live_price or (daily.last_close if daily else None)
    ind_d = daily.indicators if daily else {}
    ind_h = snaps["1h"].indicators if snaps.get("1h") else {}

    patterns_by_tf = {label: list(s.patterns_found) for label, s in snaps.items()}
    primary, primary_tf, by_pattern = select_primary_pattern(patterns_by_tf)

    support = daily.support if daily else None
    resistance = daily.resistance if daily else None
    channel_pos = rr = None
    if price and support is not None and resistance is not None and resistance > support:
        channel_pos = round((price - support) / (resistance - support), 3)
        if support < price < resistance:
            rr = round(min((resistance - price) / (price - support), 5.0), 3)

    above = [
        1.0 if s.last_close > s.indicators["sma_20"] else 0.0
        for s in snaps.values()
        if s.last_close is not None and s.indicators.get("sma_20")
    ]
    macd_hist = (ind_d.get("macd") or {}).get("histogram")

    numeric = {
        "ret_5d": _pct_return(closes_1d, 5),
        "ret_20d": _pct_return(closes_1d, 20),
        "ret_60d": _pct_return(closes_1d, 60),
        "dist_sma20_pct": _dist_pct(price, ind_d.get("sma_20")),
        "dist_sma50_pct": _dist_pct(price, ind_d.get("sma_50")),
        "dist_sma200_pct": _dist_pct(price, ind_d.get("sma_200")),
        "rsi_1d": ind_d.get("rsi_14"),
        "rsi_1h": ind_h.get("rsi_14"),
        "macd_hist_pct": round(macd_hist / price * 100, 4) if macd_hist is not None and price else None,
        "channel_pos": channel_pos,
        "risk_reward": rr,
        "trend_alignment": round(sum(above) / len(above), 3) if above else None,
        "rel_volume_1d": ind_d.get("relative_volume_20d"),
        "atr_pct_1d": round(ind_d["atr_14"] / price * 100, 3) if ind_d.get("atr_14") and price else None,
        "atr_pct_1h": round(ind_h["atr_14"] / price * 100, 3) if ind_h.get("atr_14") and price else None,
        "beta": info.get("beta"),
        "log_market_cap": None,
        "pe_ratio": info.get("trailingPE"),
        "days_to_earnings": days_to_earnings,
    }
    if info.get("marketCap"):
        import math

        numeric["log_market_cap"] = round(math.log10(info["marketCap"]), 3)

    return {
        "ticker": ticker,
        "price": price,
        "support_1d": support,
        "resistance_1d": resistance,
        "primary_pattern": primary,
        "primary_pattern_timeframe": primary_tf,
        "pattern_timeframes": by_pattern,
        "patterns_by_timeframe": patterns_by_tf,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "numeric": numeric,
        "missing": sorted(k for k, v in numeric.items() if v is None),
        "as_of": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_features(ticker: str) -> dict:
    """שולף את כל הנתונים החיים למניה אחת ובונה את מאפייניה (עם מטמון 10 דקות)."""
    key = ticker.upper()
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]

    from tools.earnings import fetch_earnings_calendar
    from tools.market_data import fetch_live_price, fetch_recent_ohlc

    snaps = {}
    for cfg in TIMEFRAME_CONFIGS:
        try:
            snaps[cfg["label"]] = analyze_timeframe(key, cfg)
        except Exception:
            continue

    try:
        closes = [c["close"] for c in fetch_recent_ohlc(key, days=300, interval="1d")]
    except Exception:
        closes = []

    try:
        import yfinance as yf

        info = yf.Ticker(key).info or {}
    except Exception:
        info = {}

    try:
        e = fetch_earnings_calendar(key)
        dte = e.trading_days_until if e.data_available else None
    except Exception:
        dte = None

    features = derive_features(key, snaps, closes, fetch_live_price(key), info, dte)
    _CACHE[key] = (time.time(), features)
    return features


def load_universe_features(tickers: list[str], max_workers: int = 6) -> dict[str, dict]:
    """מאפיינים חיים לכל הטיקרים, במקביל."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return dict(zip(tickers, pool.map(build_features, tickers)))


def return_correlations(tickers: list[str]) -> dict[str, dict[str, float]]:
    """
    קורלציית תשואות יומיות היסטורית (CORRELATION_PERIOD) בין כל זוג טיקרים -
    המדד הסטטיסטי הסטנדרטי ל"מניות שמתנהגות דומה". {טיקר: {טיקר אחר: קורלציה}}.
    אם ההורדה נכשלת מחזיר {} (הקבוצה תיושמט מהציון, לא תנוחש).
    """
    try:
        import yfinance as yf

        data = yf.download(tickers, period=CORRELATION_PERIOD, interval="1d", progress=False, auto_adjust=True)["Close"]
        corr = data.pct_change().dropna(how="all").corr()
        return {a: {b: float(corr.loc[a, b]) for b in corr.columns if b != a and corr.loc[a, b] == corr.loc[a, b]} for a in corr.index}
    except Exception:
        return {}
