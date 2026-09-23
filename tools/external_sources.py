"""
external_sources.py
====================
מקורות מידע חיצוניים חינמיים, ללא מפתח API וללא Claude API:

- Finviz         : כותרות חדשות + נתוני snapshot (יעד אנליסטים, RSI, Short Float...)
                   - קריאת דף ה-quote הציבורי (HTML).

כללי ברזל זהים לשאר הכלים: כל כשל (רשת, חסימה, שינוי מבנה) מוחזר כ-
{"available": False, "error": ...} - לעולם לא ממציאים נתון חסר. בקשות
בודדות ועדינות בלבד (ללא לולאות סריקה אגרסיביות), עם User-Agent ומטמון.
"""

import html
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
