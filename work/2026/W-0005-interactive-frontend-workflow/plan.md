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
