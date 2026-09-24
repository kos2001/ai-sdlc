---
id: W-0004
type: spec
status: accepted
intent: ./intent.md
skills_applied: []
risk_tier: T2
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-09-24
---

# T3 spec 에 원문 근거를 요구한다 — Spec

## Requirements

- **R1** `kind == "spec"` 이고 `risk_tier == "T3"` 일 때만 검사한다.
- **R2** 근거가 규격이면 (`sources` 에 `kind: spec` 이 있으면) **조항과 버전**이
  `sources` 나 본문에 보여야 한다. 버전은 `V<숫자>.<숫자>.<숫자>` · `V<숫자>.x`
  · `RFC <숫자>` 중 하나다.
- **R3** 근거가 규격이 아니면 `sources` 가 **비어 있지 않아야** 한다. 빈 칸으로
  통과하지 않는다.
- **R4** `sources` 와 본문을 둘 다 본다.
- **R5** T3 이 아닌 것, spec 이 아닌 것은 지금 그대로다.
- **R6** `make check` 통과.

## Design

`artifacts._validate_spec` 에 한 덩이를 더한다.

```python
SPEC_VERSION = re.compile(r"V\d+\.(x|\d+)(\.(y|\d+))?|RFC\s*\d+", re.I)

def _t3_evidence(art, err):
    if art.kind != "spec" or str(art.meta.get("risk_tier")) != "T3":
        return
    sources = art.meta.get("sources") or []
    if not sources:
        err("T3 spec needs sources: the clause and version it rests on, "
            "or why the source text is not the evidence")
        return
    if any(str(s.get("kind")) == "spec" for s in sources if isinstance(s, dict)):
        haystack = json.dumps(sources, ensure_ascii=False) + art.body
        if not SPEC_VERSION.search(haystack):
            err("T3 spec cites a clause without a version "
                "(e.g. '38.214 V18.10.0 5.1.3', 'RFC 3095 5.9.2')")
```

근거는 **intent 의 `sources`** 에서 읽는다. spec 템플릿에는 `sources` 칸이 없다 —
무엇에 기대는지는 intent 가 적는 자리다. spec 본문도 같이 본다.

`sdlc/artifacts.py` 가 12 KB 한도 근처라 검사는 `sdlc/policy.py` 에 둔다
(`required_approvals` 가 간 자리와 같다). 등급이 무엇을 요구하는가는 정책 쪽 물음이다.

### 구현하며 알게 된 것 — AC-4 는 이미 지켜지고 있었다

`sources` 가 빈 intent 는 **제출 자체가 안 된다**:

```
sources must cite at least one ticket/metric/incident/interview once proposed
```

그래서 빈 `sources` 를 든 T3 spec 은 생기지 않는다 — 새 검사의 그 갈래는 **닿지
않는다**. 방어로 남겨 두되, AC-4 를 지키는 것은 이 검사가 아니라 intent 의 기존
규칙이다. 시험도 그 자리에서 본다. 닿지 않는 코드를 "내가 막았다" 고 세면
게이트 수만 늘고 막는 힘은 늘지 않는다.

### 왜 버전까지인가

조항 번호는 릴리스마다 뜻이 달라진다. "38.214 §5.1.3" 은 Rel-15 와 Rel-18 이
다른 표를 가리킬 수 있다. 승인자를 둘에서 하나로 줄인 저장소가 그 대가로 내놓는
것이 **어느 판본을 봤는가**다. 버전이 없으면 그 대가가 없다.

## Acceptance criteria

- **AC-1** `kind: spec` 근거에 조항만 있고 버전이 없는 T3 spec 이 accepted 로
  못 간다 — R2.
- **AC-2** 조항 + 버전이 있으면 간다 (`sources` 에 있든 본문에 있든) — R2 · R4.
- **AC-3** 근거가 `kind: defect` 뿐인 T3 spec 은 버전 없이도 간다 — R3.
- **AC-4** `sources` 가 비어 있는 T3 spec 은 못 간다 — R3.
- **AC-5** T2 spec 과 T3 intent/plan 은 이 검사를 받지 않는다 — R5.
- **AC-6** `make check` 통과 — R6.

## Security & compliance notes

이 검사는 **모양만 본다.** `V18.10.0` 이 적혀 있는지는 보지만 그 판본의 그 조항이
정말 그렇게 말하는지는 못 본다. 모양 검사를 대조로 착각하면 안 된다 - 쓰는
저장소는 대조 목록을 따로 들고 있어야 한다 (lls-kit 의 `docs/verification.md`).

그래도 값이 있다. 지금은 **아무것도** 요구하지 않는다.

## Alternatives considered

- **승인 수와 묶어 한 검사로**: 승인이 모자란 것과 근거가 없는 것은 다른 실패다.
  메시지가 흐려진다.
- **모든 등급에 요구**: T0~T2 는 근거가 측정·결함인 경우가 많다. 형식적인 인용만 는다.
