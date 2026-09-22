"""How many humans a gate needs, and where that number comes from (W-0002).

The count lives in policy/risk-tiers.json, not in the code. A repo with one owner
writes `human_reviews: 1` for T3 and can then finish T3 work; a repo with a code
owner and a domain expert writes 2 and keeps both. Before this, the code said 2 and
a single-owner repo could never accept a T3 spec at all.
"""

import json

from sdlc import artifacts, policy, workitems
from tests.helpers import RepoTestCase


def policy_with(reviews):
    return {"tiers": {tier: {"human_reviews": n} for tier, n in reviews.items()},
            "rules": [], "default": "T1"}


class RequiredApprovalsTest(RepoTestCase):
    def write_policy(self, obj) -> None:
        (self.root / "policy").mkdir(exist_ok=True)
        (self.root / "policy" / "risk-tiers.json").write_text(json.dumps(obj), encoding="utf-8")

    # W-0002:AC-1
    def test_without_a_root_the_built_in_rule_stands(self):
        self.assertEqual(policy.required_approvals("spec", "T3"), 2)
        self.assertEqual(policy.required_approvals("plan", "T3"), 2)
        self.assertEqual(policy.required_approvals("spec", "T2"), 1)
        self.assertEqual(policy.required_approvals("intent", "T3"), 1)

    # W-0002:AC-2
    def test_policy_saying_one_is_honoured(self):
        self.write_policy(policy_with({"T3": 1, "T2": 1}))
        self.assertEqual(policy.required_approvals("spec", "T3", self.root), 1)
        self.assertEqual(policy.required_approvals("plan", "T3", self.root), 1)

    # W-0002:AC-3
    def test_the_floor_is_one_even_when_policy_says_zero(self):
        self.write_policy(policy_with({"T0": 0, "T1": 0}))
        self.assertEqual(policy.required_approvals("spec", "T1", self.root), 1)
        self.assertEqual(policy.required_approvals("plan", "T0", self.root), 1)

    # W-0002:AC-4
    def test_unusable_policy_falls_back(self):
        (self.root / "policy" / "risk-tiers.json").unlink()
        self.assertEqual(policy.required_approvals("spec", "T3", self.root), 2)
        self.write_policy({"tiers": {"T3": {"human_reviews": "1"}}})
        self.assertEqual(policy.required_approvals("spec", "T3", self.root), 2)
        self.write_policy({"tiers": {"T3": {"human_reviews": True}}})   # bool is not a count
        self.assertEqual(policy.required_approvals("spec", "T3", self.root), 2)
        self.write_policy({"tiers": {"T2": {"human_reviews": 1}}})      # tier missing
        self.assertEqual(policy.required_approvals("spec", "T3", self.root), 2)

    # W-0002:AC-5
    def test_this_repo_still_needs_two_for_t3(self):
        from tests.helpers import PROJECT
        self.assertEqual(policy.required_approvals("spec", "T3", PROJECT), 2)


class ApproveAndValidateAgreeTest(RepoTestCase):
    """Every place that counts approvals must give the same answer (W-0002:AC-6).

    If one of them forgets the root, a single-owner repo gets a spec that `approve`
    calls accepted and `validate` calls short of approvals - or the reverse. Nobody
    would see it until a gate blocks for no visible reason.
    """

    # W-0002:AC-6
    def test_one_approval_accepts_and_validates_under_a_single_owner_policy(self):
        policy_path = self.root / "policy" / "risk-tiers.json"
        config = json.loads(policy_path.read_text(encoding="utf-8"))
        config["tiers"]["T3"]["human_reviews"] = 1
        policy_path.write_text(json.dumps(config), encoding="utf-8")
        self.commit("single owner policy")

        intent = workitems.new_work(self.root, "Spec tables", self.human, "T3", year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        workitems.submit(spec, self.root)
        art = workitems.approve(spec, self.root, self.human, "product-owner")

        self.assertEqual(art.meta["status"], "accepted")
        index = {a.rel: a for a in artifacts.discover(self.root)}
        issues = artifacts.validate(index[art.rel], index)
        self.assertEqual([i.message for i in issues if "approval" in i.message], [])
