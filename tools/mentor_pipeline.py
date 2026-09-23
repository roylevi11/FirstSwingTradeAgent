"""
mentor_pipeline.py
===================
DREAM-08: צינור שבועי לעיבוד סרטוני מנטורים - הופך תוכן וידאו לידע
מתויג במאגר (data/watchlist.csv), בדיוק כפי שתוכנן בשיחה המקורית עם
Gemini, אבל כאן עם Claude API (עקבי עם שאר הארכיטקטורה) ולא Gemini.

חשוב: בהתאם להחלטה האחרונה (נתונים חיים בלבד ל-evaluate_trade), מה
שהצינור הזה כותב ל-CSV הוא **רק** ידע שבאמת אי אפשר לקבל בשום דרך
אחרת - רמות תמיכה/התנגדות ותבנית *כפי שהמנטור עצמו ציין אותן*, ו-
Sector/Company_Name למטא-דאטה. שדות כמו מחיר נוכחי/ימים-לדוחות
נשארים ריקים בכוונה - אלה יגיעו תמיד מהכלים החיים (fetch_market_data
וכו') כשמישהו ישאל על המניה בפועל, לא מתיוג ישן של סרטון.

**לא נבדק בפועל בסביבת הכתיבה** (אין רשת, ואין ANTHROPIC_API_KEY כאן) -
רק לוגיקת הפענוח וההמרה (JSON -> שורת CSV) נבדקה, עם נתונים מדומים.
"""

import csv
import json
import os

MENTORS = [
    {"name": "Raz_Gamliel", "video_id": "a-6kI528kuI"},  # מהדוגמה המקורית בשיחה
    {"name": "Assaf_Marciano", "video_id": None},  # TODO: להשלים קישור/video_id אמיתי
]

EXTRACTION_MODEL = "claude-sonnet-5"

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.csv")
WATCHLIST_FIELDS = [
    "Ticker", "Company_Name", "Sector", "Current_Price", "Key_Support",
    "Key_Resistance", "Days_To_Earnings", "Technical_Pattern", "Market_Cap",
    "PE_Ratio", "Source_Tag",
]


def get_transcript(video_id: str, languages: tuple = ("he", "en")) -> str | None:
    """שולף תמלול מסרטון יוטיוב. מחזיר None אם לא זמין (לא ממציא תוכן)."""
    from youtube_transcript_api import YouTubeTranscriptApi  # ייבוא מושהה

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=list(languages))
        return " ".join(item["text"] for item in transcript_list)
    except Exception:
        return None


EXTRACTION_PROMPT_TEMPLATE = """\
להלן תמלול מתוך סרטון ניתוח שוק של {mentor_name}.
חלץ מתוך התמלול את כל המניות שהוזכרו כרעיון מעקב/כניסה אפשרי.

החזר אך ורק JSON תקני - מערך של אובייקטים, כל אחד עם השדות:
- Ticker: סימול המניה (למשל NVDA, AAPL)
- Company_Name: שם החברה
- Sector: ענף (Technology, Energy, Consumer Cyclical וכו')
- Support_Key: רמת תמיכה שהוזכרה (מספר בלבד, או null אם לא הוזכרה)
- Resistance_Key: רמת התנגדות/יעד שהוזכרה (מספר בלבד, או null)
- Pattern_Technical: התבנית או הרציונל הטכני שהוזכר
- Direction: Long או Short

אל תמציא מניה או רמה שלא הוזכרה בפירוש בתמלול. אם משהו לא ברור - null.

התמלול:
{transcript}
"""


def _parse_extraction_response(raw_text: str) -> list[dict]:
    """
    מפרק את תשובת ה-JSON מ-Claude לרשימת רעיונות. מופרד מהקריאה ל-API
    כדי שאפשר לבדוק אותו בלי רשת - זה בדיוק המקום שבו תשובה לא-תקנית
    הייתה עלולה לקרוס את כל הצינור בשקט אם לא היה כאן טיפול מפורש.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        ideas = json.loads(text)
    except json.JSONDecodeError:
        return []
    return ideas if isinstance(ideas, list) else []


def extract_trading_ideas(transcript_text: str, mentor_name: str, api_key: str | None = None) -> list[dict]:
    """שולח את התמלול ל-Claude ומחזיר רשימת רעיונות מסחר מובנים (JSON)."""
    import anthropic  # ייבוא מושהה

    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(mentor_name=mentor_name, transcript=transcript_text)

    response = client.messages.create(
        model=EXTRACTION_MODEL,
        max_tokens=2000,
        temperature=0.1,  # נמוך בכוונה - זו משימת חילוץ עובדות, לא יצירה
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_extraction_response(raw_text)


def _idea_to_watchlist_row(idea: dict, mentor_name: str) -> dict:
    """
    ממפה רעיון בודד לשורת CSV, בהתאם לסכמה האחידה של watchlist.csv.
    שדות שלא ניתן לדעת מסרטון (מחיר נוכחי, ימים לדוחות) נשארים ריקים
    בכוונה - הסוכן ישלוף אותם חי כשיידרש, לא מתיוג ישן.
    """
    return {
        "Ticker": (idea.get("Ticker") or "").upper(),
        "Company_Name": idea.get("Company_Name") or "",
        "Sector": idea.get("Sector") or "",
        "Current_Price": "",
        "Key_Support": idea.get("Support_Key") if idea.get("Support_Key") is not None else "",
        "Key_Resistance": idea.get("Resistance_Key") if idea.get("Resistance_Key") is not None else "",
        "Days_To_Earnings": "",
        "Technical_Pattern": idea.get("Pattern_Technical") or "",
        "Market_Cap": "",
        "PE_Ratio": "",
        "Source_Tag": f"{mentor_name}_Mentor",
    }


def append_ideas_to_watchlist(ideas: list[dict], mentor_name: str, csv_path: str = WATCHLIST_PATH) -> int:
    """מוסיף רעיונות שחולצו לקובץ רשימת המעקב. מחזיר כמה שורות נוספו בפועל (מדלג על טיקרים ריקים)."""
    rows = [_idea_to_watchlist_row(idea, mentor_name) for idea in ideas]
    rows = [r for r in rows if r["Ticker"]]  # לא כותבים שורה בלי טיקר בכלל

    if not rows:
        return 0

    file_exists = os.path.isfile(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=WATCHLIST_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def run_pipeline_for_mentor(mentor: dict) -> dict:
    """מריץ את השרשרת המלאה עבור מנטור בודד: תמלול -> חילוץ -> עדכון קובץ."""
    if not mentor.get("video_id"):
        return {"mentor": mentor["name"], "status": "skipped", "reason": "no video_id configured"}

    transcript = get_transcript(mentor["video_id"])
    if not transcript:
        return {"mentor": mentor["name"], "status": "failed", "reason": "transcript unavailable"}

    ideas = extract_trading_ideas(transcript, mentor["name"])
    added = append_ideas_to_watchlist(ideas, mentor["name"])
    return {"mentor": mentor["name"], "status": "ok", "ideas_found": len(ideas), "rows_added": added}
