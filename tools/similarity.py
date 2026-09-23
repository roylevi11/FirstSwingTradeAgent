"""
similarity.py
=============
Phase C: שכבת הדמיון מעבודה 3, הפעם בקוד פייתון אמיתי וסקיילבילי -
לא תלוי בהדבקת פרומפט ב-AI Studio, ועובד על כל אורך רשימת המעקב.

שני אלגוריתמים, בדיוק כמו בעבודה 3:
- Cosine Similarity: משווה כיוון של וקטור תכונות (כולל מספריות מנורמלות).
- Jaccard Similarity: משווה חפיפת תגיות קטגוריות בלבד (סקטור/תבנית/קרבה-לדוחות).

התכונות (Features) בשימוש: Sector, Technical_Pattern, Risk:Reward (מחושב
דרך tools/risk.py - לא מאוחסן, כדי שלא יהיה נתון כפול/לא מעודכן),
ו-Days_To_Earnings.
"""

import math
from dataclasses import dataclass

from tools.watchlist import WatchlistEntry, load_all_watchlist_entries
from tools.risk import calc_risk_reward


@dataclass
class SimilarityResult:
    ticker: str
    company_name: str | None
    score: float
    technical_pattern: str | None
    sector: str | None
    risk_reward_ratio: float | None


def _entry_risk_reward(entry: WatchlistEntry) -> float | None:
    """מחשב R:R לפי הנתונים בקובץ, אם קיימים כל שלושת המחירים."""
    if entry.current_price is None or entry.key_support is None or entry.key_resistance is None:
        return None
    # מחיר מחוץ לטווח [תמיכה, התנגדות] = הרמות המתויגות התיישנו; לא מחשבים R:R מטעה
    if not (entry.key_support < entry.current_price < entry.key_resistance):
        return None
    try:
        return calc_risk_reward(entry.current_price, entry.key_support, entry.key_resistance).ratio
    except ValueError:
        return None


def _minmax_normalize(value: float, all_values: list[float]) -> float:
    """נרמול Min-Max ל-[0,1], כדי שערך גדול (כמו ימים לדוחות) לא 'יבלע' ערך קטן (כמו R:R)."""
    lo, hi = min(all_values), max(all_values)
    if hi == lo:
        return 0.5  # כל הערכים זהים - אין מידע מבחין, ניטרלי
    return (value - lo) / (hi - lo)


def _build_feature_vector(
    entry: WatchlistEntry,
    all_entries: list[WatchlistEntry],
    all_sectors: list[str],
    all_patterns: list[str],
    include_sector: bool,
) -> list[float]:
    """
    בונה וקטור תכונות בדיוק כמו שהוסבר בשיחה: One-Hot לקטגוריות,
    Min-Max Normalization למספריות. include_sector=False מדמה את ניסוי
    "הסרת הסקטור" מעבודה 3.
    """
    vector: list[float] = []

    if include_sector:
        vector += [1.0 if entry.sector == s else 0.0 for s in all_sectors]

    vector += [1.0 if entry.technical_pattern == p else 0.0 for p in all_patterns]

    all_rr = [rr for e in all_entries if (rr := _entry_risk_reward(e)) is not None]
    entry_rr = _entry_risk_reward(entry)
    vector.append(_minmax_normalize(entry_rr, all_rr) if entry_rr is not None and all_rr else 0.5)

    all_days = [e.days_to_earnings for e in all_entries if e.days_to_earnings is not None]
    vector.append(
        _minmax_normalize(entry.days_to_earnings, all_days)
        if entry.days_to_earnings is not None and all_days
        else 0.5
    )

    return vector


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return round(dot / (norm1 * norm2), 4)


def _tag_set(entry: WatchlistEntry) -> set:
    """תגיות קטגוריות עבור ג'קארד: סקטור, תבנית, ו'דלי' קרבה-לדוחות (רחוק/קרוב)."""
    tags = set()
    if entry.sector:
        tags.add(f"sector:{entry.sector}")
    if entry.technical_pattern:
        tags.add(f"pattern:{entry.technical_pattern}")
    if entry.days_to_earnings is not None:
        bucket = "earnings:far" if entry.days_to_earnings >= 30 else "earnings:near"
        tags.add(bucket)
    return tags


def jaccard_similarity(entry_a: WatchlistEntry, entry_b: WatchlistEntry) -> float:
    tags_a, tags_b = _tag_set(entry_a), _tag_set(entry_b)
    union = tags_a | tags_b
    if not union:
        return 0.0
    intersection = tags_a & tags_b
    return round(len(intersection) / len(union), 4)


def find_similar_stocks(
    base_ticker: str,
    method: str = "cosine",
    include_sector: bool = True,
    top_n: int = 5,
    entries: list[WatchlistEntry] | None = None,
) -> list[SimilarityResult]:
    """
    נקודת הכניסה הראשית: מוצא את N המניות הדומות ביותר ל-base_ticker
    מתוך כל רשימת המעקב, לפי method ("cosine" | "jaccard").
    entries ניתן להזרקה (לבדיקות); ברירת מחדל: כל data/watchlist.csv.
    """
    if entries is None:
        entries = load_all_watchlist_entries(live=True)

    base = next((e for e in entries if e.ticker.upper() == base_ticker.upper()), None)
    if base is None:
        return []

    candidates = [e for e in entries if e.ticker.upper() != base.ticker.upper()]

    results: list[SimilarityResult] = []

    if method == "jaccard":
        for c in candidates:
            score = jaccard_similarity(base, c)
            results.append(
                SimilarityResult(
                    ticker=c.ticker, company_name=c.company_name, score=score,
                    technical_pattern=c.technical_pattern, sector=c.sector,
                    risk_reward_ratio=_entry_risk_reward(c),
                )
            )
    else:  # cosine
        all_sectors = sorted({e.sector for e in entries if e.sector})
        all_patterns = sorted({e.technical_pattern for e in entries if e.technical_pattern})
        base_vec = _build_feature_vector(base, entries, all_sectors, all_patterns, include_sector)
        for c in candidates:
            c_vec = _build_feature_vector(c, entries, all_sectors, all_patterns, include_sector)
            score = cosine_similarity(base_vec, c_vec)
            results.append(
                SimilarityResult(
                    ticker=c.ticker, company_name=c.company_name, score=score,
                    technical_pattern=c.technical_pattern, sector=c.sector,
                    risk_reward_ratio=_entry_risk_reward(c),
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]


def find_valid_alternative(
    base_ticker: str,
    min_risk_reward: float,
    entries: list[WatchlistEntry] | None = None,
) -> SimilarityResult | None:
    """
    זו ה-'שכבת דמיון' בפועל כפי שתוארה ב-System Prompt: כשעסקה נפסלת,
    מוצאים את המניה הדומה ביותר (קוסינוס, כולל סקטור) שכן עומדת ב-R:R
    המינימלי הנדרש. מחזיר None אם אין חלופה מתאימה ברשימה.
    """
    ranked = find_similar_stocks(base_ticker, method="cosine", include_sector=True, top_n=50, entries=entries)
    for candidate in ranked:
        if candidate.risk_reward_ratio is not None and candidate.risk_reward_ratio >= min_risk_reward:
            return candidate
    return None
