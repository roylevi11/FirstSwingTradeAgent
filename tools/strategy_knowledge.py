"""
strategy_knowledge.py
======================
שונה במהותו מ-tools/mentor_pipeline.py: זה לא צינור *שבועי* שמחפש
טיקרים עדכניים בסרטון חדש. זה חילוץ **חד-פעמי** (או מתי שתרצה לעדכן
ידנית) של מתודולוגיה/אסטרטגיה כללית מתוך קורס קיים - התוצר הוא קובץ
ידע (data/knowledge/*.md) שהסוכן יכול "לצטט" ממנו כהקשר תומך, לא
מקור אמת למספרים. חוקי הברזל (evaluate_trade) נשארים הסמכות הבלעדית
להחלטה - הידע הזה הוא הקשר איכותני בלבד ("למה מנטור X חושב ככה"),
בדיוק כמו ששכבת ה-Knowledge מוגדרת בארכיטקטורת 5 הרכיבים.

הערת רגישות תוכן: זהו קורס בתשלום. הפרומפט כאן מכוון בכוונה לחילוץ
**עקרונות מתומצתים**, לא תמלול/ציטוט מילולי - גם כי זה הערך שרצוי
(ידע מעובד, לא גיבוי גולמי), וגם כי זה שימוש אישי הוגן בתוכן שרכשת,
לא שכפול/הפצה שלו.

**לא נבדק בפועל** (אין רשת/מפתח כאן) - רק מבנה הרישום ובניית הקובץ
המאוחד נבדקו.
"""

import os
from dataclasses import dataclass

# 30 השיעורים שנשלחו - רק הכתובות הציבוריות, לא קישור הקהילה הפרטי
LESSON_REGISTRY = [
    {"title": "הקדמה ושאלות נפוצות", "video_id": "hvUWUwxH67s"},
    {"title": "שיעור 1", "video_id": "F7WuvgtepRA"},
    {"title": "שיעור 2", "video_id": "whGHOV3oMqo"},
    {"title": "שיעור 3", "video_id": "jvpRWHQ8ohk"},
    {"title": "שיעור 4", "video_id": "fp6iGytktHU"},
    {"title": "שיעור 5", "video_id": "ruNgPhJid_0"},
    {"title": "שיעור 6", "video_id": "GxeKCobmKro"},
    {"title": "שיעור 7", "video_id": "E3djq8ffHV8"},
    {"title": "שיעור 8", "video_id": "CWDGPCjMYjg"},
    {"title": "שיעור 9", "video_id": "cCZ9c9W2U9U"},
    {"title": "שיעור 10", "video_id": "vfrHSPtgEDc"},
    {"title": "שיעור 11", "video_id": "nNJ1_Eq3htQ"},
    {"title": "שיעור 12", "video_id": "PQi-i_W4Wqs"},
    {"title": "שיעור 13", "video_id": "LmUXMno_tg8"},
    {"title": "שיעור 14", "video_id": "_6eeNEtVqR4"},
    {"title": "שיעור 15", "video_id": "I4n-tm2mJyo"},
    {"title": "שיעור 16", "video_id": "VVSO4akePwg"},
    {"title": "עסקאות אישיות חלק 1", "video_id": "80UAVlwxti4"},
    {"title": "עסקאות אישיות חלק 2", "video_id": "kXyyL-jLyUY"},
    {"title": "עסקאות אישיות חלק 3", "video_id": "oqEUD501tMA"},
    {"title": "עסקאות אישיות חלק 4", "video_id": "7e2mb4WFCr4"},
    {"title": "עסקאות אישיות חלק 5", "video_id": "6-VPUa2GCok"},
    {"title": "סוד מסחר - חדשות", "video_id": "0zsHRkkx0Fs"},
    {"title": "סוד מסחר - הסווינגים", "video_id": "yJM8KZmjdJs"},
    {"title": "מחזוריות הרגש בשוק", "video_id": "G1vVS9PppOE"},
    {"title": "מנטליות מברזל חלק 1", "video_id": "YUlTSHJOguI"},
    {"title": "מנטליות מברזל חלק 2", "video_id": "Vdr3an7zlO4"},
    {"title": "מנטליות מברזל חלק 3", "video_id": "gVjwrIUOOcs"},
    {"title": "מנטליות מברזל חלק 4", "video_id": "vRIxtEIxtBc"},
    {"title": "מנטליות מברזל חלק 5", "video_id": "LMzo-OIMt2U"},
]

