# FirstSwingTradeAgent — כללי עבודה עם Claude

## Git
- אחרי כל שינוי, לשאול את המשתמש לפני commit / push, ולחכות לאישור.
- בקשה מפורשת ("תדחוף לגיט") מאשרת רק את העדכון הספציפי הזה.
- Remote: `https://github.com/roylevi11/FirstSwingTradeAgent.git`, ענף `main`.

## Claude API
- בשלב זה לא מריצים שום דבר שקורא ל-Claude API (`main.py`, `python -m eval.run_evaluation`, `run_agent`), אלא אם המשתמש ביקש במפורש.
- אימות שינויים: `python -m unittest discover -s tests` וקריאות ישירות לכלים הדטרמיניסטיים ולמקורות החינמיים.
- `eval/evaluation_report.md` ישן (לפני המעבר לניתוח רב-טווחי); לא להריץ מחדש בלי בקשה.

## מחירים ונתונים
- מחיר תמיד חי (`tools/market_data.fetch_live_price`); המחיר ב-`data/watchlist.csv` לא נקרא.
- תמיכה/התנגדות/תבנית לעסקה: `analyze_multi_timeframe` (חי). הרמות ב-CSV הן הפניה היסטורית בלבד.
- העדפה למקורות חינמיים ללא מפתח: Finviz, StockTwits, SEC EDGAR.
- לא משתמשים: Market Momentum Radar (robots.txt אוסר `/api/`, `/v2/`) ו-TradingView scanner (robots.txt אוסר הכול חוץ מ-`/global/scan`). לכבד robots.txt בכל מקור חדש.
- שכבת הדמיון (`find_similar_stocks`) פועלת על נתונים חיים בלבד (`tools/live_similarity.py`): מאפיינים ממספר טווחי זמן, קורלציה היסטורית, ו-Edge היסטורי לתבניות (`tools/pattern_stats.py`, נבדק על S&P500+NASDAQ; לחדש עם `python -m tools.pattern_stats`, ~4 דקות). מה-CSV נלקחת רק זהות המניה. "אין תבנית" (None) הוא ערך לגיטימי.
- נתון חסר מדווח כחסר, לעולם לא מומצא.

## חוקי ברזל (config/rules_config.py)
- קרבה לדוחות: לפחות יום מסחר אחד. יחס סיכון/סיכוי מינימלי 1:2. סיכון מקסימלי לעסקה 1.5%.
- `evaluate_trade` הוא פסק דין סופי; אין לעקוף.
