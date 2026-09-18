"""The self-improvement loop: lessons close only with a control, and a regressed control fails the check."""

import tempfile
import unittest
from pathlib import Path

from sdlc import cli, lessons


class LessonsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "tests").mkdir()
        (self.root / "tests/test_x.py").write_text("def test_guard():\n    pass\n")
        (self.root / "CLAUDE.md").write_text("# Rules\n")

    def tearDown(self):
        self._tmp.cleanup()

    def add(self, **kw):
        base = dict(title="t", detected_by="human", what_happened="w", root_cause="c", gate_existed=False)
        base.update(kw)
        return lessons.add(self.root, **base)

    def test_ids_are_sequential_and_new_lessons_open(self):
        self.assertEqual(self.add()["id"], "L-001")
        second = self.add()
        self.assertEqual((second["id"], second["status"]), ("L-002", "open"))

    def test_close_requires_a_control_that_exists(self):  # W-0001:AC-1
        self.add()
        with self.assertRaisesRegex(lessons.LessonError, "does not exist"):
            lessons.close(self.root, "L-001", "test", "tests/missing.py::test_guard")
        with self.assertRaisesRegex(lessons.LessonError, "no longer contains"):
            lessons.close(self.root, "L-001", "test", "tests/test_x.py::test_other")
        closed = lessons.close(self.root, "L-001", "test", "tests/test_x.py::test_guard")
        self.assertEqual(closed["status"], "closed")

    def test_rule_control_is_written_into_claude_md(self):  # W-0001:AC-2
        self.add()
        lessons.close(self.root, "L-001", "rule", rule="Re-measure over the full dataset before claiming a pattern.")
        text = (self.root / "CLAUDE.md").read_text()
        self.assertIn(lessons.RULES_START, text)
        self.assertIn("- Re-measure over the full dataset before claiming a pattern. (L-001)", text)
        self.assertEqual(lessons.check(self.root)[0], [])

    def test_check_fails_when_a_control_regresses(self):  # W-0001:AC-3
        self.add(title="guard against X")
        lessons.close(self.root, "L-001", "test", "tests/test_x.py::test_guard")
        self.assertEqual(lessons.check(self.root)[0], [])
        (self.root / "tests/test_x.py").write_text("def test_something_else():\n    pass\n")
        errors, _ = lessons.check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("control regressed", errors[0])
        self.assertEqual(cli.main(["--root", str(self.root), "lessons", "check"]), 1)

    def test_check_rejects_malformed_and_warns_on_stale(self):
        self.add(detected_at="2000-01-01")
        errors, warnings = lessons.check(self.root)
        self.assertEqual(errors, [])
        self.assertTrue(warnings and "open for" in warnings[0])
        ledger = lessons.load(self.root)
        ledger.append({"id": "L-001", "title": "dup"})
        lessons.save(self.root, ledger)
        self.assertTrue(any("missing" in e for e in lessons.check(self.root)[0]))

    def test_status_measures_prevention_and_controls(self):  # W-0001:AC-4
        self.add(gate_existed=True, detected_by="gate")
        self.add()
        lessons.close(self.root, "L-001", "test", "tests/test_x.py::test_guard")
        st = lessons.status(self.root)
        self.assertEqual((st["total"], st["open"], st["closed"]), (2, 1, 1))
        self.assertEqual(st["prevention_rate"], 0.5)
        self.assertEqual(st["controls"], {"test": 1})
        self.assertEqual(st["controls_holding"], 1)
        self.assertEqual(st["detected_by"], {"gate": 1, "human": 1})


if __name__ == "__main__":
    unittest.main()
