---
id: W-0003
type: spec
status: draft
intent: ./intent.md
skills_applied: []
risk_tier: T2
approvals: []
---

# 승인 요건이 낮아진 아티팩트를 다시 센다 — Spec

## Requirements

- **R1** `sdlc recheck <path>` 가 그 아티팩트에 지금 필요한 승인 수를 정책에서
  세고, 기록된 승인이 그만큼이면 `proposed -> accepted` 로 올린다.
- **R2** **승인을 만들지 않는다.** `approvals:` 는 읽기만 한다. 모자라면 몇 건이
  모자란지 말하고 **0 이 아닌 코드**로 끝낸다.
- **R3** 검증을 통과하지 못하면 올리지 않는다 — 기존 상태 변경과 같은 길
  (`_save_if_valid`).
- **R4** `proposed` 가 아닌 것은 건드리지 않는다. accepted 를 다시 내리지도,
  draft 를 건너뛰지도 않는다.
- **R5** 훅이 막는 목록에 들어간다. 승인 명령과 같은 선이다 — 사람이 부른다.

## Design

`workitems.py` 에 함수 하나, `cli.py` 에 하위 명령 하나.

```python
def recheck(art, root):
    _require(art, "proposed")
    approvals = [a for a in art.meta.get("approvals") or [] if isinstance(a, dict)]
    need = policy.required_approvals(art.kind, _tier_for(art, root), root)
    if len(approvals) < need:
        raise GateError(f"{art.rel}: {need} 건 필요, {len(approvals)} 건 있음")
    art.meta["status"] = "accepted"
    return _save_if_valid(art, root, "recheck")
```

승인을 세는 자리가 이미 하나로 모여 있다 (W-0002). 여기서도 같은 것을 부른다.

### 왜 승인 명령을 고치지 않나

승인 명령은 "내가 승인한다" 는 뜻이다. 같은 사람이 두 번 부르는 것을 막는 것이
그 명령의 일이고, 그 규칙은 옳다. "이미 충분한가" 는 **다른 질문**이라 다른
명령에 둔다. 한 명령이 두 가지를 하면, 거절이 어느 쪽 이유인지 흐려진다.

## Acceptance criteria

- **AC-1** 승인 1 건 · 요건 1 건인 `proposed` spec 에 부르면 `accepted` 가 된다 — R1.
- **AC-2** 승인 1 건 · 요건 2 건이면 올라가지 않고, 메시지가 `2`·`1` 을 말하며,
  종료 코드가 0 이 아니다 — R2.
- **AC-3** 부른 뒤에도 `approvals:` 가 그대로다 (길이도 내용도) — R2.
- **AC-4** `draft` 나 `accepted` 에 부르면 거절한다 — R4.
- **AC-5** 검증이 불평하는 아티팩트는 올라가지 않는다 — R3.
- **AC-6** 훅의 차단 목록에 `recheck` 가 있다 — R5.
- **AC-7** `make check` 통과.

## Security & compliance notes

이 명령은 **게이트를 넘는 문**이다. 승인을 만들지는 않지만 상태를 올린다.
그래서 훅이 막는 목록(사람만 부른다)에 같이 넣는다 (R5 · AC-6). 그러지 않으면
에이전트가 요건이 낮은 등급으로 아티팩트를 만들고 스스로 올릴 길이 생긴다.

지금은 이 자리가 **손으로 status 를 고치는 것**이라 더 나쁘다 — 기록도 검증도
없이 넘는다. 이 작업은 그 길에 검증을 붙인다.

## Alternatives considered

- **승인 명령이 같은 신원의 재호출을 '재계산' 으로 받아들이기**: 거절 이유가
  흐려진다. "이미 승인했다" 와 "이제 충분하다" 는 다른 말이다.
- **정책이 바뀌면 자동으로 다시 세기**: 언제 도는지가 불분명해지고, 사람이
  모르는 사이에 게이트가 열린다.
