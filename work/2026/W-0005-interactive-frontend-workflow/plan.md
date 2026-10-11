---
id: W-0005
type: plan
status: done
spec: ./spec.md
approvals:
  - by: kos2001 <62705131+kos2001@users.noreply.github.com>
    role: tech-lead
    at: 2026-10-11
---

# Interactive frontend workflow — Plan

## Steps
- [x] intent → spec → plan을 순서대로 제출하고 사람의 승인을 확인한다.
- [x] 라우트 query, 요청 세대·cleanup, 로딩·재시도, mutation 중복 방지를 구현한다.
- [x] 보드 탐색·URL 복원과 개요 지표에서 필터로 이동을 구현한다.
- [x] 상세 revision 및 draft 편집 API, 입력 검증·잠금·원자적 저장을 구현한다.
- [x] 초안 본문·sources 편집, 미리보기, 저장·충돌·이탈 보호를 구현한다.
- [x] 상세 탭의 ARIA·키보드 탐색과 선택 상태 복원을 구현한다.
- [x] 브랜치 기준 입력과 인시던트·교훈 검색/필터를 구현한다.
- [x] 번역·반응형·테마·reduced-motion 스타일을 적용한다.
- [x] AC 태그가 있는 API·브라우저 검증과 make check를 완료한다.
- [x] README의 화면·draft API·실행/검증 안내를 한국어/영어로 갱신한다.

## Test strategy
구현 리뷰에서 발견한 생성 API의 owner 줄바꿈 입력도 같은 변경에서 거절한다.
템플릿의 frontmatter로 들어가는 입력이 승인 메타데이터를 주입하지 못하도록
필드 타입·길이·단일 행을 검사하고 AC-3 API 회귀 검증에 포함한다.

모든 새 검증에 W-0005:AC-n 태그를 붙이며 기존 테스트를 약화하지 않는다.

| 기준 | 증거 |
|---|---|
| AC-1 | 샘플 보드의 검색·조합 필터·정렬·보기, URL 직접 이동/새로고침/뒤로 가기, 개요 링크 UI 검증 |
| AC-2 | 임시 demo의 생성→편집→저장→재조회→제출 API 및 UI 흐름, 실제 저장 파일 검사 |
| AC-3 | 비초안·보호 필드·입력·Host/header 거절과 파일 불변 unittest |
| AC-4 | 동일 revision 동시 저장, 외부 수정 후 stale 저장, 악성 본문 직렬화·미리보기 회귀 검증 |
| AC-5 | 키보드 탭 이동·ARIA·tabindex, 입력 유지·이탈·저장 UI 검증 |
| AC-6 | 유효/무효 ref, 인시던트/교훈 조합 필터·결과 없음 UI 검증 |
| AC-7 | 지연·실패 응답 중 최신 화면, POST 수, 실패 후 입력·버튼 복구 검사 |
| AC-8 | 375px/데스크톱·ko/en·light/dark 렌더링과 초점·label·reduced-motion, make check |

임시 demo 저장소를 사용한다. 브라우저 검증 의존성은 개발에만 두며 제품 실행에는
추가하지 않는다. 최종 명령 출력과 실제 렌더링으로 각 AC의 완료를 확인한다.

## Rollout
사람의 plan 승인 후 구현한다. 정적 자산과 API를 함께 변경하며 기존 API와 호환되는
draft 엔드포인트를 추가한다. demo에서 검증한 다음 실제 저장소의 조회 화면을
확인한다. 배포·병합은 범위 밖이다. 파일 손실·보호 필드 변경·화면 경합이 있으면
릴리스하지 않고 수정한다.

## Control bands
운영 서비스가 없는 로컬 앱이므로 bands 파일을 임의로 추가하지 않는다.
검증 불변식: 보호 메타데이터 변경 0건, stale 덮어쓰기 0건, 반복 클릭당 mutation
1회, 최종 경로·화면 불일치 0건, 새 문자열 번역 누락 0건.

## Verification evidence
- 사람 승인 근거: 사용자가 이 대화에서 `승인할께`라고 명시했고, 기존 CLI로 각 단계의 승인 기록을 남겼다.
- `make check`: 100 Python tests passed, artifact and lesson checks passed.
- `scripts/check_frontend.py`: 7 browser regression groups passed; 375px/1440px × ko/en × light/dark screenshots rendered and inspected.
- `python3 -m sdlc trace W-0005 --strict`: 8/8 criteria traced.
- Browser tests: `tests/frontend.js`; API tests: `tests/test_drafts.py`.
- 실 저장소 조회: http://127.0.0.1:8791/ (최종 읽기 검증).

## Follow-up interaction refinement
사용자가 같은 프론트엔드 개선을 다시 요청하여, 승인된 R1/R2/R3/R5/R8의
탐색·편집 동작을 확장한다. API와 게이트 상태는 변경하지 않는다.

- 작업/화면 빠른 이동 dialog: Ctrl/⌘ K, 검색, 방향키·Enter·Escape, 오류 재시도.
- 보드/목록의 읽기 전용 작업 미리보기: 체인·현재 본문·추적 요약, 상세/편집 연결.
- 보드 조건을 상세 URL에 전달하여 상세에서 돌아올 때 같은 필터·정렬·보기 복원.
- 초안 Markdown 서식 도구와 Ctrl/⌘ S 저장: 기존 변경 버퍼·충돌·중복 저장 보호 사용.

