"""
main.py
=======
הרצה מהטרמינל:  python main.py NVDA
(דורש קובץ .env עם ANTHROPIC_API_KEY - ראו .env.example)

זו התחלת ה"אפליקציה העצמאית" שדוברה בשיחה עם Gemini - כבר לא תלויים
בכניסה ידנית ל-AI Studio; זו סקריפט שניתן להריץ, לתזמן (cron / GitHub
Actions, כמו שנעשה עבור DREAM-08), או לחבר בעתיד לדשבורד (DREAM-05).
"""

import sys

from dotenv import load_dotenv

from agent.loop import run_agent

load_dotenv()


def main() -> None:
    if len(sys.argv) < 2:
        print("שימוש: python main.py <TICKER>")
        print("דוגמה:  python main.py NVDA")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    custom_question = sys.argv[2] if len(sys.argv) > 2 else None
    request = custom_question or (
        f"תסרוק את מניית {ticker} ותגיד לי האם מומלץ להיכנס לעסקת סווינג "
        f"היום לפי הכללים שלנו. שלוף נתוני שוק, בדוק מועד דוחות, ואז הפעל "
        f"את evaluate_trade עם כל הנתונים כדי לקבל פסק דין סופי."
    )

    print(f"מריץ את הסוכן עבור {ticker}...\n")
    result = run_agent(request)
    print(result["final_text"])
    print(f"\n[הושלם ב-{result['steps_used']} צעדים]")
    print(f"[כלים שנבחרו: {', '.join(result['tools_used']) or 'אין'}]")


if __name__ == "__main__":
    main()
