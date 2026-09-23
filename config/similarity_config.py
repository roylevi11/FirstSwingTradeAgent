"""
similarity_config.py
====================
פרמטרים של שכבת הדמיון החיה (tools/live_similarity.py). כולם ניתנים לשינוי
כאן במקום אחד. המשקלים הם הנחת עבודה (prior) - לא "אמת" - ולכן הם גלויים
ומתועדים; מה שכן נקבע מסטטיסטיקה היסטורית הוא ציון ה-Edge של כל תבנית
(tools/pattern_stats.py) והקורלציה ההיסטורית בין המניות.
"""

# משקל כל קבוצת מאפיינים בציון הדמיון הכולל (מנורמל אוטומטית לסכום 1
# על הקבוצות שיש עליהן נתון; קבוצה שחסר בה נתון אינה "מנוחשת").
GROUP_WEIGHTS: dict[str, float] = {
    "behavior_correlation": 0.20,  # קורלציית תשואות יומיות היסטורית (מדד סטטיסטי)
    "pattern": 0.20,               # תבנית טכנית + בכמה/אילו טווחי זמן היא מופיעה
    "technical_state": 0.25,       # מומנטום, מגמה (SMA), RSI, מיקום בערוץ, R:R חי
    "risk_profile": 0.10,          # תנודתיות (ATR%) ובטא
    "sector": 0.10,                # סקטור ותעשייה
    "earnings": 0.05,              # קרבה לדוחות
    "fundamentals": 0.10,          # שווי שוק ומכפיל רווח
}

# שילוב סופי: rank_score = (1 - EDGE_WEIGHT) * similarity + EDGE_WEIGHT * historical_edge
EDGE_WEIGHT: float = 0.30

# --- בדיקת עבר (backtest) של תבניות ---
BACKTEST_PERIOD: str = "2y"        # חלון נתונים יומיים
BACKTEST_HORIZON_DAYS: int = 10    # כמה ימי מסחר מחזיקים עסקה
BACKTEST_TARGET_R: float = 2.0     # יעד = כניסה + 2 * סיכון (תואם את סף ה-R:R שלנו)
BACKTEST_MIN_SAMPLES: int = 15     # פחות מזה -> Edge ניטרלי (0.5), מסומן "insufficient_sample"
EDGE_SCALE_R: float = 0.15         # פער של 0.15R (מעל/מתחת לקו הבסיס) = Edge קיצוני (1.0 / 0.0).
                                   # נבחר לפי הסקאלה שנמדדה ב-S&P500+NASDAQ: הפערים בין תבניות הם 0.02-0.12R בלבד
STATS_MAX_AGE_DAYS: int = 30       # אחרי כמה ימים נחשבת הסטטיסטיקה ישנה (מסומן stale, לא מחושב אוטומטית)
STATS_MIN_TICKERS: int = 30        # מינימום מניות למדידה זוגית (paired) כדי לסמוך עליה

# קורלציה היסטורית
CORRELATION_PERIOD: str = "6mo"
