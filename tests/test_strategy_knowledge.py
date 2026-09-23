"""
test_strategy_knowledge.py
============================
בודק את מבנה LESSON_REGISTRY ואת build_knowledge_markdown - לא קורא
תמלול או Claude API אמיתיים.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.strategy_knowledge import LESSON_REGISTRY, LessonResult, build_knowledge_markdown


class TestLessonRegistry(unittest.TestCase):
    def test_thirty_lessons_registered(self):
        self.assertEqual(len(LESSON_REGISTRY), 30)

    def test_all_lessons_have_title_and_video_id(self):
        for lesson in LESSON_REGISTRY:
            self.assertTrue(lesson["title"])
            self.assertTrue(lesson["video_id"])
            self.assertNotIn(" ", lesson["video_id"])  # video_id לא אמור להכיל רווחים

    def test_no_duplicate_video_ids(self):
        ids = [lesson["video_id"] for lesson in LESSON_REGISTRY]
        self.assertEqual(len(ids), len(set(ids)))


class TestBuildKnowledgeMarkdown(unittest.TestCase):
    def test_successful_lesson_includes_summary(self):
        results = [LessonResult("שיעור 1", "abc123", "ok", "כלל חשוב: תמיד לחכות לאישור נפח.")]
        md = build_knowledge_markdown(results)
        self.assertIn("שיעור 1", md)
        self.assertIn("תמיד לחכות לאישור נפח", md)

    def test_unavailable_transcript_noted_not_hidden(self):
        results = [LessonResult("שיעור 2", "xyz789", "transcript_unavailable")]
        md = build_knowledge_markdown(results)
        self.assertIn("שיעור 2", md)
        self.assertIn("לא זמין", md)

    def test_status_summary_counts_correctly(self):
        results = [
            LessonResult("A", "1", "ok", "..."),
            LessonResult("B", "2", "ok", "..."),
            LessonResult("C", "3", "transcript_unavailable"),
        ]
        md = build_knowledge_markdown(results)
        self.assertIn("2/3", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
