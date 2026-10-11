---
id: W-0005
type: spec
status: accepted
intent: ./intent.md
skills_applied: []
risk_tier: T2
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: architect
    at: 2026-10-11
---

# Interactive frontend workflow — Spec

## Requirements
- R1 보드에 ID·제목·담당자 검색, 단계·위험 등급·승인 대기·검증 문제 필터,
  ID·제목·위험 등급 정렬, 보드/목록 전환, 결과 수와 초기화를 제공한다.
- R2 보드 조건을 hash URL query에 보존하고 공유·새로고침·뒤로/앞으로 이동·언어
  전환에서 복원한다. 개요의 단계와 관련 지표를 해당 필터로 연결한다.
- R3 draft 상세에서 본문 편집·안전한 Markdown 미리보기·저장을 제공한다.
  intent의 sources 종류·참조를 추가·수정·제거한다. 저장 전 탭 이동에는 입력을
  유지하고 화면 이탈에는 경고한다. 충돌 시 자동 덮어쓰기하지 않는다.
- R4 편집 API는 draft의 body와 intent sources만 수정한다. 현재 파일의 revision을
  확인하고 stale 저장은 409로 거절한다. 기타 메타데이터는 보존한다.
- R5 상세 탭에 tab/tabpanel 연결, roving tabindex, 좌우 방향키·Home·End 조작을
  제공하고 새로고침·언어 변경에서 선택 상태를 복원한다.
- R6 브랜치 기준 ref 입력·실행, 인시던트 검색·상태 필터, 교훈 검색·상태·발견
  주체 필터를 제공한다. 검색 결과 없음과 저장소에 항목 없음은 구분한다.
- R7 로딩·오류·재시도를 표시하며 이전 요청이 최신 화면·제목을 덮지 못하게 한다.
  생성·저장·제출 중 반복 실행을 막고 실패 후 입력과 조작을 복구한다.
- R8 새 문자열을 한국어/영어로 제공하고 375px/데스크톱, 밝은/어두운 테마,
  키보드, reduced-motion에서 조작 가능한 UI를 제공한다.

## Design
기존 vanilla JavaScript를 유지한다. board.js, editor.js, 인터랙션 스타일·번역을
별도 파일로 나누어 크기 제한을 지킨다.

- app.js: query를 분리한 라우트 매칭, 요청 세대·화면 cleanup, 로딩·재시도,
  진행 중 mutation 잠금. intro-live 등 비동기 하위 갱신도 현재 화면인지 확인한다.
- board.js: 한 번 받은 데이터를 검색·필터·정렬한다. 검색마다 API를 호출하지
  않는다. URL 조건과 브라우저 탐색을 동기화하고 새로고침은 조건을 유지한다.
- detail.js/editor.js: 탭 선택과 편집 버퍼를 유지한다. 미리보기는 기존 escape
  기반 Markdown 렌더러를 사용한다. 제출 전 변경분 저장을 요구한다. 충돌 시
  입력을 보존하고 최신 파일 다시 불러오기 선택을 제공한다.
- api.py: 상세 아티팩트에 현재 파일 bytes의 SHA-256 revision을 포함한다.
- POST /api/work/W-NNNN/draft: {stage, body, sources?, revision}을 받는다.
  draft 상태·revision·필드 타입·크기·sources 형식을 검증한다. intent 외 sources,
  잘못된 stage, 보호 메타데이터 입력을 거절한다. {path, status, revision}을 반환한다.
  본문은 frontmatter.render로 직렬화하여 본문의 frontmatter처럼 보이는 텍스트가
  승인·상태를 바꾸지 못하게 한다.
- server.py: 기존 Host·JSON·X-SDLC·payload 크기 제한을 적용한다. root 내 HTTP
  mutation을 공통 잠금으로 직렬화하여 ID 생성과 저장/제출의 경합을 방지한다.
  저장은 같은 디렉터리의 임시 파일과 replace를 사용한다. 외부 편집은 revision으로
  감지하며 외부 편집기와의 완전한 프로세스 간 트랜잭션은 제공하지 않는다.

새 작업 → 본문과 근거 작성 → 저장 → 제출은 앱에서 완료한다. accepted 전환은
기존 사람 CLI 승인으로 유지한다.

## Acceptance criteria
- AC-1 보드 검색·조합 필터·정렬·보기 전환이 샘플 데이터 결과와 일치한다.
  초기화·결과 없음·URL 복원·개요에서 필터로 이동을 검증한다 (R1, R2).
- AC-2 앱에서 새 intent의 본문과 sources를 편집·미리보기·저장하고, 실제 파일과
  재조회 내용이 일치한다. 유효한 초안은 제출된다 (R3).
- AC-3 API가 비초안·보호 필드·잘못된 stage/sources·누락된 JSON/X-SDLC·외부
  Host를 거절하고 파일을 변경하지 않는다 (R4).
- AC-4 stale 저장은 409이고 최신 파일을 보존한다. 같은 revision의 동시 HTTP
  저장은 한 번만 성공한다. HTML/script와 frontmatter처럼 보이는 본문이
  실행되거나 메타데이터를 변경하지 않는다 (R3, R4).
- AC-5 탭은 클릭·방향키·Home·End로 선택되며 ARIA와 tabindex가 일치한다.
  저장 전 탭 이동·화면 이탈·저장 후 버퍼 처리가 입력을 보호한다 (R3, R5).
- AC-6 브랜치 ref 변경과 잘못된 ref 오류 복구, 인시던트·교훈 검색과 필터가
  실제 API 결과에 맞게 동작한다 (R6).
- AC-7 지연 응답 중 이동해도 최종 화면·제목은 최신 경로와 일치한다. 반복 클릭은
  한 POST만 전송하며 실패 후 입력 유지와 재시도가 가능하다 (R7).
- AC-8 ko/en, 375px/데스크톱, light/dark에서 실제 렌더링을 확인하고 키보드
  초점·label·reduced-motion을 검증한다. make check가 통과한다 (R8).

## Security & compliance notes
로컬 쓰기 보호를 유지한다. 초안 본문과 근거 외 frontmatter는 보존한다.
사용자 입력은 HTML 삽입 전 escape한다. 승인 API와 게이트를 우회하는 칸반 이동은
제공하지 않는다. 제품 저장소의 승인 기록을 테스트 중 변경하지 않는다.

## Alternatives considered
- 프레임워크 도입: 현 앱에 필요하지 않은 빌드·의존성 비용이 생긴다.
- 전체 frontmatter 편집: 승인·등급·상태 변경 경로를 만들므로 제외한다.
- 자동 저장: 제출 시점·충돌 처리를 불명확하게 하므로 명시적 저장을 사용한다.
- 드래그 칸반 이동: 칸이 실제 게이트 상태를 나타내므로 기존 stage/submit을 사용한다.
