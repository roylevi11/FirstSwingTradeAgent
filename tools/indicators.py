"""
indicators.py
=============
DREAM-03: אינדיקטורים כמותיים מורחבים - בדיוק כפי שנדון בשיחה עם Gemini
("באמצעות ספריות ניתוח טכני ב-Python... נוכל לחשב עבור הסוכן כל אינדיקטור
שתרצה"). כאן זה מומש כפונקציות מתמטיות טהורות, ללא תלות ב-pandas-ta
(פחות תלויות = פחות נקודות תקלה), על אותו פורמט candles שמחזיר
tools/market_data.fetch_recent_ohlc (רשימת dict, מהישן לחדש).

כל הפונקציות דטרמיניסטיות וניתנות לבדיקה בלי רשת - בדיוק כמו risk.py.
"""

Candle = dict  # {"date", "open", "high", "low", "close", "volume"}


def _closes(candles: list[Candle]) -> list[float]:
    return [c["close"] for c in candles]


def calc_sma(candles: list[Candle], period: int) -> float | None:
    """ממוצע נע פשוט (Simple Moving Average) של N הנרות האחרונים."""
    closes = _closes(candles)
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


def _ema_series(prices: list[float], period: int) -> list[float]:
    """מחזיר את כל סדרת ה-EMA (לא רק הערך האחרון) - נדרש לחישוב MACD,
    שהוא בעצמו EMA שמופעל על הפרש בין שני EMA אחרים."""
    if len(prices) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period  # זרע ראשוני: SMA
    series = [ema]
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
        series.append(ema)
    return series


def calc_ema(candles: list[Candle], period: int) -> float | None:
    """ממוצע נע מעריכי (Exponential Moving Average) - נותן משקל גבוה יותר לנרות האחרונים."""
    series = _ema_series(_closes(candles), period)
    return round(series[-1], 4) if series else None


def calc_macd(candles: list[Candle], fast: int = 12, slow: int = 26, signal: int = 9) -> dict | None:
    """
    MACD (Moving Average Convergence Divergence) - אינדיקטור מגמה ומומנטום.
    macd = EMA(fast) - EMA(slow); signal = EMA(signal) של קו ה-MACD עצמו;
    histogram = macd - signal. חציית macd מעל signal נחשבת אות שורי,
    מתחתיו אות דובי. הפרמטרים הסטנדרטיים (12/26/9) לפי המוסכמה המקובלת.
    """
    closes = _closes(candles)
    if len(closes) < slow + signal:
        return None

    fast_series = _ema_series(closes, fast)
    slow_series = _ema_series(closes, slow)
    # מיישרים את שתי הסדרות כך שיתייחסו לאותם ימים בדיוק (fast מתחיל מוקדם יותר)
    offset = len(fast_series) - len(slow_series)
    macd_line = [f - s for f, s in zip(fast_series[offset:], slow_series)]

    if len(macd_line) < signal:
        return None
    signal_series = _ema_series(macd_line, signal)

    macd_value = macd_line[-1]
    signal_value = signal_series[-1]
    return {
        "macd": round(macd_value, 4),
        "signal": round(signal_value, 4),
        "histogram": round(macd_value - signal_value, 4),
    }


def calc_rsi(candles: list[Candle], period: int = 14) -> float | None:
    """
    RSI (Relative Strength Index) לפי שיטת Wilder - אינדיקטור מומנטום.
    מעל 70 נחשב בדרך כלל "קניית יתר" (Overbought), מתחת ל-30 "מכירת יתר".
    """
    closes = _closes(candles)
    if len(closes) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calc_atr(candles: list[Candle], period: int = 14) -> float | None:
    """
    ATR (Average True Range) - מודד תנודתיות בפועל (לא כיוון). שימושי
    לקביעת מרחק סטופ-לוס/יעד יחסי לתנודתיות האמיתית של הנכס, במקום
    מספרים קבועים (בדיוק כפי שהוסבר בשיחה עם Gemini).
    """
    if len(candles) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(candles)):
        high, low = candles[i]["high"], candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None
    return round(sum(true_ranges[-period:]) / period, 4)


def calc_relative_volume(candles: list[Candle], period: int = 20) -> float | None:
    """
    נפח המסחר של הנר האחרון, יחסית לממוצע N הימים שלפניו.
    ערך מעל 1.5 מציין נפח חריג - רכיב מפתח בזיהוי פריצות אמיתיות (DREAM-02).
    """
    if len(candles) < period + 1:
        return None
    today_volume = candles[-1]["volume"]
    avg_volume = sum(c["volume"] for c in candles[-(period + 1):-1]) / period
    if avg_volume == 0:
        return None
    return round(today_volume / avg_volume, 4)


def analyze_indicators(candles: list[Candle]) -> dict:
    """נקודת כניסה מרוכזת - כל האינדיקטורים בקריאה אחת, עבור כלי הסוכן."""
    return {
        "sma_20": calc_sma(candles, 20),
        "sma_50": calc_sma(candles, 50),
        "sma_100": calc_sma(candles, 100),
        "sma_200": calc_sma(candles, 200),
        "ema_10": calc_ema(candles, 10),
        "rsi_14": calc_rsi(candles, 14),
        "atr_14": calc_atr(candles, 14),
        "macd": calc_macd(candles),
        "relative_volume_20d": calc_relative_volume(candles, 20),
        "candles_available": len(candles),
    }
