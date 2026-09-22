"""
run_evaluation.py
==================
מריץ את סט הוולידציה (8 שאלות) ואת מבחן העמידות (5 שאלות) מול הסוכן
בפועל, ומפיק דוח Markdown עם התשובה בפועל לצד התשובה הצפויה - מוכן
למילוי ידני של "נכון/חלקי/שגוי" (עבור נושא 3, משימות 1-2 בדרישות
הפרויקט הסופי של הקורס).

דורש רשת + ANTHROPIC_API_KEY אמיתי - להרצה אצלך, לא בסביבת הכתיבה.

הרצה:  python -m eval.run_evaluation
פלט:   eval/evaluation_report.md
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv

from agent.loop import run_agent

load_dotenv()

HERE = os.path.dirname(__file__)


def _load(path: str) -> list:
    with open(os.path.join(HERE, path), encoding="utf-8") as f:
        return json.load(f)


def run_validation_set() -> list[dict]:
    questions = _load("validation_questions.json")
    results = []
    for q in questions:
        print(f"[ולידציה {q['id']}] מריץ: {q['question']}")
        response = run_agent(q["question"])
        results.append({**q, "agent_response": response["final_text"], "steps_used": response["steps_used"]})
    return results


def run_stress_test() -> list[dict]:
    questions = _load("stress_test_questions.json")
    results = []
    for q in questions:
        print(f"[עמידות {q['id']}] מריץ: {q['question']}")
        response = run_agent(q["question"])
        results.append({**q, "agent_response": response["final_text"], "steps_used": response["steps_used"]})
    return results


def write_report(validation_results: list[dict], stress_results: list[dict]) -> str:
    lines = [
        f"# דוח הערכה - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## סט ולידציה (8 שאלות, תשובה ידועה)",
        "",
        "| מזהה | שאלה | תשובה צפויה | תשובת הסוכן בפועל | ציון (למלא ידנית: נכון/חלקי/שגוי) |",
        "|---|---|---|---|---|",
    ]
    for r in validation_results:
        q = r["question"].replace("|", "\\|")
        exp = r["expected_answer"].replace("|", "\\|")
        act = r["agent_response"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r['id']} | {q} | {exp} | {act} | |")

    lines += [
        "",
        "**אחוז הצלחה:** למלא לאחר הציון הידני - (מספר 'נכון' / 8) * 100",
        "",
        "## מבחן עמידות (5 שאלות קשות)",
        "",
        "| מזהה | קטגוריה | שאלה | התנהגות צפויה | תשובת הסוכן בפועל | ציון (למלא ידנית: הצליח/נכשל) |",
        "|---|---|---|---|---|---|",
    ]
    for r in stress_results:
        q = r["question"].replace("|", "\\|")
        exp = r["expected_behavior"].replace("|", "\\|")
        act = r["agent_response"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r['id']} | {r['category']} | {q} | {exp} | {act} | |")

    lines += ["", "**אם נכשל - איך בדיוק נכשל:** למלא ידנית לכל שאלה שסומנה 'נכשל'."]

    return "\n".join(lines)


def main() -> None:
    print("מריץ סט ולידציה...")
    validation_results = run_validation_set()
    print("\nמריץ מבחן עמידות...")
    stress_results = run_stress_test()

    report = write_report(validation_results, stress_results)
    out_path = os.path.join(HERE, "evaluation_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nהדוח נשמר ב: {out_path}")
    print("פתח/י אותו ומלא/י ידנית את עמודות הציון (נכון/חלקי/שגוי, הצליח/נכשל).")


if __name__ == "__main__":
    main()
