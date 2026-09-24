"""How many humans a gate needs, and where that number comes from (W-0002).

The count lives in policy/risk-tiers.json, not in the code. A repo with one owner
writes `human_reviews: 1` for T3 and can then finish T3 work; a repo with a code
owner and a domain expert writes 2 and keeps both. Before this, the code said 2 and
a single-owner repo could never accept a T3 spec at all.
"""

import json

from sdlc import artifacts, policy, workitems
from tests.helpers import PROJECT, RepoTestCase


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


class RecheckTest(RepoTestCase):
    """이미 충분한 승인을 기록만으로 인정한다 (W-0003).

    정책이 T3 을 2 건에서 1 건으로 낮추면 이미 proposed 인 것은 그대로 멈춘다 -
    승인 명령은 승인을 **더하는** 자리이고 같은 사람은 두 번 못 한다. 빠져나갈
    길이 손으로 status 를 고치는 것뿐이었다.
    """

    def single_owner(self, tier: str = "T3", reviews: int = 1):
        path = self.root / "policy" / "risk-tiers.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["tiers"][tier]["human_reviews"] = reviews
        path.write_text(json.dumps(config), encoding="utf-8")
        self.commit("policy")

    def proposed_spec(self, tier: str = "T3", approvals: int = 1):
        intent = workitems.new_work(self.root, "Spec tables", self.human, tier, year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        workitems.submit(spec, self.root)
        if approvals:
            try:
                workitems.approve(spec, self.root, self.human, "product-owner")
            except workitems.GateError:
                pass
        return spec

    # W-0003:AC-1
    def test_enough_approvals_become_accepted(self):
        self.single_owner()
        spec = self.proposed_spec()
        art = artifacts.load(spec, self.root)
        self.assertEqual(art.meta["status"], "accepted")   # 이 정책에서는 approve 가 이미 올린다

    # W-0003:AC-2
    def test_not_enough_refuses_and_says_how_many(self):
        self.single_owner(reviews=2)
        spec = self.proposed_spec()
        with self.assertRaises(workitems.GateError) as caught:
            workitems.recheck(spec, self.root)
        # recheck 가 **스스로** 거절해야 한다. 검사를 지워도 뒤의 validate 가
        # 막아서 거절은 나지만, 그 메시지는 다르다 ("needs N human approval(s)").
        # 그것까지 통과로 세면 검사가 없는 것을 못 본다
        self.assertIn("needs 2 approval(s), has 1", str(caught.exception))
        self.assertEqual(artifacts.load(spec, self.root).meta["status"], "proposed")

    # W-0003:AC-5
    def test_invalid_artifact_does_not_move(self):
        """검증이 불평하면 status 가 안 바뀐다 - _save_if_valid 와 같은 길."""
        self.single_owner()
        intent = workitems.new_work(self.root, "Broken", self.human, "T3", year=2026)
        self.fill_intent(intent)
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        workitems.submit(spec, self.root)
        spec.write_text(spec.read_text(encoding="utf-8").replace(
            "## Acceptance criteria", "## Nothing here"), encoding="utf-8")
        with self.assertRaises(workitems.GateError):
            workitems.recheck(spec, self.root)
        self.assertEqual(artifacts.load(spec, self.root).meta["status"], "proposed")

    # W-0003:AC-3
    def test_recheck_writes_no_approval(self):
        self.single_owner(reviews=2)
        spec = self.proposed_spec()
        before = list(artifacts.load(spec, self.root).meta["approvals"])
        with self.assertRaises(workitems.GateError):
            workitems.recheck(spec, self.root)
        self.assertEqual(artifacts.load(spec, self.root).meta["approvals"], before)

    # W-0003:AC-1
    def test_lowering_the_policy_unblocks_a_stuck_artifact(self):
        """멈춘 것을 푸는 길 - 손으로 status 를 고치지 않는다."""
        self.single_owner(reviews=2)
        spec = self.proposed_spec()
        self.assertEqual(artifacts.load(spec, self.root).meta["status"], "proposed")
        self.single_owner(reviews=1)                       # 소유자가 하나라고 정책을 고쳤다
        art = workitems.recheck(spec, self.root)
        self.assertEqual(art.meta["status"], "accepted")
        self.assertEqual(len(art.meta["approvals"]), 1)    # 승인은 늘지 않았다

    # W-0003:AC-6 · W-0003:AC-7 (make check 가 이 파일을 돈다)
    def test_recheck_is_a_human_command(self):
        """게이트를 넘는 문이라 훅이 막는다 - 승인 명령과 같은 선이다.

        승인을 만들지는 않지만 상태를 올린다. 막지 않으면 에이전트가 요건이
        낮은 등급으로 아티팩트를 만들고 스스로 올릴 길이 된다.
        """
        guard = json.loads((PROJECT / "policy" / "guard.json").read_text(encoding="utf-8"))
        patterns = [c["pattern"] for c in guard["blocked_commands"]]
        self.assertTrue(any("recheck" in p for p in patterns), patterns)
        self.assertTrue(any("approve" in p for p in patterns), patterns)

    # W-0003:AC-4
    def test_refuses_when_not_proposed(self):
        self.single_owner()
        spec = self.proposed_spec()                        # 이미 accepted
        with self.assertRaises(workitems.GateError):
            workitems.recheck(spec, self.root)
