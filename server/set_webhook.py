"""
set_webhook.py
===============
מריצים פעם אחת, אחרי שהשרת עלה ל-Render וקיבל כתובת ציבורית:
    python server/set_webhook.py https://YOUR-APP.onrender.com

זה מודיע לטלגרם "תשלח עדכונים (הודעות, לחיצות כפתור) לכתובת הזאת"
במקום שהבוט יצטרך לבדוק (polling) - יעיל יותר לשרת שרץ ברציפות.
"""

import os
import sys
import requests

from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if len(sys.argv) < 2:
    print("שימוש: python server/set_webhook.py https://YOUR-APP.onrender.com")
    sys.exit(1)

base_url = sys.argv[1].rstrip("/")
webhook_url = f"{base_url}/webhook"

resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook", params={"url": webhook_url})
print(resp.json())

# בדיקה שזה באמת נרשם
check = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
print(check.json())
