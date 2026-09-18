"""Risk tiers route review depth (Play 10) and release gates (Play 11)."""

from sdlc import risk, workitems
from tests.helpers import RepoTestCase, git


class RiskTest(RepoTestCase):
    def tier(self, *paths):
        return risk.assess(self.root, list(paths))["tier"]

    def test_path_rules(self):
        self.assertEqual(self.tier("docs/guide.md"), "T0")
        self.assertEqual(self.tier("README.md"), "T0")
        self.assertEqual(self.tier("src/checkout/cart.py"), "T1")
        self.assertEqual(self.tier("db/migrations/0042_add.sql"), "T2")
        self.assertEqual(self.tier("services/web/package.json"), "T2")
        self.assertEqual(self.tier("services/CLAUDE.md"), "T2")
        self.assertEqual(self.tier("services/auth/token.py"), "T3")
        self.assertEqual(self.tier("infra/main.tf"), "T3")
        self.assertEqual(self.tier(".github/workflows/ci.yml"), "T3")

    def test_highest_tier_wins(self):
        result = risk.assess(self.root, ["docs/a.md", "src/x.py", "services/payments/charge.py"])
        self.assertEqual(result["tier"], "T3")
        self.assertEqual(result["human_reviews"], 2)
        self.assertEqual(result["release"], "human-approved")

    def test_declared_tier_of_touched_work_item_and_floor(self):
        intent = workitems.new_work(self.root, "Payments", self.human, "T3", year=2026)
        rel = intent.relative_to(self.root).as_posix()
        self.assertEqual(self.tier(rel, "src/x.py"), "T3")
        self.assertEqual(risk.assess(self.root, ["docs/a.md"], floor="T2")["tier"], "T2")

    def test_assess_diff(self):
        git(self.root, "checkout", "-q", "-b", "change")
        self.write("src/billing/invoice.py", "x = 1\n")
        self.commit("billing")
        self.assertEqual(risk.assess_diff(self.root, "main")["tier"], "T3")
