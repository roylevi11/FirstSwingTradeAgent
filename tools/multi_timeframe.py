"""
multi_timeframe.py
===================
שינוי ארכיטקטוני לפי בקשה מפורשת: מרגע זה, תמיכה/התנגדות/תבנית טכנית
לא נשלפות מתיוג ידני (watchlist.csv) אלא **נגזרות מחדש בכל הרצה מנתונים
חיים**, על פני כמה טווחי זמן במקביל - בדיוק כמו שבטריידינג-וויו בוחרים
טווח (5m/15m/30m/1h/4h/1D) ורואים תמונה שונה בכל אחד.

שיטת תמיכה/התנגדות: Donchian-style - השפל והשיא על פני חלון הזמן
האחרון בכל טווח. זו שיטה סטנדרטית, שקופה ודטרמיניסטית (לא "דעה" של
מודל שפה) - ממשיכה את אותו עיקרון של "לא מנחשים, מחשבים".
"""

from dataclasses import dataclass

from tools.patterns import detect_patterns
from tools.indicators import analyze_indicators

Candle = dict

# טווחי הזמן הנתמכים, לפי הבקשה: 5, 15, 30, 60 דקות, 240 דקות (4 שעות), ומעלה (יומי).
# yfinance לא תומך ב-"240m" כמרווח ישיר - בונים אותו מחדש מנתוני 60 דקות (resample).
TIMEFRAME_CONFIGS = [
    {"label": "5m", "yf_interval": "5m", "days": 5, "resample_from_60m": None},
    {"label": "15m", "yf_interval": "15m", "days": 10, "resample_from_60m": None},
    {"label": "30m", "yf_interval": "30m", "days": 20, "resample_from_60m": None},
    {"label": "1h", "yf_interval": "60m", "days": 59, "resample_from_60m": None},
    {"label": "4h", "yf_interval": "60m", "days": 59, "resample_from_60m": 4},
    {"label": "1D", "yf_interval": "1d", "days": 300, "resample_from_60m": None},
    {"label": "1W", "yf_interval": "1wk", "days": 1460, "resample_from_60m": None},
]
# הערה: SMA200 רלוונטי בפועל רק לטווח היומי (1D) ומעלה - זו הדרך
# המקובלת להשתמש בו (מגמת-על ארוכת-טווח). בטווחי זמן קצרים יותר (עד
# 4h) הוא יחזור כ-None באופן טבעי בגלל מגבלת ה-59 יום של נתונים
# תוך-יומיים אצל yfinance - זו לא בעיה שדורשת פתרון, כי גם מבחינה
# אנליטית SMA200 על נרות של 5 דקות הוא כמעט חסר משמעות.


def resample_candles(candles: list[Candle], factor: int) -> list[Candle]:
    """
    מאחד כל `factor` נרות עוקבים לנר אחד גדול יותר (למשל 4 נרות של 60
    דקות -> נר אחד של 4 שעות). Open=הראשון, Close=האחרון, High/Low=
    מקסימום/מינימום, Volume=סכום. נרות עודפים שלא משלימים קבוצה מלאה
    בתחילת הרשימה מושמטים, כדי שכל נר מיוצג בפרופורציה נכונה.
    """
    if factor <= 1 or not candles:
        return candles

    trim = len(candles) % factor
    trimmed = candles[trim:] if trim else candles

    resampled = []
    for i in range(0, len(trimmed), factor):
        group = trimmed[i:i + factor]
        if len(group) < factor:
            continue
        resampled.append({
            "date": group[0]["date"],
            "open": group[0]["open"],
            "high": max(c["high"] for c in group),
            "low": min(c["low"] for c in group),
            "close": group[-1]["close"],
            "volume": sum(c["volume"] for c in group),
        })
    return resampled


def calc_support_resistance(candles: list[Candle], lookback: int = 20) -> tuple[float | None, float | None]:
    """
    תמיכה/התנגדות דינמיות (Donchian Channel): השפל/השיא על פני
    lookback הנרות האחרונים. לא תיוג ידני - מחושב מחדש כל הרצה.
    """
    if len(candles) < 2:
        return None, None
    window = candles[-lookback:] if len(candles) >= lookback else candles
    support = min(c["low"] for c in window)
    resistance = max(c["high"] for c in window)
    return round(support, 2), round(resistance, 2)


@dataclass
class TimeframeSnapshot:
    label: str
    candles_available: int
    last_close: float | None
    support: float | None
    resistance: float | None
    patterns_found: list
    indicators: dict


def analyze_timeframe(ticker: str, tf_config: dict) -> TimeframeSnapshot:
    """מריץ את כל שרשרת הניתוח (נתונים -> תמיכה/התנגדות -> תבניות -> אינדיקטורים) על טווח זמן בודד."""
    from tools.market_data import fetch_recent_ohlc  # ייבוא מושהה - yfinance נדרש רק כאן בפועל, לא בבדיקות הלוגיקה הטהורה

    raw = fetch_recent_ohlc(ticker, days=tf_config["days"], interval=tf_config["yf_interval"])
    factor = tf_config["resample_from_60m"]
    candles = resample_candles(raw, factor) if factor else raw

    if not candles:
        return TimeframeSnapshot(tf_config["label"], 0, None, None, None, [], {})

    support, resistance = calc_support_resistance(candles)
    patterns = detect_patterns(candles, support_level=support)
    indicators = analyze_indicators(candles)

    return TimeframeSnapshot(
        label=tf_config["label"],
        candles_available=len(candles),
        last_close=candles[-1]["close"],
        support=support,
        resistance=resistance,
        patterns_found=patterns,
        indicators=indicators,
    )


def analyze_multi_timeframe(ticker: str) -> dict:
    """
    נקודת הכניסה הראשית: מריץ ניתוח מלא על כל טווחי הזמן הנתמכים,
    ומחזיר תמונת מצב מאוחדת - זהו התחליף החי ל-fetch_watchlist_entry
    לצורך קביעת תמיכה/התנגדות/תבנית עבור evaluate_trade.
    """
    results = {}
    for tf in TIMEFRAME_CONFIGS:
        snap = analyze_timeframe(ticker, tf)
        results[tf["label"]] = {
            "candles_available": snap.candles_available,
            "last_close": snap.last_close,
            "support": snap.support,
            "resistance": snap.resistance,
            "patterns_found": snap.patterns_found,
            "indicators": snap.indicators,
        }
    return results
