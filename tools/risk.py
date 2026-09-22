"""
risk.py
=======
חישובים מתמטיים טהורים. שום פונקציה כאן לא "מנחשת" - הכל נוסחה קבועה.

זו בדיוק העקרון שהוכח בעבודה 2: כשהסוכן נשאל על יחס סיכון/סיכוי, הוא לא
ענה מהזיכרון - הוא הריץ קוד. הפונקציות כאן הן ה"קוד" הזה, בגרסה קבועה
ובדוקה, שהסוכן (agent/loop.py) יקרא לו בכל פעם דרך Function Calling.
"""

from dataclasses import dataclass


@dataclass
class RiskRewardResult:
    reward: float
    risk: float
    ratio: float  # ratio = reward / risk


def calc_risk_reward(entry_price: float, stop_loss: float, target_price: float) -> RiskRewardResult:
    """
    מחשב יחס סיכון/סיכוי (Risk:Reward Ratio).

    reward = |target_price - entry_price|
    risk   = |entry_price - stop_loss|
    ratio  = reward / risk

    לדוגמה (מבוסס NVDA בעבודה 2): entry=128.40, stop=118.00, target=140.00
        reward = 140.00 - 128.40 = 11.60
        risk   = 128.40 - 118.00 = 10.40
        ratio  = 11.60 / 10.40  = 1.115...  (נכשל, מתחת ל-2.0)
    """
    if entry_price <= 0 or stop_loss <= 0 or target_price <= 0:
        raise ValueError("כל המחירים חייבים להיות חיוביים")
    if stop_loss == entry_price:
        raise ValueError("מחיר הסטופ-לוס לא יכול להיות זהה למחיר הכניסה (חלוקה באפס)")

    reward = abs(target_price - entry_price)
    risk = abs(entry_price - stop_loss)
    ratio = reward / risk
    return RiskRewardResult(reward=round(reward, 4), risk=round(risk, 4), ratio=round(ratio, 4))


def calc_position_size(account_size: float, risk_percent: float, entry_price: float, stop_loss: float) -> dict:
    """
    מחשב כמות מניות לקנייה, לפי אחוז סיכון קבוע מהתיק (REQ-03 מעבודה 1/3).

    סכום הסיכון בדולרים = account_size * (risk_percent / 100)
    מרחק לסטופ (לכל מניה)  = |entry_price - stop_loss|
    כמות מניות            = סכום הסיכון בדולרים / מרחק לסטופ  (מעוגל למטה)

    לדוגמה: תיק של $50,000, סיכון 1.5%, כניסה $220.50, סטופ $215.00
        סכום סיכון = 50000 * 0.015 = $750
        מרחק לסטופ = 220.50 - 215.00 = $5.50
        כמות מניות = 750 / 5.50 = 136 מניות (מעוגל למטה)
    """
    if account_size <= 0:
        raise ValueError("גודל התיק חייב להיות חיובי")
    if risk_percent <= 0:
        raise ValueError("אחוז הסיכון חייב להיות חיובי")
    if stop_loss == entry_price:
        raise ValueError("מחיר הסטופ-לוס לא יכול להיות זהה למחיר הכניסה")

    risk_amount_usd = account_size * (risk_percent / 100)
    per_share_risk = abs(entry_price - stop_loss)
    shares = int(risk_amount_usd // per_share_risk)  # מעוגל למטה - אף פעם לא מסכנים יותר מהמותר

    return {
        "risk_amount_usd": round(risk_amount_usd, 2),
        "per_share_risk_usd": round(per_share_risk, 2),
        "shares": shares,
        "total_position_usd": round(shares * entry_price, 2),
    }
