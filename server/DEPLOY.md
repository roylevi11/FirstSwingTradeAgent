# פריסת בוט הטלגרם ל-Render — מדריך שלב-אחר-שלב

## שלב 1: יצירת הבוט בטלגרם
1. פתחי/פתח שיחה עם [@BotFather](https://t.me/BotFather) בטלגרם.
2. שלחי/שלח `/newbot`, תני/תן שם ו-username (חייב להסתיים ב-`bot`).
3. תקבלי/תקבל **טוקן** — שמרי/שמור אותו, זה `TELEGRAM_BOT_TOKEN`.
4. שלחי/שלח הודעה כלשהי לבוט החדש שלך (כדי שיהיה chat פעיל).
5. כדי לגלות את ה-`TELEGRAM_CHAT_ID` שלך: שלחי/שלח הודעה לבוט, ואז גשי/גש ל-
   `https://api.telegram.org/bot<TOKEN>/getUpdates` בדפדפן — תראי/תראה `"chat":{"id": ...}`.

## שלב 2: יצירת חשבון Render
1. הירשמי/הירשם בחינם ב-[render.com](https://render.com) (אפשר עם GitHub).
2. **New** → **Web Service** → חברי/חבר את ה-repository `FirstSwingTradeAgent`.
3. Render יזהה את `render.yaml` אוטומטית ויציע את ההגדרות הנכונות.
   אם לא — הגדירי/הגדר ידנית:
   - **Build Command:** `pip install -r server/requirements.txt`
   - **Start Command:** `cd server && gunicorn app:app`
4. תחת **Environment**, הוסיפי/הוסף את שלושת המשתנים:
   - `ANTHROPIC_API_KEY` — המפתח שלך
   - `TELEGRAM_BOT_TOKEN` — מ-BotFather
   - `TELEGRAM_CHAT_ID` — מה-getUpdates
5. **Create Web Service**. הפריסה הראשונה לוקחת כמה דקות.

## שלב 3: רישום ה-Webhook
אחרי שהשירות עלה, יהיה לך URL כמו `https://swing-copilot-bot.onrender.com`.
הריצי/הרץ מקומית (עם `.env` מוגדר עם אותו טוקן):
```bash
python server/set_webhook.py https://swing-copilot-bot.onrender.com
```
תוצאה מצופה: `{"ok": true, "result": true, ...}`.

## שלב 4: בדיקה
```bash
curl -X POST https://swing-copilot-bot.onrender.com/scan/NVDA
```
אמורה להגיע הודעה בטלגרם עם ניתוח מלא וכפתורי ✅/❌.

## הערות חשובות (לא באגים, מגבלות ידועות)

- **השכבה החינמית של Render "נרדמת"** אחרי כ-15 דקות ללא בקשות, ומתעוררת עם עיכוב של כמה שניות בבקשה הבאה. תקין ל-MVP אישי, לא לשימוש production רציני.
- **הדיסק החינמי הוא ephemeral** — `trades.db` מתאפס בכל דיפלוי מחדש (עדכון קוד). לשמירה קבועה: שדרוג ל-Render Persistent Disk, או מעבר ל-DB חיצוני (Postgres חינמי גם קיים ב-Render).
- **הדשבורד לא מתעדכן "בעצמו" ברקע** — צריך ללחוץ "סנכרן" בטאב "התראות מהבוט". זו מגבלה אמיתית: לדף שפורסם אין דרך לקבל push מתהליך Python חיצוני; הפתרון המעשי הוא סנכרון ביוזמת המשתמש.
- **אין עדיין תזמון אוטומטי לסריקות** — `/scan/<ticker>` צריך להיקרא (ידנית, או דרך cron חיצוני כמו [cron-job.org](https://cron-job.org) שקורא ל-endpoint בזמנים קבועים). זה לא נבנה כרגע כי לא סוכם על אילו מניות/מתי לסרוק אוטומטית.
