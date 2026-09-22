---
id: W-0003
type: intent
status: proposed
owner: kos2001 <62705131+kos2001@users.noreply.github.com>
sources:
  - kind: defect
    ref: "lls-kit W-0018: spec 이 승인 1 건을 갖고도 proposed 에 남아, 사람이 status 를 손으로 고쳐야 했다 (2026-09-23)"
risk_tier: T2
origin: human
approvals: []
---

# 승인 요건이 낮아진 아티팩트를 다시 센다

## Problem

W-0002 로 승인 수가 정책에서 오게 됐다. 그러면 **요건이 낮아지는 일**이 생긴다 —
lls-kit 에서 T3 이 2 건에서 1 건이 됐다.

그런데 이미 `proposed` 인 아티팩트는 그대로 멈춰 있다. 승인 기록은 1 건으로
이미 충분한데 `status` 가 `proposed` 다. 승인 명령을 다시 부르면 같은 신원이라
거절한다 — `ERROR ... already approved work/2026/W-0018-38-523-1/spec.md`.

빠져나갈 길이 **손으로 status 를 고치는 것**뿐이었다. 게이트를 사람이 손으로
넘는 순간, 그 게이트가 무엇을 지켰는지 아무도 모르게 된다. 실제로 lls-kit 에서
그렇게 했다.

승인 명령은 승인을 **더하는** 자리라 "이미 충분한가" 를 묻는 곳이 없다.

## Desired outcome

승인이 이미 충분한 아티팩트를 **기록을 건드리지 않고** accepted 로 올릴 수 있다.

- `sdlc recheck <path>`: 지금 정책으로 필요한 수를 세고, 기록된 승인이 그만큼이면
  `proposed -> accepted` 로 올린다.
- 승인을 **만들지 않는다.** `approvals:` 에 아무것도 더하지 않는다. 모자라면
  모자란다고 말하고 끝낸다.
- 검증을 통과하지 못하면 올리지 않는다 (`_save_if_valid` 와 같은 길).

## Constraints

- 표준 라이브러리만, `make check` 통과.
- **요건이 올라간 경우에는 내리지 않는다.** accepted 였는데 요건이 늘었다면
  그건 검증이 불평할 일이지 이 명령이 되돌릴 일이 아니다.
- 사람이 부르는 명령이다. 에이전트가 이것으로 게이트를 넘지 못하게, 훅이 승인
  명령을 막는 것과 같은 선에 둔다.

## Out of scope

- 승인 기록의 이력(누가 언제 무엇을 승인했나)을 바꾸는 일.
- 정책이 바뀐 것을 감지해 자동으로 도는 일. 사람이 부른다.

## Open questions

없다.
