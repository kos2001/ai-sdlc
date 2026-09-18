"""Play 6 (plan before code) and Play 8 (evals are never silently weakened)."""

from sdlc import gates, workitems
from tests.helpers import RepoTestCase, git


class PlanGateTest(RepoTestCase):
    def accepted_plan(self):
        intent = workitems.new_work(self.root, "Cache", self.human, "T1", year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        workitems.submit(spec, self.root)
        workitems.approve(spec, self.root, self.human, "architect")
        plan = workitems.add_stage(self.root, intent.parent, "plan")
        self.fill_plan(plan)
        workitems.submit(plan, self.root)
        return plan

    def test_docs_only_change_needs_no_plan(self):
        git(self.root, "checkout", "-q", "-b", "docs")
        self.write("docs/guide.md", "hi\n")
        self.commit("docs")
        self.assertTrue(gates.plan_gate(self.root, "main").ok)

    def test_code_without_work_item_fails(self):
        git(self.root, "checkout", "-q", "-b", "feature/cache")
        self.write("src/cache.py", "x = 1\n")
        self.commit("code")
        result = gates.plan_gate(self.root, "main", refs="feature/cache")
        self.assertFalse(result.ok)
        self.assertIn("without a work item", result.messages[0])

    def test_code_needs_plan_accepted_not_just_proposed(self):
        plan = self.accepted_plan()
        self.commit("plan proposed")
        git(self.root, "checkout", "-q", "-b", "feature/w-0001-cache")
        self.write("src/cache.py", "x = 1\n")
        self.commit("code")
        result = gates.plan_gate(self.root, "main", refs="feature/w-0001-cache")
        self.assertFalse(result.ok)
        self.assertIn("needs accepted", result.messages[0])

        workitems.approve(plan, self.root, self.human, "tech-lead")
        self.commit("plan accepted")
        self.assertTrue(gates.plan_gate(self.root, "main", refs="feature/w-0001-cache").ok)

    def test_uncommitted_approval_does_not_count(self):
        plan = self.accepted_plan()
        self.commit("plan proposed")
        git(self.root, "checkout", "-q", "-b", "feature/w-0001-cache")
        self.write("src/cache.py", "x = 1\n")
        self.commit("code")
        workitems.approve(plan, self.root, self.human, "tech-lead")  # working tree only
        self.assertFalse(gates.plan_gate(self.root, "main", refs="W-0001").ok)


class EvalGuardTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.write("tests/test_cart.py",
                   "import unittest\n\n\nclass CartTest(unittest.TestCase):\n"
                   "    def test_total(self):  # W-0001:AC-1\n        self.assertEqual(1, 1)\n\n"
                   "    def test_empty(self):\n        self.assertEqual(0, 0)\n")
        self.commit("tests")
        git(self.root, "checkout", "-q", "-b", "change")

    def guard(self):
        self.commit("change")
        return gates.eval_guard(self.root, "main")

    def test_adding_tests_is_fine(self):
        path = self.root / "tests/test_cart.py"
        path.write_text(path.read_text() + "\n    def test_more(self):\n        pass\n")
        self.assertTrue(self.guard().ok)

    def test_removed_test_is_flagged(self):
        path = self.root / "tests/test_cart.py"
        path.write_text(path.read_text().replace("    def test_empty(self):\n        self.assertEqual(0, 0)\n", ""))
        result = self.guard()
        self.assertFalse(result.ok)
        self.assertTrue(any("removed test definition" in m for m in result.messages))

    def test_skip_marker_is_flagged(self):
        path = self.root / "tests/test_cart.py"
        path.write_text(path.read_text().replace("    def test_empty", "    @unittest.skip('flaky')\n    def test_empty"))
        self.assertTrue(any("skip" in m for m in self.guard().messages))

    def test_removed_ac_tag_is_flagged(self):
        path = self.root / "tests/test_cart.py"
        path.write_text(path.read_text().replace("  # W-0001:AC-1", ""))
        self.assertTrue(any("W-0001:AC-1" in m for m in self.guard().messages))

    def test_deleted_file_is_flagged(self):
        (self.root / "tests/test_cart.py").unlink()
        self.assertTrue(any("deleted" in m for m in self.guard().messages))