MENTOR_NAME = "Assaf_Marciano"
KNOWLEDGE_MODEL = "claude-sonnet-5"
KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge", "assaf_marciano_methodology.md")

DISTILLATION_PROMPT_TEMPLATE = """\
להלן תמלול של שיעור מסחר בשם "{title}" מתוך קורס של {mentor_name}.

חלץ ממנו **תמצית עקרונות מתודולוגיים** - לא תמלול, לא ציטוט מילולי,
אלא סיכום מנוסח מחדש במילים שלך:
- כללי ניהול סיכונים או מנטליות שהוזכרו
- קריטריונים לבחירת עסקה (אם הוזכרו)
- טעויות נפוצות שהוזהר מפניהן
- כל עיקרון אחר שחוזר ומודגש

כתוב עד 200 מילים, בעברית, כרשימת נקודות תמציתית. אם השיעור לא מכיל
עקרונות מתודולוגיים ברורים (למשל שיעור טכני-בלבד), כתוב זאת במפורש.

התמלול:
{transcript}
"""


@dataclass
class LessonResult:
    title: str
    video_id: str
    status: str  # "ok" | "transcript_unavailable" | "skipped"
    summary: str | None = None


def distill_lesson(lesson: dict, api_key: str | None = None) -> LessonResult:
    """מריץ שרשור תמלול->סיכום עקרונות עבור שיעור בודד."""
    from tools.mentor_pipeline import get_transcript  # שימוש חוזר בפונקציה הקיימת

    transcript = get_transcript(lesson["video_id"])
    if not transcript:
        return LessonResult(lesson["title"], lesson["video_id"], "transcript_unavailable")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key or None)
    prompt = DISTILLATION_PROMPT_TEMPLATE.format(
        title=lesson["title"], mentor_name=MENTOR_NAME, transcript=transcript
    )
    response = client.messages.create(
        model=KNOWLEDGE_MODEL,
        max_tokens=500,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    summary = "".join(block.text for block in response.content if block.type == "text")
    return LessonResult(lesson["title"], lesson["video_id"], "ok", summary)


def build_knowledge_markdown(results: list[LessonResult]) -> str:
    """
    מאחד את כל תוצאות השיעורים לקובץ ידע אחד. מופרד מהריצה בפועל כדי
    שאפשר לבדוק את הפורמט בלי רשת - עם LessonResult מדומים.
    """
    lines = [
        f"# מתודולוגיית מסחר - {MENTOR_NAME}",
        "",
        "*קובץ ידע מתומצת, לא תמלול מלא - נועד כהקשר תומך לסוכן, לא כמקור אמת למספרים.*",
        "",
    ]
    ok_count = sum(1 for r in results if r.status == "ok")
    lines.append(f"**סטטוס:** {ok_count}/{len(results)} שיעורים עובדו בהצלחה.")
    lines.append("")

    for r in results:
        lines.append(f"## {r.title}")
        if r.status == "ok":
            lines.append(r.summary or "")
        elif r.status == "transcript_unavailable":
            lines.append("*(תמלול לא זמין לשיעור זה - דולג)*")
        else:
            lines.append("*(דולג)*")
        lines.append("")

    return "\n".join(lines)


def run_full_distillation(api_key: str | None = None) -> str:
    """מריץ על כל LESSON_REGISTRY, שומר את הקובץ המאוחד, ומחזיר את הנתיב."""
    results = [distill_lesson(lesson, api_key) for lesson in LESSON_REGISTRY]
    markdown = build_knowledge_markdown(results)

    os.makedirs(os.path.dirname(KNOWLEDGE_PATH), exist_ok=True)
    with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        f.write(markdown)

    failed = [r.title for r in results if r.status != "ok"]
    if failed:
        print(f"אזהרה: {len(failed)} שיעורים לא עובדו: {failed}")
    return KNOWLEDGE_PATH


def fetch_strategy_notes() -> str:
    """קורא את קובץ הידע הקיים (אם כבר הורץ run_full_distillation). לשימוש הסוכן."""
    if not os.path.isfile(KNOWLEDGE_PATH):
        return "אין עדיין קובץ ידע מתודולוגי - יש להריץ תחילה את distill_strategy_knowledge.py."
    with open(KNOWLEDGE_PATH, encoding="utf-8") as f:
        return f.read()
