---
id: W-0004
type: plan
status: accepted
spec: ./spec.md
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-09-24
---

# T3 spec 에 원문 근거를 요구한다 — Plan

## Steps

- [x] 검사를 더하고 `_validate_spec` 에서 부른다. `artifacts.py` 가 12 KB 한도
      근처라 `policy.py` 에 뒀다 —
      `W-0004:AC-1` `AC-2` `AC-3` `AC-4`
- [x] T3 이 아니거나 spec 이 아니면 지나간다 — `W-0004:AC-5`
- [x] `tests/test_t3_evidence.py` — 다섯 갈래를 본다
- [x] **변이로 확인**: 버전 정규식을 느슨하게 하면 AC-1 이 잡는가,
      `sources` 검사를 빼면 AC-4 가 잡는가
- [x] 12 KB 게이트 (`artifacts.py` 가 한도 근처다 - 넘치면 `policy.py` 로 옮긴다)
- [x] `make check` — `W-0004:AC-6`
- [x] 커밋 · push · PR

## Test strategy

기존 `tests/helpers.py` 의 임시 저장소 틀을 쓴다.

| AC | 무엇으로 |
|---|---|
| AC-1 | `kind: spec` 근거 + 조항만 -> 거절 |
| AC-2 | 조항 + 버전 (sources / 본문 각각) -> 통과 |
| AC-3 | `kind: defect` 만 -> 통과 |
| AC-4 | `sources: []` -> 거절 |
| AC-5 | T2 spec, T3 intent/plan -> 검사 안 함 |

## Rollback

검사를 빼면 이전 동작이다. 그러면 승인 1 건짜리 T3 이 근거 없이 통과하는
자리로 돌아간다.

## Risks

- **모양만 본다.** 형식적인 인용이 늘 수 있다. spec 에 적었다.
- 쓰는 저장소의 기존 아티팩트를 깰 수 있다. lls-kit 에서 세어 보니 T3 9 개 중
  8 개가 이미 만족하고 하나(W-0019)는 `kind: defect` 근거라 AC-3 으로 통과한다.
