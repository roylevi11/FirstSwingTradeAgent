"""
external_sources.py
====================
מקורות מידע חיצוניים חינמיים, ללא מפתח API וללא Claude API:

- Finviz         : כותרות חדשות + נתוני snapshot (יעד אנליסטים, RSI, Short Float...)
                   - קריאת דף ה-quote הציבורי (HTML).
- StockTwits     : סנטימנט קהילתי (Bullish/Bearish) מהזרם הציבורי של הסימבול.
- TradingView    : המלצה טכנית מצטברת (Recommend.All) ואינדיקטורים, דרך נקודת
                   הקצה הציבורית של ה-scanner. אין כאן API רשמי - זו נקודת קצה
                   לא מתועדת שעלולה להשתנות; כל כשל מדווח, לא מוסתר.
- MMR Screener   : marketmomentumradar.com/api/screener/momentum - אותו JSON
                   שדף ה-momentum-screener עצמו קורא (MMR/Chart/Entry/Bottoming).

כללי ברזל זהים לשאר הכלים: כל כשל (רשת, חסימה, שינוי מבנה) מוחזר כ-
{"available": False, "error": ...} - לעולם לא ממציאים נתון חסר. בקשות
בודדות ועדינות בלבד (ללא לולאות סריקה אגרסיביות), עם User-Agent ומטמון.
"""

import html
import json
import re
import time
import urllib.error
import urllib.request

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_TIMEOUT = 20
_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5 דקות


def _http(url: str, data: bytes | None = None, headers: dict | None = None) -> str:
    key = f"{url}|{data!r}"
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]  # type: ignore[return-value]
    req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    _CACHE[key] = (time.time(), body)
    return body


def _fail(source: str, exc: Exception) -> dict:
    return {"source": source, "available": False, "error": f"{type(exc).__name__}: {exc}"}


# ----------------------------- Finviz -----------------------------

_FINVIZ_KEYS = [
    "Price", "P/E", "Forward P/E", "Target Price", "Recom", "RSI (14)", "Rel Volume",
    "Short Float", "Earnings", "Perf Week", "Perf Month", "SMA20", "SMA50", "SMA200",
    "52W High", "52W Low", "Beta",
]


def parse_finviz(page: str, limit: int = 8) -> dict:
    news = []
    table = re.search(r'id="news-table".*?</table>', page, re.S)
    if table:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(0), re.S)
        for row in rows:
            link = re.search(r'<a[^>]*class="tab-link-news"[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', row, re.S)
            if not link:
                continue
            when = re.search(r"<td[^>]*>\s*([^<]+?)\s*</td>", row, re.S)
            src = re.search(r"<span>\(([^)]*)\)</span>", row)
            news.append(
                {
                    "time": html.unescape(when.group(1)).strip() if when else None,
                    "headline": html.unescape(re.sub(r"<[^>]+>", "", link.group(2))).strip(),
                    "source": html.unescape(src.group(1)) if src else None,
                    "url": html.unescape(link.group(1)),
                }
            )
            if len(news) >= limit:
                break

    snapshot = {}
    pairs = re.findall(
        r'snapshot-td-label">(.*?)</div></td>\s*<td[^>]*>\s*<div class="snapshot-td-content">(.*?)</div></td>',
        page,
        re.S,
    )
    for label, value in pairs:
        label = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        if label in _FINVIZ_KEYS and label not in snapshot:
            snapshot[label] = html.unescape(re.sub(r"<[^>]+>", "", value)).strip()

    return {"source": "finviz", "available": bool(news or snapshot), "news": news, "snapshot": snapshot}


def fetch_finviz(ticker: str, limit: int = 8) -> dict:
    try:
        page = _http(f"https://finviz.com/quote.ashx?t={ticker.upper()}")
        result = parse_finviz(page, limit)
        result["ticker"] = ticker.upper()
        if not result["available"]:
            result["error"] = "לא נמצאו חדשות/נתונים בדף (הסימבול לא קיים או שמבנה הדף השתנה)"
        return result
    except Exception as exc:
        return {"ticker": ticker.upper(), **_fail("finviz", exc)}


# ---------------------------- StockTwits ----------------------------


def parse_stocktwits(payload: dict, max_messages: int = 5) -> dict:
    messages = payload.get("messages", [])
    bull = bear = 0
    recent = []
    for m in messages:
        sentiment = ((m.get("entities") or {}).get("sentiment") or {}).get("basic")
        if sentiment == "Bullish":
            bull += 1
        elif sentiment == "Bearish":
            bear += 1
        if len(recent) < max_messages:
            recent.append(
                {
                    "created_at": m.get("created_at"),
                    "user": (m.get("user") or {}).get("username"),
                    "sentiment": sentiment,
                    "text": (m.get("body") or "")[:240],
                }
            )
    tagged = bull + bear
    return {
        "source": "stocktwits",
        "available": True,
        "messages_sampled": len(messages),
        "bullish": bull,
        "bearish": bear,
        "bullish_share_of_tagged": round(bull / tagged, 2) if tagged else None,
        "watchlist_count": (payload.get("symbol") or {}).get("watchlist_count"),
        "recent_messages": recent,
        "note": "סנטימנט קהילתי לא מסונן ורועש - אינדיקציה בלבד, לא בסיס להחלטה.",
    }


