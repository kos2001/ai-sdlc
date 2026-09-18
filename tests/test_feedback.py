"""Play 4: review comments become CLAUDE.md rules and regression evals."""

import unittest

from sdlc import feedback


COMMENTS = [
    {"body": "[rule] Use the shared `retry()` helper for HTTP calls.", "path": "a.py", "line": 3, "html_url": "u1", "user": {"login": "r1"}},
    {"body": "[RULE] use the shared retry() helper for HTTP calls", "path": "b.py", "line": 9, "html_url": "u2", "user": {"login": "r2"}},
    {"body": "[rule] Prefer dataclasses", "path": "c.py", "line": 1, "html_url": "u3", "user": {"login": "r1"}},
    {"body": "[bug] Off-by-one in pagination\nmore detail", "path": "p.py", "line": 40, "html_url": "u4", "user": {"login": "r1"}},
    {"body": "[false-positive] security-reviewer flagged a test fixture as a secret", "path": "t.py", "line": 2, "html_url": "u5"},
    {"body": "looks good", "path": "x.py"},
]


class CollectTest(unittest.TestCase):
    def test_groups_by_tag_and_promotes_repeats(self):
        grouped = feedback.collect(COMMENTS)
        self.assertEqual(len(grouped["rule"]), 3)
        self.assertEqual(grouped["bug"][0]["text"], "Off-by-one in pagination")
        promote = feedback.repeated(grouped["rule"])
        self.assertEqual(len(promote), 1)
        self.assertEqual(len(promote[0][1]), 2)

    def test_report_sections(self):
        text = feedback.report(feedback.collect(COMMENTS))
        promote_section = text.split("## Regression")[0]
        self.assertIn("retry()", promote_section)
        self.assertIn("2x", promote_section)
        self.assertIn("Off-by-one in pagination", text)
        self.assertIn("Prefer dataclasses", text.split("watch list")[1])
        self.assertNotIn("looks good", text)
