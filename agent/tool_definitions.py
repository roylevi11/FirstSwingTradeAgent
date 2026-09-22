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
        "מתויגים ידנית ולא מגיעים מ-API של מחירים."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
        "required": ["ticker"],
    },
}

FETCH_OHLC_TOOL = {
    "name": "fetch_recent_ohlc",
    "description": "שולף נתוני מחיר היסטוריים (Open/High/Low/Close/Volume) לימים האחרונים - בסיס לזיהוי תבניות טכניות.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string"},
            "days": {"type": "integer", "description": "כמות ימים לאחור, ברירת מחדל 10"},
        },
        "required": ["ticker"],
    },
}

# הכלי המובנה של Claude API - המקביל ל-Grounding with Google Search
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

ALL_TOOLS = [
    FETCH_MARKET_DATA_TOOL,
    FETCH_EARNINGS_TOOL,
    FETCH_WATCHLIST_TOOL,
    FETCH_OHLC_TOOL,
    EVALUATE_TRADE_TOOL,
    WEB_SEARCH_TOOL,
]
