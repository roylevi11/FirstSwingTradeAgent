"""
market_data.py
===============
מימוש חלקי-ראשוני של DREAM-01: החלפת ה-CSV הסטטי בחיבור API אמיתי.

הערה חשובה על מגבלות: yfinance נותן נתונים מדויקים אך לרוב במחיר סוף-יום
או בהשהיה קלה - זה עדיין לא Tick-by-Tick חי ברזולוציית מילישניות (לשם כך
נדרש בעתיד Polygon.io / Alpaca בתשלום, לפי הרוד-מאפ). אבל זה כבר שדרוג
עצום לעומת הזנה ידנית של CSV, וזה API ייעודי אמיתי - לא ניחוש טקסטואלי
מחיפוש גוגל כמו בניסוי TradingView שנכשל.

כלל הברזל שהודגם שם חל גם כאן: אם נתון חסר - מחזירים None ומדווחים על
כך, ולעולם לא ממציאים מספר.
"""

from dataclasses import dataclass
from datetime import datetime

import yfinance as yf


@dataclass
class MarketSnapshot:
    ticker: str
    company_name: str | None
    sector: str | None
    current_price: float | None
    market_cap: float | None
    pe_ratio: float | None
    fetched_at: str
    missing_fields: list


def fetch_market_data(ticker: str) -> MarketSnapshot:
    """
    שולף נתוני שוק עדכניים למניה בודדת.
    כל שדה שלא נמצא מדווח ב-missing_fields ומקבל None - אף פעם לא מומצא.
    """
    yf_ticker = yf.Ticker(ticker)
    info = yf_ticker.info or {}

    missing = []

    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if current_price is None:
        missing.append("current_price")

    company_name = info.get("longName") or info.get("shortName")
    if company_name is None:
        missing.append("company_name")

    sector = info.get("sector")
    if sector is None:
        missing.append("sector")

    market_cap = info.get("marketCap")
    if market_cap is None:
        missing.append("market_cap")

    pe_ratio = info.get("trailingPE")
    if pe_ratio is None:
        missing.append("pe_ratio")

    return MarketSnapshot(
        ticker=ticker.upper(),
        company_name=company_name,
        sector=sector,
        current_price=current_price,
        market_cap=market_cap,
        pe_ratio=pe_ratio,
        fetched_at=datetime.utcnow().isoformat(),
        missing_fields=missing,
    )


def fetch_recent_ohlc(ticker: str, days: int = 10) -> list[dict]:
    """
    שולף את ה-OHLC (Open, High, Low, Close) ההיסטורי של N הימים האחרונים.
    זהו הבסיס הדרוש עבור DREAM-02 (זיהוי תבניות כמו Inside Bar) בשלב הבא -
    התבנית לא "מנוחשת" מטקסט, אלא מחושבת מהנתונים המספריים האלה.
    """
    yf_ticker = yf.Ticker(ticker)
    hist = yf_ticker.history(period=f"{days}d")

    if hist.empty:
        return []

    records = []
    for date, row in hist.iterrows():
        records.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
        )
    return records
