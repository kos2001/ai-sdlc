---
id: W-0002
type: intent
status: accepted
owner: kos2001 <62705131+kos2001@users.noreply.github.com>
sources:
  - kind: defect
    ref: "lls-kit: T3 spec/plan 이 승인될 수 없어 W-0004 가 2026-09-20 부터 proposed 로 멈춰 있다"
risk_tier: T2
origin: human
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-09-22
---

# 승인 수를 위험 등급 정책에서 읽는다

## Problem

`artifacts.required_approvals` 가 T3 의 spec/plan 에 **2** 를 못 박고 있다
(`sdlc/artifacts.py:157`). 같은 사람이 두 번 승인할 수는 없으므로, 승인자가
한 명인 저장소에서는 **T3 작업을 끝낼 방법이 없다.**

그런데 승인자 수는 이미 정책 파일에 있다 — `policy/risk-tiers.json` 의
`tiers.T3.human_reviews`. 이 저장소는 2 이고, 가져다 쓰는 저장소(lls-kit)는 1 로
두고 그 이유까지 적어 뒀다:

> "Single owner, so T3 is one approval plus spec-text evidence (clause + version,
> check.py output), not two people."

**코드가 그 파일을 읽지 않는다.** 그래서 정책과 동작이 갈렸고, 갈린 줄 모른 채
lls-kit 의 W-0004(PDCP 헤더 비트 배치, T3)가 승인 1 건을 받아 둔 채
**2026-09-20 부터 멈춰 있다**. 그 저장소에서 T3 은 규격 표·골든 벡터·게이트라
가장 무거운 등급인데, 하필 그쪽이 통째로 막힌다.

정책 파일을 읽는 자리는 이미 있다 (`sdlc/risk.py:19` 의 `policy.load`). 승인
규칙만 그것을 안 쓴다.

## Desired outcome

`required_approvals` 가 정책의 `human_reviews` 를 읽는다.

- 이 저장소의 동작은 그대로다 — T3 은 여전히 2 (정책에 2 라고 적혀 있다).
- 정책이 1 이라고 적은 저장소에서는 1 이다.
- **어느 등급도 0 으로는 내려가지 않는다.** T0/T1 은 `human_reviews` 가 0 이지만
  spec/plan 승인은 최소 1 건을 지킨다 (지금 동작). 정책을 읽는다고 게이트가
  느슨해지면 안 된다.

## Constraints

- `make check` 통과. 표준 라이브러리만 (`sdlc/` 규약).
- 정책 파일이 없거나 등급이 없으면 **지금 값으로 되돌아간다** (T3 은 2).
- `policy/**` 는 보호 경로다. 이 작업은 정책을 고치지 않고 **읽기만** 한다.

## Out of scope

- lls-kit 쪽 재반입(re-vendor)과 그 저장소의 보상 통제(T3 에 원문 근거를
  요구하는 검증). 거기서 따로 건다.
- 승인자의 역할(role)을 구분해 세는 일. 지금은 신원만 본다.

## Open questions

없다.