AC-1/AC-5/AC-7/AC-8에 실제 브라우저 검증을 추가한다. 새 dialog는 작은 화면과
두 언어/테마에서 검증하고, 미저장 편집 이탈과 지연 응답을 회귀 검증한다.

### Follow-up evidence
- [x] 빠른 이동의 검색·방향키·Enter·Escape와 오류 재시도를 검증했다.
- [x] 미리보기 닫기의 초점 복귀·본문 키보드 초점·지연 응답 격리, 초안 편집 연결과 보드 조건 복원을 검증했다.
- [x] 서식 적용의 선택 범위, Ctrl/⌘ S 중복 저장 보호, 빠른 이동에서 미저장 이탈 거절을 검증했다.
- [x] `make check`: 100 tests passed, artifacts and 18 lesson controls validated.
- [x] 브라우저 11개 회귀 검증 그룹: 375×812/1440×1000, ko/en, light/dark, reduced-motion 통과.
- [x] 실 서버 읽기 검증: 데스크톱 미리보기·모바일 Meta-K 검색/상세 이동, POST 0건·JS 오류 0건.
- [x] UI 캡처 검토 후 저장 버튼의 근거 입력 가림을 수정하고 회귀 검증을 추가했다.
- [x] `trace W-0005 --strict`: 8/8; JS syntax and source sizes, `git diff --check` passed.

후속 검증 로그: `/private/tmp/ai-sdlc-interaction-check.log`,
`/private/tmp/ai-sdlc-interaction-unit.log`, `/private/tmp/ai-sdlc-interaction-live.log`.
스크린샷: `/private/tmp/ai-sdlc-frontend-qa/` (미리보기·빠른 이동·편집 화면).

## Research-driven navigation refinement
사용자가 GitHub 및 웹 검색을 통해 추가 기능을 구현하도록 요청했다.
`research.md`의 1차 자료에 근거하여 기존 보드 탐색(R1/R2), 키보드 이동(R5),
오류 복구와 반응형(R7/R8)을 다음과 같이 확장한다.

- 보드 검색·필터·정렬·보기 조합을 이름 있는 보기로 저장, 열기, 갱신, 이름 변경,
  삭제, 링크 복사한다. 변경 중 표시와 명시적 저장을 제공한다.
- 보드/목록/상세에서 작업 즐겨찾기, 최근 본 작업과 저장된 보기의 빠른 이동을 제공한다.
- 필드 검색은 stage/tier/owner/id/is, 따옴표, 쉼표 OR, 조건 간 AND, 부정을 지원한다.
  잘못된 알려진 값/따옴표는 오류와 도움말을 표시한다. 알 수 없는 접두사는 일반 텍스트다.
- 개인 데이터는 workspace_id별 localStorage에 둔다. overview에 root의 SHA-256
  식별자를 추가하여 같은 이름의 다른 저장소에서도 설정을 격리한다. 경로 자체는 보내지 않는다.
- 저장소 접근 실패는 현재 탭 메모리로 복구하고 안내한다. 손상된 데이터는 검증하며
  다른 탭의 변경을 반영한다. 아티팩트·승인 메타데이터·쓰기 API는 변경하지 않는다.

검증: AC-1은 검색·보기 CRUD/URL 복원·즐겨찾기·최근 작업·저장소 격리,
AC-5는 키보드·초점·미저장 편집 보호, AC-7은 손상/차단 storage·다른 탭 동기화,
AC-8은 ko/en·375px/1440px·light/dark 렌더링을 확인한다. 기존 make check와
브라우저 회귀 검증을 유지하고 독립 브라우저 시나리오를 추가한다.

### Research refinement evidence
- [x] GitHub API로 Plane의 view/favorite store를 읽고, 공식 GitHub/Plane/Linear 문서를 비교해 `research.md`에 근거를 기록했다.
- [x] 보기 CRUD·변경 조건 표시·이름 변경 중 입력 유지·새로고침·개인 ID 없는 공유 URL을 검증했다.
- [x] 보드/목록/상세 즐겨찾기와 최근 작업, 빠른 이동의 개인 바로가기와 저장된 보기를 검증했다.
- [x] 필드 검색·문구·AND/쉼표 OR·부정·입력 오류와 일반 아포스트로피 처리를 검증했다.
- [x] 같은 이름의 저장소 격리, 손상된 설정, 읽기 차단/쓰기 용량 초과, 즐겨찾기 상한을 검증했다.
- [x] 다른 탭의 설정 변경 및 저장된 보기로 이탈 시 편집 중 입력이 유지됨을 검증했다.
- [x] 기존 브라우저 11개 그룹 + 추가 7개 그룹 통과, ko/en·375×812/1440×1000·light/dark 캡처 검토.
- [x] 개인 탐색에서 POST 0건, 임시 저장소의 모든 기존 아티팩트 내용 불변.
- [x] 실 서버에서 필드 검색·별표·보기 저장/재로딩·빠른 이동·모바일 폭, JS 오류 0건·POST 0건 확인.
- [x] `make check`: 101 tests passed; artifact and lesson controls validated. `trace W-0005 --strict`: 8/8.
- [x] 사용자의 한/영 README 요청에 따라 언어 전환·문서 링크를 명시하고, 두 버전의 기능·API·브라우저 검증 안내를 함께 갱신했다.

로그: `/private/tmp/ai-sdlc-discovery-check.log`, `/private/tmp/ai-sdlc-discovery-unit.log`,
`/private/tmp/ai-sdlc-discovery-live.log`. 검증: `tests/discovery.js`,
`tests/test_server.py::test_workspace_identity_is_stable_and_separates_same_named_roots`.
