---
id: W-0002
type: plan
status: accepted
spec: ./spec.md
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-09-22
---

# 승인 수를 위험 등급 정책에서 읽는다 — Plan

## Steps

- [x] `sdlc/artifacts.py` 의 `required_approvals` 에 `root` 인자를 더하고
      `policy.load` 로 `human_reviews` 를 읽는다. 바닥은 `max(1, n)` — `W-0002:AC-1` `AC-2` `AC-3`
- [x] 되돌아갈 자리를 넓게 잡는다 (파일 없음·키 없음·형 틀림·불리언) — `W-0002:AC-4`
- [x] 부르는 세 자리에 `root` 를 넘긴다: `workitems.approve`,
      `artifacts.validate`, `api` — `W-0002:AC-6`
- [x] `tests/` 에 시험을 더한다. 정책을 임시 디렉터리에 지어 넣고 본다 —
      `AC-1` ~ `AC-5`
- [x] **어긋남 시험**: `human_reviews: 1` 정책에서 승인 1 건 뒤 `validate` 가
      불평하지 않는 것. 셋 중 한 자리에서 `root` 를 빼면 이 시험이 깨지는지
      변이로 확인한다 — `W-0002:AC-6`
- [x] `make check` — `W-0002:AC-7`
- [x] 커밋 · push · PR

## Test strategy

| AC | 시험 |
|---|---|
| AC-1 | `root=None` 이면 T3 spec 2, T2 spec 1, intent 1 |
| AC-2 | `human_reviews: 1` 정책 -> T3 spec 1 |
| AC-3 | `human_reviews: 0` 정책 -> spec/plan 1 (0 아님) |
| AC-4 | 파일 없음 / 값이 `"1"` / 값이 `True` -> 되돌아간 값 |
| AC-5 | 이 저장소의 실제 `policy/risk-tiers.json` -> T3 spec 2 |
| AC-6 | 승인 1 건 뒤 validate 가 조용하다 (세 자리가 같은 답) |

## Rollback

`required_approvals` 의 `root` 를 무시하면 이전 동작이다. 부르는 자리는 인자를
더 넘길 뿐이라 그대로 둬도 된다.

## Risks

- **한 자리를 빠뜨리면 조용히 어긋난다** — 승인은 되는데 validate 가 막거나
  그 반대. AC-6 이 그것을 본다.
- 정책을 잘못 쓰면 승인이 줄어든다. 바닥 1 이 최악을 막는다.
