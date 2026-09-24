---
id: W-0004
type: intent
status: accepted
owner: kos2001 <62705131+kos2001@users.noreply.github.com>
sources:
  - kind: defect
    ref: lls-kit W-0019 가 T3 승인을 2 건에서 1 건으로 낮추며 진 빚 - 정책이 요구하는 '원문 근거' 는 강제되지 않는다
risk_tier: T2
origin: human
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-09-24
---

# T3 spec 에 원문 근거를 요구한다

## Problem

W-0002 로 승인 수가 정책에서 오게 됐고, 쓰는 쪽(lls-kit)은 T3 을 **1 건**으로
낮췄다. 그 근거는 그 저장소의 정책 머리말이다:

> "Single owner, so T3 is one approval **plus spec-text evidence (clause + version)**,
> not two people."

**낮추는 쪽은 코드가 됐고, 더하는 쪽은 글로 남았다.** T3 spec 이 조항도 버전도
적지 않고 accepted 로 간다. 가장 무거운 등급에서 그러고 있다.

이것은 한 저장소의 사정이 아니다. `human_reviews` 를 1 로 적는 저장소는 모두
같은 자리에 선다 - 승인자 하나로 줄인 대가를 무엇으로 치를지 도구가 묻지 않는다.

## Desired outcome

`risk_tier: T3` 인 spec 이 accepted 로 가려면 근거가 **보여야** 한다.

- 규격이 근거면 **조항과 버전**이 같이 있어야 한다 (`V18.10.0`, `RFC 3095` 꼴).
  조항 번호만으로는 안 된다.
- 규격이 근거가 아니면 (게이트·정책·결함에서 온 T3) `sources` 에 그것이 있어야
  한다. **빈 `sources` 는 통과하지 않는다.**
- `sources` 와 본문을 **둘 다** 본다. 한쪽만 보면 다른 쪽으로 빠져나간다.

## Constraints

- 표준 라이브러리만, `make check` 통과.
- **이미 accepted 된 것을 거꾸로 깨지 않는다.** 검사는 spec 에만, T3 에만 건다.
- 이 저장소의 T3 은 `policy/**` 등이라 spec 이 없을 수도 있다 - 없으면 조용하다.

## Out of scope

- 'check.py 출력' 같은 실행 결과를 아티팩트에 박게 하는 일. 출력은 낡는다.
  AC 와 시험의 연결은 `trace` 가 이미 든다.
- T0~T2 에 같은 요구를 다는 일. 그쪽은 근거가 측정인 경우가 많고, 모양을
  요구하면 형식적인 인용만 는다.

## Open questions

없다.
