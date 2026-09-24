"""T3 는 무엇에 기대는지 보여야 한다 (W-0004).

W-0002 로 승인 수가 정책에서 오게 되자 쓰는 저장소가 T3 을 1 건으로 낮췄다.
그 근거는 정책 머리말이었다 - "one approval **plus spec-text evidence
(clause + version)**". 낮추는 쪽은 코드가 됐고 더하는 쪽은 글로 남았다.

조항 번호만으로는 안 된다. "38.214 5.1.3" 은 릴리스마다 다른 표를 가리킨다.
승인자를 둘에서 하나로 줄인 저장소가 그 대가로 내놓는 것이 **어느 판본을
봤는가** 다.

규격이 근거가 아닌 T3 도 있다 (게이트·정책·결함). 그런 것은 intent 의 sources
가 말한다. 빈 sources 는 아무 말도 하지 않으므로 통과하지 않는다.
"""

import re

from sdlc import artifacts, workitems
from tests.helpers import RepoTestCase

SPEC_SOURCE = "sources:\n  - kind: spec\n    ref: {ref}"
DEFECT_SOURCE = "sources:\n  - kind: defect\n    ref: the checkout latency report"


class T3EvidenceTest(RepoTestCase):
    def work(self, tier: str, sources: str, body_extra: str = ""):
        intent = workitems.new_work(self.root, "Spec tables", self.human, tier, year=2026)
        self.fill_intent(intent)                           # 틀이 ticket 근거를 넣는다
        text = intent.read_text(encoding="utf-8").replace(
            "sources:\n  - kind: ticket\n    ref: SUP-1", sources.rstrip("\n"))
        intent.write_text(text, encoding="utf-8")
        workitems.submit(intent, self.root)
        workitems.approve(intent, self.root, self.human, "product-owner")
        spec = workitems.add_stage(self.root, intent.parent, "spec")
        self.fill_spec(spec)
        if body_extra:
            spec.write_text(spec.read_text(encoding="utf-8") + body_extra, encoding="utf-8")
        return spec

    def issues(self, spec):
        index = {a.rel: a for a in artifacts.discover(self.root)}
        art = index[spec.relative_to(self.root).as_posix()]
        return [i.message for i in artifacts.validate(art, index)]

    def submit(self, spec):
        workitems.submit(spec, self.root)

    # W-0004:AC-1
    def test_clause_without_version_is_refused(self):
        spec = self.work("T3", SPEC_SOURCE.format(ref='"38.214 5.1.3"'))
        with self.assertRaises(workitems.GateError) as caught:
            self.submit(spec)
        self.assertIn("without a version", str(caught.exception))

    # W-0004:AC-2
    def test_clause_with_version_in_sources_passes(self):
        spec = self.work("T3", SPEC_SOURCE.format(ref='"38.214 V18.10.0 5.1.3"'))
        self.submit(spec)
        self.assertEqual([], [m for m in self.issues(spec) if "version" in m])

    # W-0004:AC-2
    def test_version_in_the_body_also_counts(self):
        spec = self.work("T3", SPEC_SOURCE.format(ref='"38.214 5.1.3"'),
                         body_extra="\n\nRead against RFC 3095 5.9.2.\n")
        self.submit(spec)
        self.assertEqual([], [m for m in self.issues(spec) if "version" in m])

    # W-0004:AC-3
    def test_a_defect_source_needs_no_version(self):
        spec = self.work("T3", DEFECT_SOURCE)
        self.submit(spec)
        self.assertEqual([], [m for m in self.issues(spec) if "version" in m])

    # W-0004:AC-4
    def test_empty_sources_never_reaches_the_spec(self):
        """빈 sources 는 **intent 단계**가 이미 막는다.

        새 검사의 그 갈래는 닿지 않는다 - 지켜지는 자리가 여기임을 못 박아 둔다.
        방어로 남겨 두되, 이것이 AC-4 를 지키는 규칙이라고 적는다.
        """
        intent = workitems.new_work(self.root, "Spec tables", self.human, "T3", year=2026)
        self.fill_intent(intent)
        text = intent.read_text(encoding="utf-8").replace(
            "sources:\n  - kind: ticket\n    ref: SUP-1", "sources: []")
        intent.write_text(text, encoding="utf-8")
        with self.assertRaises(workitems.GateError) as caught:
            workitems.submit(intent, self.root)
        self.assertIn("sources must cite", str(caught.exception))

    # W-0004:AC-5
    def test_t2_is_not_asked_for_a_version(self):
        spec = self.work("T2", SPEC_SOURCE.format(ref='"38.214 5.1.3"'))
        self.submit(spec)                                  # 버전이 없어도 불평하지 않는다
        self.assertEqual([], [m for m in self.issues(spec) if "version" in m])

    # W-0004:AC-5 · W-0004:AC-6 (make check 가 이 파일을 돈다)
    def test_the_pattern_is_not_a_catch_all(self):
        """버전처럼 보이는 것만 버전으로 센다 - 아무 숫자나 통과하면 검사가 없다."""
        self.assertTrue(re.search(artifacts.SPEC_VERSION if hasattr(artifacts, "SPEC_VERSION")
                                  else __import__("sdlc.policy", fromlist=["x"]).SPEC_VERSION,
                                  "38.214 V18.10.0"))
        from sdlc import policy
        self.assertIsNone(policy.SPEC_VERSION.search("38.214 5.1.3"))
        self.assertIsNone(policy.SPEC_VERSION.search("clause 5.3.5.13.4"))
