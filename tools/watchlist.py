"""
watchlist.py
============
זהו רכיב ה-"Knowledge" בטבלת חמשת הרכיבים (Model/Instructions/Knowledge/
Tools/Memory) - המידע הספציפי, המתויג-ידנית (Curated) שממנו הסוכן שואב
תשובות: רמות תמיכה/התנגדות, תבנית טכנית, ותיוג מקור.

שימו לב לחלוקת התפקידים בין שני כלי הנתונים:
- market_data.py -> נתונים חיים מה-API (מחיר, שווי שוק, מכפיל) - DREAM-01.
- watchlist.py (כאן) -> ידע אנליסט מוזן מראש (תמיכה/התנגדות/תבנית) -
  בדיוק כמו ה-CSV שהוזן ידנית ב-AI Studio בעבודות 2-3. רמות תמיכה/
  התנגדות הן החלטת ניתוח טכני אנושית - yfinance לא "יודע" אותן.
"""

import csv
import os
from dataclasses import dataclass

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.csv")


@dataclass
class WatchlistEntry:
    ticker: str
    found: bool
    company_name: str | None = None
    sector: str | None = None
    current_price: float | None = None
    key_support: float | None = None
    key_resistance: float | None = None
    days_to_earnings: int | None = None
    technical_pattern: str | None = None
    source_tag: str | None = None


def _row_to_entry(row: dict) -> WatchlistEntry:
    def _to_float(v):
        try:
            return float(v) if v not in (None, "") else None
        except ValueError:
            return None

    def _to_int(v):
        try:
            return int(v) if v not in (None, "") else None
        except ValueError:
            return None

    return WatchlistEntry(
        ticker=row["Ticker"].upper(),
        found=True,
        company_name=row.get("Company_Name") or None,
        sector=row.get("Sector") or None,
        current_price=_to_float(row.get("Current_Price")),
        key_support=_to_float(row.get("Key_Support")),
        key_resistance=_to_float(row.get("Key_Resistance")),
        days_to_earnings=_to_int(row.get("Days_To_Earnings")),
        technical_pattern=row.get("Technical_Pattern") or None,
        source_tag=row.get("Source_Tag") or None,
    )


def fetch_watchlist_entry(ticker: str) -> WatchlistEntry:
    """
    שולף את הידע המתויג-ידנית עבור מניה מתוך data/watchlist.csv.
    אם המניה לא ברשימה - found=False, ואין שום ניחוש של ערכים.
    """
    ticker = ticker.upper()
    if not os.path.isfile(WATCHLIST_PATH):
        return WatchlistEntry(ticker=ticker, found=False)

    with open(WATCHLIST_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Ticker"].upper() == ticker:
                return _row_to_entry(row)

    return WatchlistEntry(ticker=ticker, found=False)


def load_all_watchlist_entries() -> list[WatchlistEntry]:
    """
    טוען את כל השורות מ-watchlist.csv כרשימת WatchlistEntry.
    זהו הבסיס לשכבת הדמיון (tools/similarity.py) - כדי למצוא את המניה
    הדומה ביותר, צריך קודם את הנתונים המתויגים של *כל* המניות ברשימה.
    """
    if not os.path.isfile(WATCHLIST_PATH):
        return []

    entries = []
    with open(WATCHLIST_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(_row_to_entry(row))
    return entries
