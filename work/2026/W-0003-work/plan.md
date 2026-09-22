---
id: W-0003
type: plan
status: draft
spec: ./spec.md
approvals: []
---

# 승인 요건이 낮아진 아티팩트를 다시 센다 — Plan

## Steps

- [ ] `workitems.recheck(art, root)` — 요건을 세고, 충분하면 accepted, 아니면
      GateError. `approvals:` 는 읽기만 — `W-0003:AC-1` `AC-2` `AC-3`
- [ ] `proposed` 가 아니면 거절 (`_require`) — `W-0003:AC-4`
- [ ] 저장은 `_save_if_valid` 로 — `W-0003:AC-5`
- [ ] `cli.py` 에 하위 명령
- [ ] 훅의 차단 목록에 더한다 — **`policy/**` 는 보호 경로라 사람이 한다.**
      패치를 만들어 두고 알린다 — `W-0003:AC-6`
- [ ] `tests/test_approvals.py` 에 이어 붙인다 — `AC-1` ~ `AC-5`
- [ ] **변이로 확인**: 요건 검사를 지우면 AC-2 가 잡는가, 기록을 건드리면
      AC-3 이 잡는가
- [ ] `make check` — `W-0003:AC-7`
- [ ] 커밋 · push · PR

## Test strategy

기존 `tests/test_approvals.py` 가 이미 정책을 임시로 지어 넣는 틀을 갖고 있다.
거기 이어 붙인다.

| AC | 무엇으로 |
|---|---|
| AC-1 | 요건 1 · 승인 1 -> accepted |
| AC-2 | 요건 2 · 승인 1 -> 그대로, 메시지에 2 와 1, 코드 != 0 |
| AC-3 | 부르기 전후의 `approvals:` 가 같다 |
| AC-4 | draft / accepted 에 부르면 GateError |
| AC-5 | 검증이 불평하면 status 가 안 바뀐다 |
| AC-6 | 차단 목록에 이름이 있다 |

## Rollback

명령을 지우면 된다. 그러면 요건이 낮아졌을 때 **손으로 status 를 고치는** 길로
돌아간다 - 지금 상태다.

## Risks

- **게이트를 넘는 문이 하나 더 생긴다.** 승인을 만들지는 않지만 상태를 올린다.
  차단 목록에 넣지 않으면 에이전트가 스스로 넘을 길이 된다 (AC-6).
- 요건이 **올라간** 경우를 건드리면 안 된다. accepted 를 내리는 일은 하지 않는다.
