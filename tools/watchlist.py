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
    key_support: float | None = None
    key_resistance: float | None = None
    technical_pattern: str | None = None
    source_tag: str | None = None


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
                def _to_float(v):
                    try:
                        return float(v) if v not in (None, "") else None
                    except ValueError:
                        return None

                return WatchlistEntry(
                    ticker=ticker,
                    found=True,
                    company_name=row.get("Company_Name") or None,
                    sector=row.get("Sector") or None,
                    key_support=_to_float(row.get("Key_Support")),
                    key_resistance=_to_float(row.get("Key_Resistance")),
                    technical_pattern=row.get("Technical_Pattern") or None,
                    source_tag=row.get("Source_Tag") or None,
                )

    return WatchlistEntry(ticker=ticker, found=False)
