"""
orders.py
=========
"במקום להיות צ'אט שמסיים ב'בהצלחה במסחר', הוא ייצר תוצר עבודה ייעודי
(תזכיר עסקה) ועצר במכוון לפני ביצוע פעולה רגישה כדי לבקש אישור."
(מהעבודות הקודמות - עקרון ה-Approval-Based Copilot)

הפונקציה הזו אף פעם לא שולחת פקודה לברוקר, לא נוגעת בכסף אמיתי,
ולא "מבצעת" שום דבר. היא רק מארגנת טיוטה מובנית ושומרת אותה ליומן
(מבסיס ל-REQ-04 / DREAM: Audit Log) לצורך מעקב ולקחים.
"""

import csv
import os
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TradeSetupMemo:
    ticker: str
    company_name: str
    technical_pattern: str
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward_ratio: float
    shares: int | None
    status: str  # "APPROVED" | "REJECTED"
    rejection_reasons: list
    rationale: str
    created_at: str
    awaiting_approval: bool = True


def create_draft_order(
    ticker: str,
    company_name: str,
    technical_pattern: str,
    entry_price: float,
    stop_loss: float,
    target_price: float,
    risk_reward_ratio: float,
    status: str,
    rejection_reasons: list | None = None,
    shares: int | None = None,
    rationale: str = "",
    log_path: str = "data/audit_log.csv",
) -> TradeSetupMemo:
    """
    יוצר תזכיר עסקה מובנה (Trade Setup Memo) ושומר אותו ביומן.
    status חייב להיות "APPROVED" או "REJECTED" - מגיע ממנוע החוקים
    (tools/rules_engine.py), לא מהחלטה חופשית של המודל.
    """
    memo = TradeSetupMemo(
        ticker=ticker.upper(),
        company_name=company_name,
        technical_pattern=technical_pattern,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        risk_reward_ratio=risk_reward_ratio,
        shares=shares,
        status=status,
        rejection_reasons=rejection_reasons or [],
        rationale=rationale,
        created_at=datetime.utcnow().isoformat(),
        awaiting_approval=(status == "APPROVED"),
    )

    _append_to_audit_log(memo, log_path)
    return memo


def _append_to_audit_log(memo: TradeSetupMemo, log_path: str) -> None:
    """שומר כל תזכיר (מאושר או נדחה) ליומן CSV - הבסיס ל-Audit Log העתידי."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    file_exists = os.path.isfile(log_path)
    row = asdict(memo)
    row["rejection_reasons"] = " | ".join(row["rejection_reasons"])

    with open(log_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def format_memo_hebrew(memo: TradeSetupMemo) -> str:
    """מציג את התזכיר בפורמט הטקסטואלי המוכר מהעבודות הקודמות."""
    if memo.status == "REJECTED":
        reasons = "\n".join(f"  - {r}" for r in memo.rejection_reasons)
        return (
            f"מניה: {memo.ticker} ({memo.company_name})\n"
            f"סטטוס: נכשל / נדחה\n"
            f"סיבות:\n{reasons}\n"
            f"סיכום: העסקה אינה מאושרת לביצוע."
        )

    shares_line = f"כמות מניות מומלצת: {memo.shares}\n" if memo.shares else ""
    return (
        f"תזכיר עסקה (Trade Setup Memo)\n"
        f"מניה: {memo.ticker} ({memo.company_name})\n"
        f"תבנית טכנית: {memo.technical_pattern}\n"
        f"מחיר כניסה: ${memo.entry_price}\n"
        f"סטופ-לוס: ${memo.stop_loss}\n"
        f"מחיר יעד: ${memo.target_price}\n"
        f"יחס סיכון/סיכוי: 1:{memo.risk_reward_ratio}\n"
        f"{shares_line}"
        f"נימוק: {memo.rationale}\n\n"
        f"טיוטת הפקודה הוכנה וממתינה לאישורך לפני שליחה לביצוע."
    )
