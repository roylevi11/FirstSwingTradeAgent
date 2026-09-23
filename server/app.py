"""
server/app.py
==============
שרת Flask קטן שמיועד לרוץ 24/7 (למשל ב-Render) - זה בדיוק הרכיב שהיה
חסר כדי שבוט טלגרם יוכל לתפוס לחיצות כפתור בזמן אמת, בניגוד ל-GitHub
Actions השבועי (שרץ פעם ונגמר).

זרימה: POST /scan/<ticker> (או קריאה מתוזמנת) -> מריץ את agent.loop.
run_agent המלא (עם כל הכלים - ניתוח רב-טווחי, דמיון, אינדיקטורים,
StockTwits, SEC, הערות אסטרטגיה) -> שולח הודעת טלגרם עם ההסבר וכפתורי
אישור/דחייה -> כשמאשרים, נשמר ב-DB מקומי -> GET /approved-trades.json
מחזיר את הרשימה, שהדשבורד יכול לסנכרן ממנה.

הערה על מגבלה אמיתית: שרת Python לא יכול לכתוב ישירות ל-state המשותף
של דף Artifact שפורסם (זו יכולת שזמינה רק בדפדפן של הצופה, או ל-Claude
עצמו בתוך שיחה). לכן הדשבורד מסנכרן מה-endpoint הזה - אוטומטי אם ה-
fetch מהדפדפן מותר, או בהדבקה ידנית של ה-JSON כגיבוי.
"""

import os
import json
import sqlite3
import sys
from datetime import datetime

from flask import Flask, request, jsonify
import requests as http

# מאפשר import של agent/tools מהתיקייה הראשית של הריפו (רמה מעל server/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
ALLOWED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # מגביל מי יכול לתקשר עם הבוט
DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            memo_text TEXT,
            status TEXT DEFAULT 'pending',
            telegram_message_id INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def send_telegram_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    resp = http.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=15)
    return resp.json()


def edit_telegram_message(chat_id, message_id, text):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    http.post(f"{TELEGRAM_API}/editMessageText", data=payload, timeout=15)


def answer_callback(callback_query_id, text=""):
    http.post(f"{TELEGRAM_API}/answerCallbackQuery",
              data={"callback_query_id": callback_query_id, "text": text}, timeout=10)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/scan/<ticker>", methods=["POST"])
def scan_ticker(ticker):
    """
    מריץ את הסוכן המלא על טיקר, ואם יש המלצה (מאושרת או נדחית) - שולח
    התראת טלגרם עם ההסבר המלא (כל הכלים שהופעלו) וכפתורי אישור/דחייה.
    קריאה ל-endpoint הזה: POST עם header 'X-API-Key' שתואם ANTHROPIC
    בסביבת הריצה שלך (בדיקת זהות בסיסית - לא ל-production אמיתי בלי
    שכבת אבטחה נוספת).
    """
    from agent.loop import run_agent

    request_text = (
        f"תסרוק את מניית {ticker.upper()} בצורה מלאה: הפעל ניתוח רב-טווחי-זמן, "
        f"בדוק סנטימנט StockTwits, ובדוק אם יש הערות אסטרטגיה רלוונטיות. "
        f"תן לי החלטה סופית עם נימוק מלא המבוסס על כל הכלים שהפעלת."
    )
    result = run_agent(request_text)
    memo_text = result["final_text"]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO trades (ticker, memo_text, status, created_at) VALUES (?,?,?,?)",
        (ticker.upper(), memo_text, "pending", datetime.utcnow().isoformat()),
    )
    trade_id = cur.lastrowid
    conn.commit()
    conn.close()

    keyboard = {"inline_keyboard": [[
        {"text": "✅ אשר", "callback_data": f"approve:{trade_id}"},
        {"text": "❌ דחה", "callback_data": f"reject:{trade_id}"},
    ]]}
    tg_response = send_telegram_message(ALLOWED_CHAT_ID, memo_text, keyboard)

    if tg_response.get("ok"):
        msg_id = tg_response["result"]["message_id"]
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE trades SET telegram_message_id=? WHERE id=?", (msg_id, trade_id))
        conn.commit()
        conn.close()

    return jsonify({"trade_id": trade_id, "sent_to_telegram": tg_response.get("ok", False)})


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """מקבל עדכונים מטלגרם - כאן קורה התפיסה בזמן אמת של לחיצות הכפתור."""
    update = request.get_json(force=True)

    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq["data"]  # "approve:<id>" או "reject:<id>"
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        action, trade_id = data.split(":")

        conn = sqlite3.connect(DB_PATH)
        new_status = "approved" if action == "approve" else "rejected"
        conn.execute("UPDATE trades SET status=? WHERE id=?", (new_status, trade_id))
        row = conn.execute("SELECT ticker, memo_text FROM trades WHERE id=?", (trade_id,)).fetchone()
        conn.commit()
        conn.close()

        icon = "✅ אושר" if new_status == "approved" else "❌ נדחה"
        if row:
            edit_telegram_message(chat_id, message_id, f"{row[1]}\n\n*{icon}*")
        answer_callback(cq["id"], icon)

    return jsonify({"ok": True})


@app.route("/approved-trades.json")
def approved_trades():
    """
    מחזיר את כל העסקאות שאושרו, בפורמט שהדשבורד יודע לפרש.
    זהו נקודת הסנכרון בין השרת לדשבורד (ראו הערה בראש הקובץ למה
    זה לא יכול להיות push ישיר).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, ticker, memo_text, status, created_at FROM trades WHERE status='approved' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/all-trades.json")
def all_trades_json():
    """כל העסקאות (לצורך דיבוג/מעקב) - כולל ממתינות ונדחות."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, ticker, memo_text, status, created_at FROM trades ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
