---
id: W-0005
type: intent
status: accepted
owner: kos2001 <62705131+kos2001@users.noreply.github.com>
sources:
  - kind: feedback
    ref: "User request 2026-10-11: 프론트엔드를 interactive하게 변경을 하고 추가적인 작업들을 진행해 줘"
  - kind: measurement
    ref: "sdlc/webapp/views.js: board has no search/filter/sort; branch base cannot be selected in UI"
  - kind: measurement
    ref: "detail.js: artifacts are read-only and tabs lack keyboard navigation; app.js lacks a request-order guard"
risk_tier: T2
origin: human
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: product-owner
    at: 2026-10-11
---

# Interactive frontend workflow

## Problem
현재 웹 앱은 조회 중심이다. 보드에서 필요한 작업을 찾을 검색·필터가 없고,
새 작업의 초안은 외부 편집기로 이동해야 작성할 수 있다. 브랜치 비교 기준은
API가 지원하지만 화면에서 선택할 수 없다. 상세 탭은 클릭만 처리하며,
느린 응답의 화면 덮어쓰기와 생성 중 반복 제출을 막는 처리가 없다.

## Desired outcome
앱에서 작업 검색·필터·정렬, 초안 작성·미리보기·저장·제출, 브랜치 기준 선택,
인시던트·교훈 탐색을 수행할 수 있다. 개요 지표에서 관련 작업으로 이동한다.
모바일과 키보드로 동일한 기능을 사용하고, 로딩·오류·재시도 피드백을 받는다.
검증에서 stale 저장의 덮어쓰기와 최종 경로·화면 불일치는 0건,
반복 클릭당 mutation은 1회, 보호 메타데이터 변경은 0건이어야 한다.

## Constraints
- Python 표준 라이브러리, 빌드 없는 JavaScript, 소스 파일별 12 KiB 제한을 유지한다.
- 한국어/영어, 기존 밝은/어두운 테마, 모바일, 키보드를 지원한다.
- 승인 엔드포인트를 추가하지 않고 승인·등급·게이트 상태를 편집하지 않는다.
- make check와 AC별 API·실제 렌더링 검증을 완료한다.

## Out of scope
- 드래그로 단계나 승인 상태 변경, 자동 승인, 배포·병합.
- 프레임워크 전환, 외부 계정 연결, 제품 실행의 새 의존성.
- 보호 경로(policy/**, Hook 설정, CI 워크플로) 변경.

## Open questions
없음. 보드 조건은 URL에 보존하며 초안은 명시적으로 저장한다.
구현 시작 전 intent → spec → plan의 사람 승인 절차가 필요하다.
