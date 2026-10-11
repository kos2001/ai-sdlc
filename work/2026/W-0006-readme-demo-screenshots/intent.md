---
id: W-0006
type: intent
status: proposed
owner: kos2001 <62705131+kos2001@users.noreply.github.com>
sources:
  - kind: feedback
    ref: "User request 2026-10-11: ai-sdlc README에 영문 버전과 데모 스크린샷을 추가해 보강"
  - kind: measurement
    ref: README.md / README.en.md reference only web/icons/app-icon.svg; no screenshot of the web app
risk_tier: T0
origin: human
approvals: []
---

# README demo screenshots

## Problem
README를 읽는 사람은 웹 앱이 무엇을 보여주는지 설치해 보기 전에는 알 수 없다.
두 README 모두 아이콘 외에 이미지가 없고(measurement), 사용자가 영문 README 보강과 데모 스크린샷을 요청했다(feedback).

## Desired outcome
`python3 -m sdlc demo` 샘플 저장소에서 찍은 개요·보드·작업 항목·개선 루프 4장이 `docs/img/`에 있고,
README.md와 README.en.md의 웹 앱 절에서 같은 4장을 참조한다. 깨진 이미지 링크 0건, `make check` 통과.

## Constraints
- 문서만 변경한다(T0). 코드·정책·워크플로는 건드리지 않는다.
- 스크린샷은 샘플 데이터만 담는다.

## Out of scope
- 대시보드 기능 변경, 제품 사이트(web/index.html) 변경.

## Open questions
- 없음.
