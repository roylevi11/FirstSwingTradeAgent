"""
earnings.py
===========
בדיקת מועד הדוחות הכספיים הקרוב - זהו בדיוק הכלי שהוחלף בעבודה 2
בחיפוש Google Grounding כי לא הייתה גישה ל-API ייעודי. עכשיו יש.

מחזיר את מספר ימי המסחר עד לדוחות (לא ימי לוח שנה) כדי שיתאים ישירות
לחוק הברזל EARNINGS_BLACKOUT_DAYS ב-config/rules_config.py.
"""

from dataclasses import dataclass
from datetime import datetime, date

import yfinance as yf


@dataclass
class EarningsInfo:
    ticker: str
    next_earnings_date: str | None
    trading_days_until: int | None
    data_available: bool


def _count_trading_days(from_date: date, to_date: date) -> int:
    """סופר ימי מסחר (שני-שישי, ללא ניכוי חגים) בין שני תאריכים."""
    if to_date < from_date:
        return 0
    days = 0
    current = from_date
    while current < to_date:
        current = current.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:  # 0=שני ... 4=שישי
            days += 1
    return days


def fetch_earnings_calendar(ticker: str) -> EarningsInfo:
    """
    שולף את מועד הדוחות הכספיים הקרוב הבא עבור מניה.
    אם הנתון לא זמין - data_available=False ואין ניחוש של תאריך.
    """
    yf_ticker = yf.Ticker(ticker)

    next_date = None
    try:
        cal = yf_ticker.calendar
        # yfinance מחזיר לרוב dict עם מפתח "Earnings Date" (רשימת תאריכים אפשריים)
        if isinstance(cal, dict) and "Earnings Date" in cal and cal["Earnings Date"]:
            next_date = cal["Earnings Date"][0]
    except Exception:
        next_date = None

    if next_date is None:
        return EarningsInfo(
            ticker=ticker.upper(),
            next_earnings_date=None,
            trading_days_until=None,
            data_available=False,
        )

    trading_days = _count_trading_days(date.today(), next_date)
    return EarningsInfo(
        ticker=ticker.upper(),
        next_earnings_date=next_date.isoformat(),
        trading_days_until=trading_days,
        data_available=True,
    )
