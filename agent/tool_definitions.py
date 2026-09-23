"""
tool_definitions.py
====================
סכמות ה-JSON של הכלים שנחשפים ל-Claude API (Function Calling).
זהו התרגום הישיר של 5 הכלים שהוגדרו בעבודה 1
(fetch_market_data, fetch_earnings_calendar, search_financial_news,
calc_position_size, create_draft_order) לפורמט tool_use של Claude.

הערה: search_financial_news מומש לא כפונקציית Python עצמאית, אלא
כהפעלה של הכלי המובנה web_search של Claude API עצמו (server tool) -
זהו המקביל הישיר ל-"Grounding with Google Search" שבו נעשה שימוש
ב-AI Studio.
"""

EVALUATE_TRADE_TOOL = {
    "name": "evaluate_trade",
    "description": (
        "מריץ את כל חוקי הברזל הדטרמיניסטיים (יחס סיכון/סיכוי, קרבה לדוחות) "
        "על עסקה מוצעת, ומפיק תזכיר עסקה סופי (מאושר או נדחה). "
        "חובה להשתמש בכלי הזה לכל חישוב - אסור בהחלט לחשב יחס סיכון/סיכוי "
        "או להחליט על אישור/דחייה באופן עצמאי."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "סימול המניה, למשל NVDA"},
            "company_name": {"type": "string"},
            "technical_pattern": {"type": "string", "description": "התבנית הטכנית שזוהתה, למשל Inside Bar Consolidation"},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "target_price": {"type": "number"},
            "days_to_earnings": {"type": "integer", "description": "מספר ימי המסחר עד לדוחות הכספיים הקרובים"},
            "account_size": {"type": "number", "description": "גודל התיק בדולרים, לחישוב גודל פוזיציה (אופציונלי)"},
            "rationale": {"type": "string", "description": "נימוק קצר להמלצה, מבוסס הנתונים שנאספו"},
        },
        "required": ["ticker", "company_name", "technical_pattern", "entry_price", "stop_loss", "target_price", "days_to_earnings"],
    },
}

FETCH_MARKET_DATA_TOOL = {
    "name": "fetch_market_data",
    "description": "שולף נתוני שוק עדכניים למניה: מחיר נוכחי, שם חברה, סקטור, שווי שוק, מכפיל רווח.",
    "input_schema": {
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
        "required": ["ticker"],
    },
}

FETCH_EARNINGS_TOOL = {
    "name": "fetch_earnings_calendar",
    "description": "שולף את מועד הדוחות הכספיים הקרוב הבא של מניה, ומחזיר כמה ימי מסחר נותרו עד אליו.",
    "input_schema": {
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
        "required": ["ticker"],
    },
}

FETCH_WATCHLIST_TOOL = {
    "name": "fetch_watchlist_entry",
    "description": (
        "שולף ידע אנליסט מתויג-ידנית עבור מניה מרשימת המעקב המקומית: רמות "
        "תמיכה/התנגדות ותבנית טכנית שזוהתה. השתמש בכלי הזה, ולא בניחוש, "
        "בכל פעם שנדרשת רמת תמיכה/התנגדות או תבנית טכנית - אלו נתונים "
        "מתויגים ידנית ולא מגיעים מ-API של מחירים. שים לב: שדה current_price "
        "שמוחזר כאן הוא ערך היסטורי מזמן התיוג בלבד - לעולם אל תשתמש בו "
        "כמחיר כניסה; לכך יש להפעיל תמיד את fetch_market_data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
        "required": ["ticker"],
    },
}

ANALYZE_MULTI_TIMEFRAME_TOOL = {
    "name": "analyze_multi_timeframe",
    "description": (
        "מריץ ניתוח טכני חי ומלא על פני 7 טווחי זמן (5m, 15m, 30m, 1h, 4h, 1D, 1W) - "
        "עבור כל טווח: תמיכה/התנגדות דינמיות (Donchian, מחושבות מנתונים חיים, "
        "לא תיוג ידני), תבניות שזוהו, ואינדיקטורים (RSI/ATR/SMA/נפח). "
        "זהו מקור האמת היחיד לתמיכה/התנגדות/תבנית טכנית כעת - "
        "אין להסתמך על Key_Support/Key_Resistance/Technical_Pattern "
        "המתויגים ידנית ב-fetch_watchlist_entry עבור קביעת עסקה."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
        "required": ["ticker"],
    },
}

