"""Regression: a manual label without readable source text is not evidence."""
import unittest
from realitycheck.core import render_report


def case(text):
    return {
        "listing_id": "synthetic",
        "as_of": "2026-11-26",
        "question": "Is it quiet?",
        "topics": ["night_noise"],
        "sources": [{
            "id": "empty-source", "source_type": "review", "date": "2026-11-25",
            "text": text,
            "assertions": [{"topic": "night_noise", "stance": "supports"}],
        }],
    }


class MissingSourceTests(unittest.TestCase):
    def test_blank_text_is_visible_but_not_counted(self):
        for text in ("", "   \n", "\u200e\u202e"):
            with self.subTest(text=repr(text)):
                report = render_report(case(text))
                self.assertIn("**Status:** INSUFFICIENT EVIDENCE", report)
                self.assertIn("empty-source", report)
                self.assertIn("missing or unreadable — annotations not used in status", report)
                self.assertNotIn("**Status:** REPORTED SUPPORT", report)

    def test_readable_manual_text_is_still_unverified_support(self):
        report = render_report(case("Fictional account: quiet on one night."))
        self.assertIn("**Status:** REPORTED SUPPORT — NOT VERIFIED", report)
        self.assertIn("empty-source", report)


if __name__ == "__main__":
    unittest.main()
