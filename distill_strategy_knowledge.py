"""
distill_strategy_knowledge.py
===============================
הרצה חד-פעמית (לא סקריפט שבועי כמו run_mentor_pipeline.py):
    python distill_strategy_knowledge.py

מריץ על כל 30 השיעורים ב-tools/strategy_knowledge.LESSON_REGISTRY,
מייצר data/knowledge/assaf_marciano_methodology.md.

עלות משוערת: 30 קריאות Claude API (max_tokens=500 כל אחת) - סכום
קטן אבל לא אפסי. אפשר להריץ שוב בעתיד רק כדי לעדכן/לתקן שיעורים
שנכשלו (transcript_unavailable), לא חובה מהתחלה.
"""

from dotenv import load_dotenv

from tools.strategy_knowledge import run_full_distillation, LESSON_REGISTRY

load_dotenv()


def main() -> None:
    print(f"מעבד {len(LESSON_REGISTRY)} שיעורים - זה ייקח כמה דקות...\n")
    path = run_full_distillation()
    print(f"\nהושלם. קובץ הידע נשמר ב: {path}")
    print("אפשר לעבור עליו ולערוך ידנית לפני שהסוכן משתמש בו.")


if __name__ == "__main__":
    main()
