"""
run_mentor_pipeline.py
========================
הרצה מהטרמינל:  python run_mentor_pipeline.py
(דורש .env עם ANTHROPIC_API_KEY, ו-pip install youtube-transcript-api)

רץ על כל המנטורים ברשימת tools/mentor_pipeline.MENTORS. מנטור בלי
video_id מוגדר (כרגע: Assaf_Marciano) מדולג בבירור, לא נכשל בשקט.
"""

from dotenv import load_dotenv

from tools.mentor_pipeline import MENTORS, run_pipeline_for_mentor

load_dotenv()


def main() -> None:
    print(f"מריץ צינור מנטורים על {len(MENTORS)} מנטורים...\n")
    for mentor in MENTORS:
        result = run_pipeline_for_mentor(mentor)
        print(f"  {mentor['name']}: {result}")
    print("\nהושלם. בדוק/י את data/watchlist.csv לשורות חדשות.")


if __name__ == "__main__":
    main()
