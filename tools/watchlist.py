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
    price_source: str | None = None  # 'live' = מחיר אמיתי מ-yfinance; None = לא הועשר
    levels_status: str | None = None  # OK / PRICE_ABOVE_RESISTANCE / PRICE_BELOW_SUPPORT


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


def _apply_live_price(entry: WatchlistEntry) -> WatchlistEntry:
    """
    מחליף את המחיר שבקובץ (שהיה רק כדי להניע את הפרויקט) במחיר האמיתי,
    ובודק אם רמות התמיכה/התנגדות המתויגות עדיין רלוונטיות אליו.
    אם המחיר החי לא זמין - current_price נשאר None (לא חוזרים למחיר הקובץ).
    """
    from tools.market_data import fetch_live_price

    entry.current_price = fetch_live_price(entry.ticker)
    entry.price_source = "live" if entry.current_price is not None else "unavailable"
    if entry.current_price is not None and entry.key_support is not None and entry.key_resistance is not None:
        if entry.current_price > entry.key_resistance:
            entry.levels_status = "PRICE_ABOVE_RESISTANCE"
        elif entry.current_price < entry.key_support:
            entry.levels_status = "PRICE_BELOW_SUPPORT"
        else:
            entry.levels_status = "OK"
    return entry


def fetch_watchlist_entry(ticker: str, live_price: bool = True) -> WatchlistEntry:
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
                entry = _row_to_entry(row)
                return _apply_live_price(entry) if live_price else entry

    return WatchlistEntry(ticker=ticker, found=False)


def load_all_watchlist_entries(live_prices: bool = False) -> list[WatchlistEntry]:
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
            entry = _row_to_entry(row)
            entries.append(_apply_live_price(entry) if live_prices else entry)
    return entries
