"""
rules_engine.py
================
"חוקי ניהול סיכונים הם תנאי סף בינאריים (Pass/Fail)... לא מתקבלת החלטה
על בסיס 'נראה לי', אלא על בסיס עמידה מלאה בכל תנאי הסף." (מתוך השיחה עם Gemini)

הקובץ הזה הוא ה-Gatekeeper: הוא לא שואל LLM שום דבר, ולא ניתן "לשכנע"
אותו. ה-agent loop חייב להעביר דרכו כל עסקה, ואם היא נכשלת - היא נדחית,
נקודה. זו האכיפה בפועל של העיקרון "Separation of Logic from Computation"
שהוסבר בשיחה: לא נותנים למודל "לחשב בראש", והחלטת סירוב לא נתונה לפרשנות.
"""

from dataclasses import dataclass, field

from config.rules_config import (
    EARNINGS_BLACKOUT_DAYS,
    MIN_RISK_REWARD_RATIO,
    MAX_RISK_PERCENT_PER_TRADE,
)
from tools.risk import calc_risk_reward


@dataclass
class RuleCheckResult:
    passed: bool
    checks: dict = field(default_factory=dict)  # שם הכלל -> (עבר: bool, פירוט: str)
    rejection_reasons: list = field(default_factory=list)


def evaluate_hard_rules(
    days_to_earnings: int,
    entry_price: float,
    stop_loss: float,
    target_price: float,
    risk_percent_of_account: float | None = None,
) -> RuleCheckResult:
    """
    מריץ את כל חוקי הברזל על עסקה מוצעת ומחזיר פסק דין דטרמיניסטי.
    כל הכללים חייבים לעבור (AND לוגי) כדי שהעסקה תאושר.
    """
    checks: dict[str, tuple[bool, str]] = {}
    reasons: list[str] = []

    # כלל 1: קרבה לדוחות כספיים
    earnings_ok = days_to_earnings >= EARNINGS_BLACKOUT_DAYS
    checks["earnings_proximity"] = (
        earnings_ok,
        f"נותרו {days_to_earnings} ימי מסחר לדוחות (סף מינימלי: {EARNINGS_BLACKOUT_DAYS})",
    )
    if not earnings_ok:
        reasons.append(
            f"קרבה לדוחות: נותרו רק {days_to_earnings} ימים, פחות מהסף הנדרש של {EARNINGS_BLACKOUT_DAYS} ימים."
        )

    # כלל 2: יחס סיכון/סיכוי (מחושב בקוד, לא מנוחש)
    rr = calc_risk_reward(entry_price, stop_loss, target_price)
    rr_ok = rr.ratio >= MIN_RISK_REWARD_RATIO
    checks["risk_reward"] = (
        rr_ok,
        f"יחס מחושב 1:{rr.ratio} (רווח פוטנציאלי ${rr.reward} / סיכון פוטנציאלי ${rr.risk}), סף מינימלי 1:{MIN_RISK_REWARD_RATIO}",
    )
    if not rr_ok:
        reasons.append(
            f"יחס סיכון/סיכוי: 1:{rr.ratio} נמוך מהסף המינימלי הנדרש של 1:{MIN_RISK_REWARD_RATIO}."
        )

    # כלל 3 (אופציונלי): גודל הפוזיציה לא חורג מאחוז הסיכון המותר מהתיק
    if risk_percent_of_account is not None:
        risk_ok = risk_percent_of_account <= MAX_RISK_PERCENT_PER_TRADE
        checks["position_risk"] = (
            risk_ok,
            f"סיכון מבוקש {risk_percent_of_account}% מהתיק (סף מקסימלי: {MAX_RISK_PERCENT_PER_TRADE}%)",
        )
        if not risk_ok:
            reasons.append(
                f"גודל פוזיציה: הסיכון המבוקש ({risk_percent_of_account}%) חורג מהסף המקסימלי המותר ({MAX_RISK_PERCENT_PER_TRADE}%)."
            )

    overall_pass = all(ok for ok, _ in checks.values())
    return RuleCheckResult(passed=overall_pass, checks=checks, rejection_reasons=reasons)
