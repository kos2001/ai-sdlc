---
id: W-0002
type: spec
status: accepted
intent: ./intent.md
skills_applied: []
risk_tier: T2
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-09-22
---

# 승인 수를 위험 등급 정책에서 읽는다 — Spec

## Requirements

- **R1** `required_approvals(kind, tier, root=None)` 가 `root` 를 받으면
  `policy/risk-tiers.json` 의 `tiers[tier].human_reviews` 를 읽는다.
- **R2** **바닥은 1 이다.** `max(1, human_reviews)` — `human_reviews` 가 0 인
  등급(T0/T1)에서도 spec/plan 은 승인 1 건을 받아야 한다. 정책을 읽는 것이
  게이트를 느슨하게 만들면 안 된다.
- **R3** 되돌아갈 자리가 있다. `root` 가 없거나, 파일이 없거나, 등급이 표에
  없거나, `human_reviews` 가 정수가 아니면 **지금 규칙**(T3 의 spec/plan 은 2,
  나머지는 1)을 그대로 쓴다.
- **R4** 이 저장소의 동작은 바뀌지 않는다 — `policy/risk-tiers.json` 이 T3 을
  2 로 적어 두었기 때문이다. 시험이 그것을 확인한다.
- **R5** 승인을 세는 자리 **전부**가 같은 답을 쓴다 — `workitems.approve`,
  `artifacts.validate`, `api`. 한 자리만 고치면 승인은 되는데 validate 가
  막는(또는 그 반대) 어긋남이 생긴다.
- **R6** `policy/**` 는 고치지 않는다. 읽기만 한다.

## Design

```python
def required_approvals(kind: str, tier: str, root: Path | None = None) -> int:
    if kind not in ("spec", "plan"):
        return 1
    if root is not None:
        try:
            tiers = policy.load(root, "risk-tiers.json").get("tiers", {})
            n = tiers[tier]["human_reviews"]
        except (OSError, KeyError, ValueError, TypeError):
            n = None
        if isinstance(n, int) and not isinstance(n, bool):
            return max(1, n)
    return 2 if tier == "T3" else 1
```

`policy.load` 는 이미 있다 (`sdlc/policy.py:44`). `risk.py` 가 같은 파일을 같은
방식으로 읽는다 — 새 경로도, 새 형식도 만들지 않는다.

`root` 를 넘기는 자리:

| 부르는 곳 | `root` 를 어디서 얻나 |
|---|---|
| `workitems.approve` | 인자로 받은 `root` |
| `artifacts.validate` | `art.root` |
| `api` (`needed`) | 그 호출이 이미 들고 있는 art/root |

## Acceptance criteria

- **AC-1** `root` 없이 부르면 지금 값이다 — T3 의 spec/plan 은 2, 그 밖은 1 — R3.
- **AC-2** `human_reviews: 1` 로 적은 정책을 쥐여 주면 T3 의 spec 이 1 을 낸다 — R1.
- **AC-3** `human_reviews: 0` 인 등급도 spec/plan 은 1 을 낸다 (0 이 아니다) — R2.
- **AC-4** 정책 파일이 없거나 값이 문자열·불리언이면 되돌아간 값을 낸다 — R3.
- **AC-5** 이 저장소의 실제 정책으로 T3 spec 은 여전히 2 다 — R4.
- **AC-6** 승인을 세는 세 자리가 같은 함수를 같은 `root` 로 부른다. 한 자리라도
  `root` 없이 부르면 `human_reviews: 1` 정책에서 승인과 validate 가 어긋나는데,
  시험이 그 어긋남을 잡는다 — R5.
- **AC-7** `make check` 통과.

## Security & compliance notes

이 변경은 **게이트의 세기를 정책 파일로 옮긴다.** 코드에 박아 두는 것보다
느슨해 보일 수 있으나, 정책 파일은 보호 경로(사람만 고친다)이고 이미 위험 등급
자체를 정하는 자리다. 승인자 수만 따로 코드에 박혀 있던 것이 오히려 어긋남의
원인이었다.

바닥 1 (R2)이 이 변경의 안전판이다. 정책을 잘못 써도 승인 없는 spec/plan 은
없다.

## Alternatives considered

- **T3 의 2 를 그냥 1 로 바꾸기**: 이 저장소의 정책(코드 소유자 + 도메인 전문가,
  2 명)을 어긴다. 쓰는 쪽마다 다른 답이 필요한 것이 문제의 본질이다.
- **`required_approvals` 에 저장소별 설정 파일을 새로 만들기**: 같은 것을 정하는
  파일이 둘이 된다. `risk-tiers.json` 이 이미 그 자리다.
