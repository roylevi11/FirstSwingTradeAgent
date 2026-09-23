"""
sec_filings.py
===============
מענה לבקשה "ניתוח מידע בשפה פשוטה מ-BamSEC" - אבל **לא** דרך BamSEC
עצמו. בדקתי: BamSEC הוא מוצר בתשלום (כ-$69+/חודש) עם התחברות, מיועד
לצוותי מחקר מוסדיים. אין לנו הרשאה לגשת אליו, ואין להם API ציבורי.

**הפתרון הנכון:** SEC EDGAR - המקור הרשמי, החינמי ופתוח-לציבור-לגמרי
(מפורש: "public-domain data, explicitly published for reuse") שעליו
BamSEC עצמו מבוסס מלכתחילה. אנחנו שולפים את הדוחות האמיתיים ישירות
מהמקור, וה"ניתוח בשפה פשוטה" הוא בדיוק מה שהסוכן שלנו (Claude) כבר
טוב בו - לא צריך שירות חיצוני נוסף בשביל זה.

חוקי גישה הוגנת של SEC (חובה, לא אופציונלי): כל בקשה חייבת User-Agent
עם שם ואימייל מזהים, אחרת חוסמים עם 403. **יש להחליף את SEC_USER_AGENT
למטה בפרטים האמיתיים שלך לפני הרצה.**

**לא נבדק בפועל בסביבת הכתיבה** (אין רשת) - רק בנוי לפי תיעוד EDGAR
הרשמי שנבדק דרך חיפוש.
"""

# TODO: החלף בפרטים האמיתיים שלך - SEC חוסם בקשות בלי User-Agent תקין
SEC_USER_AGENT = "SwingCopilot research-project (your-email@example.com)"

RELEVANT_FORMS = ("10-K", "10-Q", "8-K")


def _get_cik_for_ticker(ticker: str) -> str | None:
    """ממפה טיקר ל-CIK (מזהה החברה ב-SEC) דרך קובץ המיפוי הרשמי."""
    import requests

    resp = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers={"User-Agent": SEC_USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    for entry in resp.json().values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None


def fetch_recent_filings(ticker: str, form_types: tuple = RELEVANT_FORMS, limit: int = 5) -> list[dict]:
    """
    שולף את הדוחות האחרונים (10-K/10-Q/8-K כברירת מחדל) של חברה.
    מחזיר מטא-דאטה וקישור למסמך המקורי - לא את הטקסט המלא (דוחות 10-K
    יכולים להגיע למגה-בייטים בודדים; שליפת הטקסט המלא לצורך סיכום היא
    הרחבה עתידית נפרדת, לא כלולה כאן במכוון).
    """
    import requests

    cik = _get_cik_for_ticker(ticker)
    if cik is None:
        return []

    resp = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers={"User-Agent": SEC_USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})

    cik_no_padding = str(int(cik))
    results = []
    for i in range(len(recent.get("form", []))):
        if recent["form"][i] not in form_types:
            continue
        accession_nodash = recent["accessionNumber"][i].replace("-", "")
        results.append({
            "form": recent["form"][i],
            "filing_date": recent["filingDate"][i],
            "report_date": recent.get("reportDate", [None] * len(recent["form"]))[i],
            "accession_number": recent["accessionNumber"][i],
            "document_url": (
                f"https://www.sec.gov/Archives/edgar/data/{cik_no_padding}/"
                f"{accession_nodash}/{recent['primaryDocument'][i]}"
            ),
        })
        if len(results) >= limit:
            break
    return results