def fetch_stocktwits(ticker: str) -> dict:
    try:
        raw = _http(f"https://api.stocktwits.com/api/2/streams/symbol/{ticker.upper()}.json")
        result = parse_stocktwits(json.loads(raw))
        result["ticker"] = ticker.upper()
        return result
    except Exception as exc:
        return {"ticker": ticker.upper(), **_fail("stocktwits", exc)}


# ---------------------------- TradingView ----------------------------

_TV_COLUMNS = [
    "close", "change", "Recommend.All", "Recommend.MA", "Recommend.Other", "RSI",
    "SMA20", "SMA50", "SMA200", "ATR", "ADX", "Perf.W", "Perf.1M", "relative_volume_10d_calc",
]


def _tv_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 0.5:
        return "Strong Buy"
    if score >= 0.1:
        return "Buy"
    if score > -0.1:
        return "Neutral"
    if score > -0.5:
        return "Sell"
    return "Strong Sell"


def parse_tradingview(payload: dict) -> dict | None:
    rows = payload.get("data") or []
    if not rows:
        return None
    row = rows[0]
    values = dict(zip(_TV_COLUMNS, row["d"]))
    return {
        "source": "tradingview",
        "available": True,
        "tv_symbol": row["s"],
        "indicators": values,
        "recommendation_all": _tv_label(values.get("Recommend.All")),
        "recommendation_ma": _tv_label(values.get("Recommend.MA")),
        "recommendation_oscillators": _tv_label(values.get("Recommend.Other")),
        "note": "דירוג טכני מצטבר של TradingView (יומי); נקודת קצה לא רשמית.",
    }


def fetch_tradingview_technicals(ticker: str) -> dict:
    t = ticker.upper()
    body = json.dumps(
        {
            "symbols": {"tickers": [f"NASDAQ:{t}", f"NYSE:{t}", f"AMEX:{t}"]},
            "columns": _TV_COLUMNS,
        }
    ).encode()
    try:
        raw = _http(
            "https://scanner.tradingview.com/america/scan",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        result = parse_tradingview(json.loads(raw))
        if result is None:
            return {"ticker": t, "source": "tradingview", "available": False, "error": "הסימבול לא נמצא (NASDAQ/NYSE/AMEX)"}
        result["ticker"] = t
        return result
    except Exception as exc:
        return {"ticker": t, **_fail("tradingview", exc)}


# --------------------------- MMR screener ---------------------------

_MMR_URL = "https://marketmomentumradar.com/api/screener/momentum"
_MMR_PAGE = 500  # תקרת השרת לעמוד


def _slim_mmr_row(row: dict) -> dict:
    def g(block: str, key: str):
        return (row.get(block) or {}).get(key)

    event = row.get("event") or {}
    return {
        "ticker": row.get("ticker"),
        "name": row.get("name"),
        "as_of": row.get("as_of"),
        "mmr_score": g("mmr", "mmr_score"),
        "chart_score": g("chart", "chart_score"),
        "entry_readiness": g("entry", "entry_readiness"),
        "bottoming_score": g("bottoming", "bottoming_score"),
        "bottoming_state": g("bottoming", "state"),
        "event_state": event.get("state_label") if event.get("status") == "EVENT" else None,
    }


def fetch_momentum_screener(
    ticker: str | None = None,
    min_entry_readiness: float | None = None,
    min_chart_score: float | None = None,
    min_mmr_score: float | None = None,
    limit: int = 10,
) -> dict:
    """
    ללא ticker: מחזיר את המניות המובילות (Entry Readiness ואז Chart Score)
    בהתאם לפילטרים. עם ticker: מחפש את המניה (עד ~8 עמודי 500 שורות,
    ~2 שניות כל אחד; נשמר במטמון 5 דקות). הציונים הם של MMR - לא שלנו.
    """
    filters = {
        "min_entry_readiness": min_entry_readiness,
        "min_chart_score": min_chart_score,
        "min_mmr_score": min_mmr_score,
    }
    query = "&".join(f"{k}={v}" for k, v in filters.items() if v is not None)
    base = f"{_MMR_URL}?rank=entry_first&{query}" if query else f"{_MMR_URL}?rank=entry_first"

    try:
        if ticker is None:
            data = json.loads(_http(f"{base}&limit={max(1, min(limit, 50))}"))
            return {
                "source": "mmr_screener",
                "available": bool(data.get("ok")),
                "matched": data["meta"].get("matched"),
                "rows": [_slim_mmr_row(r) for r in data.get("rows", [])],
            }

        t = ticker.upper()
        offset = 0
        while True:
            data = json.loads(_http(f"{base}&limit={_MMR_PAGE}&offset={offset}"))
            for r in data.get("rows", []):
                if (r.get("ticker") or "").upper() == t:
                    return {"source": "mmr_screener", "available": True, "found": True, "row": _slim_mmr_row(r)}
            offset += _MMR_PAGE
            if offset >= (data["meta"].get("matched") or 0) or not data.get("rows"):
                break
        return {
            "source": "mmr_screener",
            "available": True,
            "found": False,
            "note": f"{t} לא מופיעה במניות שה-MMR מכסה ומצליחה לדרג (או עדיין 'pending').",
        }
    except Exception as exc:
        return _fail("mmr_screener", exc)
