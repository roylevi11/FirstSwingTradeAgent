"""
test_rules_engine.py
=====================
בדיקות אלו משחזרות במדויק את 3 מקרי הבדיקה (Test Cases) שהוגדרו בעבודה 1
ונבדקו בפועל ב-AI Studio בעבודה 2:
  1. NVDA - יחס סיכון/סיכוי 1:1.12 -> אמור להיכשל.
  2. AAPL - יחס סיכון/סיכוי 1:2.09 -> אמור לעבור.
  3. בדיקת כלל קרבה לדוחות בנפרד מכלל היחס.

הבדיקות האלה לא דורשות רשת או API key - הן בודקות רק את הלוגיקה
הדטרמיניסטית הטהורה (tools/risk.py + tools/rules_engine.py).
הרצה:  python3 -m unittest tests.test_rules_engine -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.risk import calc_risk_reward, calc_position_size
from tools.rules_engine import evaluate_hard_rules


class TestRiskRewardMath(unittest.TestCase):
    def test_nvda_case_fails_risk_reward(self):
        """עבודה 2, איטרציה 1: NVDA אמורה להיכשל ביחס סיכון/סיכוי (1:1.12)."""
        result = calc_risk_reward(entry_price=128.40, stop_loss=118.00, target_price=140.00)
        self.assertAlmostEqual(result.reward, 11.60, places=2)
        self.assertAlmostEqual(result.risk, 10.40, places=2)
        self.assertAlmostEqual(result.ratio, 1.115, places=2)
        self.assertLess(result.ratio, 2.0)

    def test_aapl_case_passes_risk_reward(self):
        """עבודה 2, איטרציה 2: AAPL אמורה לעבור ביחס סיכון/סיכוי (1:2.09)."""
        result = calc_risk_reward(entry_price=220.50, stop_loss=215.00, target_price=232.00)
        self.assertAlmostEqual(result.reward, 11.50, places=2)
        self.assertAlmostEqual(result.risk, 5.50, places=2)
        self.assertAlmostEqual(result.ratio, 2.09, places=2)
        self.assertGreaterEqual(result.ratio, 2.0)

    def test_zero_risk_raises(self):
        """מחיר כניסה זהה לסטופ-לוס הוא קלט לא חוקי - לא מחזירים תוצאה שגויה בשקט."""
        with self.assertRaises(ValueError):
            calc_risk_reward(entry_price=100, stop_loss=100, target_price=110)

    def test_position_sizing(self):
        """תיק $50,000, סיכון 1.5%, כניסה/סטופ של AAPL -> 136 מניות."""
        result = calc_position_size(account_size=50_000, risk_percent=1.5, entry_price=220.50, stop_loss=215.00)
        self.assertEqual(result["risk_amount_usd"], 750.0)
        self.assertEqual(result["shares"], 136)


class TestHardRulesEngine(unittest.TestCase):
    def test_nvda_rejected_on_risk_reward_only(self):
        """NVDA: קרבה לדוחות תקינה (76 ימים), אבל נכשלת ביחס סיכון/סיכוי."""
        verdict = evaluate_hard_rules(
            days_to_earnings=76, entry_price=128.40, stop_loss=118.00, target_price=140.00
        )
        self.assertFalse(verdict.passed)
        self.assertTrue(verdict.checks["earnings_proximity"][0])  # זה כן עבר
        self.assertFalse(verdict.checks["risk_reward"][0])  # זה מה שנכשל
        self.assertEqual(len(verdict.rejection_reasons), 1)

    def test_aapl_approved(self):
        """AAPL: גם קרבה לדוחות וגם יחס סיכון/סיכוי עוברים -> אישור מלא."""
        verdict = evaluate_hard_rules(
            days_to_earnings=28, entry_price=220.50, stop_loss=215.00, target_price=232.00
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.rejection_reasons, [])

    def test_rejected_on_earnings_proximity(self):
        """מניה עם R:R מעולה אך רק יום אחד לדוחות - עדיין נדחית (בדיקת כלל בודד)."""
        verdict = evaluate_hard_rules(
            days_to_earnings=1, entry_price=100, stop_loss=95, target_price=120
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(verdict.checks["earnings_proximity"][0])
        self.assertTrue(verdict.checks["risk_reward"][0])  # ה-R:R כן טוב (4.0)

    def test_rejected_on_both_rules(self):
        """מניה שנכשלת בשני הכללים בו-זמנית -> שתי סיבות דחייה מדווחות."""
        verdict = evaluate_hard_rules(
            days_to_earnings=0, entry_price=100, stop_loss=95, target_price=102
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(len(verdict.rejection_reasons), 2)

    def test_position_risk_check_when_provided(self):
        """אם מעבירים risk_percent_of_account שחורג מהמותר - נכשל גם אם שאר הכללים תקינים."""
        verdict = evaluate_hard_rules(
            days_to_earnings=28,
            entry_price=220.50,
            stop_loss=215.00,
            target_price=232.00,
            risk_percent_of_account=3.0,  # חורג מ-MAX_RISK_PERCENT_PER_TRADE (1.5)
        )
        self.assertFalse(verdict.passed)
        self.assertIn("position_risk", verdict.checks)


if __name__ == "__main__":
    unittest.main(verbosity=2)
