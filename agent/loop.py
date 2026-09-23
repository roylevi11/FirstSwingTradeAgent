"""
loop.py
=======
לולאת הסוכן: Observe -> Think -> Act, בדיוק לפי המבנה שהוגדר בעבודה 1
ושהוסבר בעומק בשיחה עם Gemini (5 שלבים: Fetching, Pre-condition Checks,
Quantitative Analysis, Synthesis, Human Gatekeeper).

ההבדל המרכזי מהגרסה ב-AI Studio: כאן זו לולאת Python אמיתית שמריצה
Claude API עם Tool Use, ולא צ'אט בממשק גרפי. זה מה שהופך את זה
מ"תרגיל" למערכת שאפשר להריץ אוטומטית, לתזמן, ולהרחיב.
"""

import json
import os

import anthropic

from agent.prompts import SYSTEM_PROMPT
from agent.tool_definitions import ALL_TOOLS
from config.rules_config import MAX_AGENT_STEPS, ANALYST_MODEL
from tools.market_data import fetch_market_data, fetch_recent_ohlc
from tools.earnings import fetch_earnings_calendar
from tools.watchlist import fetch_watchlist_entry
from tools.similarity import find_similar_stocks, find_valid_alternative
from tools.patterns import detect_patterns
from tools.indicators import analyze_indicators
from tools.multi_timeframe import analyze_multi_timeframe
from tools.finviz_screener import run_momentum_screen
from tools.risk import calc_position_size
from tools.rules_engine import evaluate_hard_rules
from tools.orders import create_draft_order, format_memo_hebrew


def _dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """
    מנתב קריאת כלי מ-Claude לפונקציית Python המתאימה, ומחזיר תוצאה כ-dict.
    זהו נקודת המעבר הקריטית: מכאן ואילך זה קוד דטרמיניסטי, לא LLM.
    """
    if tool_name == "fetch_market_data":
        snapshot = fetch_market_data(tool_input["ticker"])
        return snapshot.__dict__

    if tool_name == "fetch_earnings_calendar":
        info = fetch_earnings_calendar(tool_input["ticker"])
        return info.__dict__

    if tool_name == "fetch_watchlist_entry":
        entry = fetch_watchlist_entry(tool_input["ticker"])
        return entry.__dict__

    if tool_name == "find_similar_stocks":
        min_rr = tool_input.get("min_risk_reward")
        if min_rr is not None:
            alt = find_valid_alternative(tool_input["ticker"], min_risk_reward=min_rr)
            return {"best_valid_alternative": alt.__dict__ if alt else None}
        ranked = find_similar_stocks(tool_input["ticker"])
        return {"ranked_candidates": [r.__dict__ for r in ranked]}

    if tool_name == "fetch_recent_ohlc":
        return {
            "candles": fetch_recent_ohlc(
                tool_input["ticker"], tool_input.get("days", 10), tool_input.get("interval", "1d")
            )
        }

    if tool_name == "detect_chart_patterns":
        patterns = detect_patterns(tool_input["candles"], tool_input.get("support_level"))
        return {"patterns_found": patterns}

    if tool_name == "analyze_technical_indicators":
        return analyze_indicators(tool_input["candles"])

    if tool_name == "analyze_multi_timeframe":
        return analyze_multi_timeframe(tool_input["ticker"])

    if tool_name == "run_finviz_screen":
        results = run_momentum_screen(tool_input.get("filters"), tool_input.get("limit", 20))
        return {"stocks": [r.__dict__ for r in results]}

    if tool_name == "evaluate_trade":
        return _dispatch_evaluate_trade(tool_input)

    raise ValueError(f"כלי לא מוכר: {tool_name}")


def _dispatch_evaluate_trade(tool_input: dict) -> dict:
    """
    מריץ את מנוע חוקי הברזל + חישוב גודל פוזיציה + יצירת תזכיר, בשלב אחד.
    זהו ה"שער" הדטרמיניסטי היחיד שדרכו יוצאת כל החלטה.
    """
    entry = tool_input["entry_price"]
    stop = tool_input["stop_loss"]
    target = tool_input["target_price"]
    days_to_earnings = tool_input["days_to_earnings"]
    account_size = tool_input.get("account_size")

    risk_pct_of_account = None
    shares = None
    if account_size:
        # אחוז הסיכון המבוקש מחושב לפי כלל ברירת המחדל שבקונפיג;
        # calc_position_size מחזיר גם את כמות המניות המתאימה.
        from config.rules_config import MAX_RISK_PERCENT_PER_TRADE

        position = calc_position_size(account_size, MAX_RISK_PERCENT_PER_TRADE, entry, stop)
        shares = position["shares"]
        risk_pct_of_account = MAX_RISK_PERCENT_PER_TRADE

    verdict = evaluate_hard_rules(
        days_to_earnings=days_to_earnings,
        entry_price=entry,
        stop_loss=stop,
        target_price=target,
        risk_percent_of_account=risk_pct_of_account,
    )

    from tools.risk import calc_risk_reward

    rr = calc_risk_reward(entry, stop, target)

    memo = create_draft_order(
        ticker=tool_input["ticker"],
        company_name=tool_input["company_name"],
        technical_pattern=tool_input["technical_pattern"],
        entry_price=entry,
        stop_loss=stop,
        target_price=target,
        risk_reward_ratio=rr.ratio,
        status="APPROVED" if verdict.passed else "REJECTED",
        rejection_reasons=verdict.rejection_reasons,
        shares=shares,
        rationale=tool_input.get("rationale", ""),
    )

    return {
        "verdict": verdict.passed,
        "checks": {k: {"passed": v[0], "detail": v[1]} for k, v in verdict.checks.items()},
        "memo_text": format_memo_hebrew(memo),
        "memo": memo.__dict__,
    }


def run_agent(user_request: str, api_key: str | None = None) -> dict:
    """
    נקודת הכניסה הראשית. מקבל בקשה בשפה חופשית (למשל "תסרוק את מניית NVDA
    ותגיד לי האם מומלץ להיכנס לעסקת סווינג היום"), ומריץ את לולאת הסוכן
    עד MAX_AGENT_STEPS צעדים או עד שמתקבלת תשובה סופית.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    messages = [{"role": "user", "content": user_request}]
    steps_used = 0

    for step in range(MAX_AGENT_STEPS):
        steps_used += 1
        response = client.messages.create(
            model=ANALYST_MODEL,
            max_tokens=12000,  # הועלה מ-2048 בעקבות ריצה אמיתית: תשובות מרובות-כלים
            # (למשל NVDA שנדחה + חיפוש חלופה + תזכיר מלא) נחתכו בתקרה נמוכה יותר.
            system=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(block.text for block in response.content if block.type == "text")
            return {"final_text": final_text, "steps_used": steps_used}

        # יש קריאות כלים לביצוע - מריצים כל אחת ומחזירים תוצאה
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "web_search":
                # כלי שרת (Server Tool) - Claude מבצע אותו בעצמו, אין צורך לתת תוצאה ידנית
                continue
            try:
                result = _dispatch_tool(block.name, block.input)
                content = json.dumps(result, ensure_ascii=False)
            except Exception as exc:  # לעולם לא "נופלים" בשקט - מדווחים לסוכן על השגיאה
                content = json.dumps({"error": str(exc)}, ensure_ascii=False)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": content}
            )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return {
        "final_text": "הסוכן הגיע למספר הצעדים המקסימלי (MAX_AGENT_STEPS) בלי מסקנה סופית.",
        "steps_used": steps_used,
    }
