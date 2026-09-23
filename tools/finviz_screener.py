"""
finviz_screener.py
===================
DREAM-12: אינטגרציה עם סורקי Finviz, גישה חינמית (ללא Finviz Elite).

החלטת תכנון חשובה: **לא** נכתב כאן scraping ידני (BeautifulSoup + פענוח
טבלת HTML לפי אינדקס עמודה) - זו גישה שברירית מאוד, כי Finviz משנים
את מבנה הדף מדי פעם ואז קוד כזה נשבר בשקט. במקום זה, נעטפת כאן הספרייה
הפתוחה והמתוחזקת `finvizfinance` (MIT License, github.com/lit26/
finvizfinance) שכבר פותרת את זה, ומחזירה DataFrame מסודר.

הערה לשימוש אחראי: זו גישה לעמוד הציבורי החינמי של Finviz, לא ה-API
הרשמי בתשלום (Finviz Elite). לשימוש אישי/לימודי בקצב סביר (לא מאות
בקשות בשנייה) זה נהוג ומקובל, אך שווה להכיר את תנאי השימוש של האתר.

**לא נבדק בפועל בסביבת הכתיבה** (אין רשת + finvizfinance לא מותקן כאן) -
כל הבדיקות שכן קיימות (tests/test_finviz_screener.py) בודקות רק את
לוגיקת העיבוד שלנו (post-processing) מול נתונים מדומים, לא את הספרייה
עצמה או את הרשת.
"""

from dataclasses import dataclass


@dataclass
class ScreenedStock:
    ticker: str
    company_name: str | None
    sector: str | None
    price: float | None
    change_pct: float | None
    volume: int | None
    source_tag: str = "Finviz_Screen"


def _row_to_screened_stock(row: dict) -> ScreenedStock:
    """
    ממיר שורה בודדת (dict, כפי שמתקבל מ-DataFrame.to_dict('records') של
    finvizfinance) ל-ScreenedStock אחיד. מופרד מ-run_momentum_screen כדי
    שאפשר לבדוק אותו בלי לתלות בספרייה עצמה (ראו הבדיקות).
    """
    def _to_float(v):
        try:
            return float(v) if v not in (None, "", "-") else None
        except (ValueError, TypeError):
            return None

    def _to_int(v):
        try:
            return int(float(v)) if v not in (None, "", "-") else None
        except (ValueError, TypeError):
            return None

    return ScreenedStock(
        ticker=str(row.get("Ticker", "")).upper(),
        company_name=row.get("Company") or None,
        sector=row.get("Sector") or None,
        price=_to_float(row.get("Price")),
        change_pct=_to_float(str(row.get("Change %", row.get("Change", ""))).replace("%", "")),
        volume=_to_int(row.get("Volume")),
    )


def run_momentum_screen(filters: dict | None = None, limit: int = 20) -> list[ScreenedStock]:
    """
    מריץ סריקת Finviz עם הפילטרים הנתונים ומחזיר רשימת מניות אחידה.

    filters: מילון פילטרים בפורמט של finvizfinance, למשל:
        {"Index": "S&P 500", "Sector": "Technology"}
    ברירת המחדל (None) מריצה בלי פילטר - כל השוק, ממוין לפי הגדרת
    finvizfinance. **חשוב:** שמות הפילטרים המדויקים (כמו סינון לפי
    מומנטום/פריצה) משתנים בין גרסאות finvizfinance - לפני הרצה קבועה,
    יש להריץ Overview().get_filter_options(...) פעם אחת כדי לוודא את
    הערכים המדויקים הנתמכים בגרסה המותקנת אצלך.

    דורש: pip install finvizfinance (נוסף ל-requirements.txt).
    """
    from finvizfinance.screener.overview import Overview  # ייבוא מושהה - לא מותקן בסביבת הכתיבה

    screener = Overview()
    if filters:
        screener.set_filter(filters_dict=filters)

    df = screener.screener_view(limit=limit, verbose=0)
    if df is None or df.empty:
        return []

    return [_row_to_screened_stock(row) for row in df.to_dict("records")]
