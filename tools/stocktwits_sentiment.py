"""
stocktwits_sentiment.py
========================
DREAM-13: סנטימנט בזמן אמת מ-StockTwits.

בניגוד ל-Market Momentum Radar, כאן יש נקודת קצה ציבורית, ללא מפתח,
מתועדת ונפוצה: https://api.stocktwits.com/api/2/streams/symbol/{TICKER}.json
משמשת ספריות קוד פתוח וכלים מסחריים כאחד - זו לא "פריצה", זו נקודת
הקצה הרשמית של סטרימים ציבוריים.

**לא נבדק בפועל בסביבת הכתיבה** (אין רשת כאן) - רק לוגיקת העיבוד
(תקצור הודעות לציון בוליש/בריש) נבדקה, עם נתונים מדומים.

שימוש הוגן: יש הגבלת קצב לא-רשמית מדווחת של כ-200 בקשות/שעה ל-IP
בנקודות הקריאה הציבוריות. אין להריץ בלולאה צפופה.
"""


def _sentiment_of(message: dict) -> str | None:
    """מחלץ את תגית הסנטימנט (Bullish/Bearish) מהודעה, אם המשתמש תייג אחת."""
    entities = message.get("entities") or {}
    sentiment = entities.get("sentiment")
    return sentiment.get("basic") if sentiment else None


def _summarize_messages(messages: list[dict]) -> dict:
    """
    מרכז רשימת הודעות StockTwits לסיכום סנטימנט אחיד. מופרד מ-fetch
    כדי שאפשר לבדוק את הלוגיקה בלי רשת (ראו tests/test_stocktwits.py).
    לא כל הודעה מתויגת ע"י הכותב - הודעות לא-מתויגות לא נספרות
    ביחס הבוליש/בריש (לא נחשבות "אפס"), בדיוק כמו כלל "אל תמציא נתון".
    """
    bullish = sum(1 for m in messages if _sentiment_of(m) == "Bullish")
    bearish = sum(1 for m in messages if _sentiment_of(m) == "Bearish")
    tagged = bullish + bearish

    return {
        "message_volume": len(messages),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "tagged_count": tagged,
        "bullish_ratio": round(bullish / tagged, 4) if tagged else None,
    }


def fetch_symbol_sentiment(ticker: str, message_limit: int = 30) -> dict:
    """
    שולף את ההודעות האחרונות על טיקר מ-StockTwits ומחזיר סיכום סנטימנט.
    אם הטיקר לא נמצא/אין הודעות - available=False, לא ניחוש של סנטימנט.
    """
    import requests  # ייבוא מושהה - לא נדרש לבדיקות הלוגיקה הטהורה

    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker.upper()}.json"
    try:
        resp = requests.get(url, headers={"User-Agent": "SwingCopilot/1.0 (educational project)"}, timeout=10)
    except requests.RequestException as exc:
        return {"available": False, "ticker": ticker.upper(), "error": str(exc)}

    if resp.status_code != 200:
        return {"available": False, "ticker": ticker.upper(), "error": f"HTTP {resp.status_code}"}

    messages = resp.json().get("messages", [])[:message_limit]
    summary = _summarize_messages(messages)
    return {"available": True, "ticker": ticker.upper(), **summary}
