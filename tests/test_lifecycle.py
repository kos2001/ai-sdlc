"""Play 1 (capture intent) -> Play 9 (spec) -> Play 6 (plan): the gated artifact chain."""

from sdlc import artifacts, cli, workitems
from tests.helpers import RepoTestCase


class LifecycleTest(RepoTestCase):
    def issues(self):
        return [str(i) for i in cli.validate_all(self.root)]

    def test_full_chain_through_all_gates(self):
        intent = workitems.new_work(self.root, "Checkout latency", self.human, "T2", year=2026)
        self.assertEqual(intent.relative_to(self.root).as_posix(), "work/2026/W-0001-checkout-latency/intent.md")
        self.assertEqual(self.issues(), [])  # a blank draft is valid

        with self.assertRaisesRegex(workitems.GateError, "sources"):
            workitems.submit(intent, self.root)  # cannot propose without evidence
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        art = workitems.approve(intent, self.root, self.human, "product-owner")
        self.assertEqual(art.status, "accepted")

        spec = workitems.add_stage(self.root, intent.parent, "spec")
        with self.assertRaisesRegex(workitems.GateError, "Acceptance criteria"):
            workitems.submit(spec, self.root)
        self.fill_spec(spec)
        workitems.submit(spec, self.root)
        workitems.approve(spec, self.root, self.human, "architect")

        plan = workitems.add_stage(self.root, intent.parent, "plan")
        self.fill_plan(plan)
        workitems.submit(plan, self.root)
        workitems.approve(plan, self.root, self.human, "tech-lead")
        self.assertEqual(self.issues(), [])

        # done requires every step checked and every AC traced to a test
        self.assertEqual(cli.main(["--root", str(self.root), "done", str(plan)]), 1)
        self.assertEqual(artifacts.load(plan, self.root).status, "accepted")  # rolled back
        self.fill_plan_checked(plan)
        self.write("tests/test_checkout.py", "# W-0001:AC-1\n# W-0001:AC-2\n")
        self.assertEqual(cli.main(["--root", str(self.root), "done", str(plan)]), 0)
        self.assertEqual(self.issues(), [])

    def fill_plan_checked(self, plan):
        plan.write_text(plan.read_text().replace("- [ ]", "- [x]"))

    def test_spec_cannot_be_proposed_before_intent_is_accepted(self):
        intent = workitems.new_work(self.root, "X", self.human, year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        with self.assertRaisesRegex(workitems.GateError, "intent must be accepted first"):
            workitems.submit(spec, self.root)

    def test_agent_identity_cannot_approve(self):
        intent = workitems.new_work(self.root, "X", self.human, year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        with self.assertRaisesRegex(workitems.GateError, "agent identity"):
            workitems.approve(intent, self.root, "Claude <noreply@anthropic.com>", "product-owner")

    def test_hand_edited_agent_approval_is_caught_by_validate(self):
        intent = workitems.new_work(self.root, "X", self.human, year=2026)
        self.fill_intent(intent)
        text = intent.read_text().replace("status: draft", "status: accepted").replace(
            "approvals: []", "approvals:\n  - by: claude[bot]\n    role: po\n    at: 2026-09-18")
        intent.write_text(text)
        self.assertTrue(any("only humans approve" in i for i in self.issues()))

    def test_t3_spec_and_plan_need_two_approvals(self):
        intent = workitems.new_work(self.root, "Payments", self.human, "T3", year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        workitems.submit(spec, self.root)
        self.assertEqual(workitems.approve(spec, self.root, self.human, "architect").status, "proposed")
        with self.assertRaisesRegex(workitems.GateError, "already approved"):
            workitems.approve(spec, self.root, self.human, "architect")
        art = workitems.approve(spec, self.root, "Sam Lee <sam@example.com>", "security")
        self.assertEqual(art.status, "accepted")

    def test_spec_cannot_lower_risk_tier(self):
        intent = workitems.new_work(self.root, "X", self.human, "T2", year=2026)
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        spec.write_text(spec.read_text().replace("risk_tier: T2", "risk_tier: T1"))
        self.assertTrue(any("tiers can only go up" in i for i in self.issues()))

    def test_sequential_ids(self):
        workitems.new_work(self.root, "A", self.human, year=2026)
        second = workitems.new_work(self.root, "B", self.human, year=2026)
        self.assertIn("W-0002-b", second.as_posix())


class TransitionTest(RepoTestCase):
    def test_illegal_transition_and_approval_tampering(self):
        intent = workitems.new_work(self.root, "X", self.human, year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        self.commit("accepted intent")
        from tests.helpers import git
        git(self.root, "checkout", "-q", "-b", "change")
        text = intent.read_text().replace("status: accepted", "status: draft")
        text = text.replace("Dana Park <dana@example.com>", "Someone Else")
        intent.write_text(text)
        self.commit("tamper")
        messages = [str(i) for i in cli.transition_issues(self.root, "main")]
        self.assertTrue(any("illegal status transition accepted -> draft" in m for m in messages))
        self.assertTrue(any("append-only" in m for m in messages))

    def test_deleting_an_artifact_is_flagged(self):
        intent = workitems.new_work(self.root, "X", self.human, year=2026)
        self.commit("draft")
        from tests.helpers import git
        git(self.root, "checkout", "-q", "-b", "change")
        intent.unlink()
        self.commit("delete")
        messages = [str(i) for i in cli.transition_issues(self.root, "main")]
        self.assertTrue(any("never deleted" in m for m in messages))