FIND_SIMILAR_STOCKS_TOOL = {
    "name": "find_similar_stocks",
    "description": (
        "מפעיל את שכבת הדמיון על רשימת המעקב, ומחזיר את המניות הדומות ביותר "
        "למניה נתונה (Cosine או Jaccard). השתמש בכלי הזה כשעסקה נפסלת "
        "כדי למצוא חלופה - אל תמליץ על מניה אחרת בלי להפעיל אותו קודם."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "סימול המניה הבסיסית (זו שנפסלה)"},
            "min_risk_reward": {
                "type": "number",
                "description": "אם צוין, הכלי יחזיר את המניה הדומה ביותר שגם עומדת ביחס סיכון/סיכוי הזה או מעליו",
            },
        },
        "required": ["ticker"],
    },
}

FETCH_OHLC_TOOL = {
    "name": "fetch_recent_ohlc",
    "description": "שולף נתוני מחיר היסטוריים (Open/High/Low/Close/Volume) - בסיס לזיהוי תבניות ולחישוב אינדיקטורים. יש להריץ אותו לפני detect_chart_patterns או analyze_technical_indicators.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string"},
            "days": {"type": "integer", "description": "כמות ימים לאחור, ברירת מחדל 10 (עבור אינדיקטורים כמו RSI/ATR/SMA50 צריך לפחות 55-60 ימים)"},
            "interval": {"type": "string", "description": "רזולוציית הנרות: '1d' (ברירת מחדל) או תוך-יומי כמו '5m'/'15m'/'1h'"},
        },
        "required": ["ticker"],
    },
}

DETECT_PATTERNS_TOOL = {
    "name": "detect_chart_patterns",
    "description": (
        "מזהה תבניות טכניות (Inside Bar, Breakout, Pullback to Support, Range Bound) "
        "מתוך נתוני OHLC בפועל - נוסחה לוגית-מתמטית, לא ניחוש משם התבנית. "
        "יש להעביר את תוצאת fetch_recent_ohlc כקלט (candles), ואופציונלית רמת תמיכה "
        "(מ-fetch_watchlist_entry) עבור בדיקת Pullback."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "candles": {"type": "array", "description": "רשימת הנרות שהתקבלה מ-fetch_recent_ohlc"},
            "support_level": {"type": "number", "description": "רמת תמיכה ידועה, לבדיקת Pullback to Support (אופציונלי)"},
        },
        "required": ["candles"],
    },
}

ANALYZE_INDICATORS_TOOL = {
    "name": "analyze_technical_indicators",
    "description": (
        "מחשב אינדיקטורים כמותיים (SMA20/50, EMA20, RSI14, ATR14, נפח יחסי) מתוך "
        "נתוני OHLC. יש להעביר את תוצאת fetch_recent_ohlc כקלט (candles). "
        "שימושי לחיזוק/החלשת הביטחון בתזכיר, לא כתחליף לחוקי הברזל של evaluate_trade."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "candles": {"type": "array", "description": "רשימת הנרות שהתקבלה מ-fetch_recent_ohlc"},
        },
        "required": ["candles"],
    },
}

# הכלי המובנה של Claude API - המקביל ל-Grounding with Google Search
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

ALL_TOOLS = [
    FETCH_MARKET_DATA_TOOL,
    FETCH_EARNINGS_TOOL,
    FETCH_WATCHLIST_TOOL,
    FETCH_OHLC_TOOL,
    DETECT_PATTERNS_TOOL,
    ANALYZE_INDICATORS_TOOL,
    ANALYZE_MULTI_TIMEFRAME_TOOL,
    FIND_SIMILAR_STOCKS_TOOL,
    EVALUATE_TRADE_TOOL,
    WEB_SEARCH_TOOL,
]
