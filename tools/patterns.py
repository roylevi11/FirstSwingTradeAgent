"""
patterns.py
===========
DREAM-02: זיהוי תבניות ספציפיות. זו בדיוק הפונקציה שדוברה בשיחה עם
Gemini בתגובה לכישלון הניסוי מול TradingView: "תבנית טכנית היא הגדרה
לוגית-מתמטית שמבוססת על יחסים בין נרות יפניים... נגדיר עבורו פונקציה
אלגוריתמית שמקבלת את נתוני הנרות ההיסטוריים ומחשבת את התנאים הלוגיים".

הנוסחאות המדויקות (Inside Bar, Breakout) לקוחות ישירות מהנוסחאות
שגמיני עצמו נתן בשיחה:
  is_inside_bar = (high_today < high_yesterday) and (low_today > low_yesterday)
  Breakout: Close(0) > Max(High, 20 days) AND Volume(0) > 1.5 * AvgVolume

כל הפונקציות מחזירות True/False חד-משמעי - לא "אולי" - כדי שהסוכן לא
יצטרך "לנחש" אם תבנית קיימת, בדיוק כמו שנדרש בעקבות כישלון TradingView.
"""

from tools.indicators import calc_sma, calc_relative_volume

Candle = dict


def is_inside_bar(candles: list) -> bool:
    """הנר האחרון (0) נמצא כולו בתוך טווח הנר שלפניו (1) - סימן לדחיסה/היסוס."""
    if len(candles) < 2:
        return False
    today, yesterday = candles[-1], candles[-2]
    return today["high"] < yesterday["high"] and today["low"] > yesterday["low"]


def is_breakout(candles: list, lookback: int = 20, volume_multiplier: float = 1.5) -> bool:
    """סגירה מעל השיא של lookback הימים האחרונים, בנפח חריג - פריצה אמיתית ולא רעש."""
    if len(candles) < lookback + 1:
        return False
    prior_candles = candles[-(lookback + 1):-1]
    prior_high = max(c["high"] for c in prior_candles)
    today = candles[-1]

    rel_volume = calc_relative_volume(candles, period=lookback)
    volume_ok = rel_volume is not None and rel_volume >= volume_multiplier

    return today["close"] > prior_high and volume_ok


def is_pullback_to_support(candles: list, support_level: float, tolerance_pct: float = 1.5) -> bool:
    """המחיר הנוכחי קרוב (בתוך tolerance_pct%) לרמת תמיכה מוגדרת מראש."""
    if not candles or support_level <= 0:
        return False
    close = candles[-1]["close"]
    distance_pct = abs(close - support_level) / support_level * 100
    return distance_pct <= tolerance_pct


def is_range_bound(candles: list, period: int = 10, width_threshold_pct: float = 5.0) -> bool:
    """הטווח (שיא-שפל) של period הימים האחרונים צר יחסית למחיר - דשדוש, לא מגמה."""
    if len(candles) < period:
        return False
    recent = candles[-period:]
    high = max(c["high"] for c in recent)
    low = min(c["low"] for c in recent)
    close = recent[-1]["close"]
    if close == 0:
        return False
    width_pct = (high - low) / close * 100
    return width_pct <= width_threshold_pct


def detect_patterns(candles: list, support_level: float | None = None) -> list[str]:
    """
    מריץ את כל בודקי התבניות ומחזיר רשימת שמות התבניות שזוהו בפועל
    (יכולות להיות כמה בו-זמנית, או אף אחת). זהו הכלי שהסוכן קורא לו
    במקום "לנחש" תבנית משם טקסטואלי בלבד.
    """
    found = []
    if is_inside_bar(candles):
        found.append("Inside Bar Consolidation")
    if is_breakout(candles):
        found.append("Breakout Confirmation")
    if support_level is not None and is_pullback_to_support(candles, support_level):
        found.append("Pullback to Support")
    if is_range_bound(candles):
        found.append("Range Bound")
    return found
