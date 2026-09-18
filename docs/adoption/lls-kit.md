# lls-kit에 ai-sdlc 적용 검토

| 항목 | 내용 |
|---|---|
| 대상 | `kos2001/lls-kit` (3GPP 링크레벨 시뮬레이터, 약 25k 라인, PR 25건) |
| 방법 | 스크래치 클론에 `sdlc/`·템플릿·lls-kit용 정책을 설치하고 PR #16–#25에 게이트를 재생. 원본 저장소는 건드리지 않음 |
| 결론 | **관리할 수 있다.** 단, lls-kit의 기존 검증 루프(`check.py`, `defects.json`)를 대체하지 않고 그 **앞뒤**(의도·승인·위험 등급·CI)를 채우는 방식이어야 한다 |

## 1. 두 체계가 겹치는 곳과 비는 곳

lls-kit은 이미 AI-native SDLC의 뒷단을 갖고 있다. 앞단과 거버넌스가 비어 있다.

| ai-sdlc Play | lls-kit 현재 | 적용 후 |
|---|---|---|
| 1 Capture intent / 9 Spec / 6 Plan | 없음. PR 본문이 사후 설명 | `work/W-NNNN/{intent,spec,plan}.md`. 결함은 `sources: kind: defect, ref: D16`로 연결 |
| 2 CLAUDE.md, 3 Skills | `CLAUDE.md`(입력 크기), `AGENTS.md`(맡길 일/안 맡길 일) | 유지. `AGENTS.md`의 "맡기면 안 되는 일"을 위험 등급과 Hook으로 **집행** |
| 5 Hooks | 없음 | 규격 표·골든·게이트 파일 편집 차단, 승인 위조 차단 |
| 8 Evals | `check.py` 6개 게이트, 골든 벡터, 동작점 실측 | `check.py`가 그대로 `make check` 역할. `eval-guard`가 `check(...)` 삭제를 잡음 |
| 10 PR review / 11 CI | 사람이 PR 병합. `.github` 없음 | `ci.yml` 추가 (`check.py` 79초 — CI에 충분히 짧음) |
| 4 Feedback / 12 Closing the loop | `defects.json` + `loop.py` (결함→게이트 폐루프, 15건 전부 닫힘) | **lls-kit 방식이 더 강하다.** 그대로 두고 결함이 새 intent를 여는 연결만 추가 |

## 2. 재생 결과 (PR #16–#25)

§4의 lls-kit용 정책으로 계산했다.

| PR | 파일 | 등급 | 등급 원인 | plan-gate |
|---|---|---|---|---|
| #25 | 11 | T2 | 결함 대장 | FAIL |
| #24 | 6 | T3 | `check.py` (테스트 목록 추가뿐) | FAIL |
| #23 | 6 | T2 | 시뮬레이터 | FAIL |
| #22 | 2 | T1 | 기본값 (PNG 삭제) | FAIL |
| #21 | 35 | T3 | 게이트 + `specdata/` | FAIL |
| #20 | 7 | T3 | `check.py` (테스트 목록 추가뿐) + `inputsize.py` | FAIL |
| #19, #17 | 8, 10 | T3 | `specmap.json` (realm) | FAIL |
| #18, #16 | 10, 13 | T3 | 규격 표 (`spec38*.py`, `specdata/`) | FAIL |

읽는 법:
- **plan-gate 전부 FAIL**은 예상대로다. 도입 후에는 T0가 아닌 변경마다 W-NNNN이 필요하다.
- **T3 7건 중 1건(#24)은 오탐**이다. `check.py`가 테스트 파일 목록을 하드코딩해서, 테스트를 추가하기만 해도 게이트 파일이 바뀐다. `check.py`가 `tests/test_*.py`를 스스로 찾게 하면 사라진다 (lls-kit PR #26). *정정: 처음에는 #20도 같은 경우라고 적었지만, #20은 게이트인 `inputsize.py`도 바꿔서 T3이 맞다. 병합된 PR 25건 전체로 다시 재면 T3 18건 → 17건이다.*
- 나머지 T3(#16–#19, #21)는 `AGENTS.md`가 "맡기면 안 된다"고 한 규격 표·realm 변경과 정확히 일치한다. 정책이 문서의 판단을 재현한다.

## 3. 파일럿에서 확인한 것

| 확인 | 결과 |
|---|---|
| `check.py` 공존 | ai-sdlc 설치 후 게이트 7개 중 6개 PASS, 입력 크기 FAIL → **ai-sdlc 쪽을 수정** (`sdlc/cli.py` 12.2KB → `cli.py` 8.8KB + `cli_ops.py` 4.0KB) 후 PASS |
| 테스트 약화 탐지 | 원래 `eval-guard`는 `def test_`만 봐서 `check("리스트를 키우면 좋아진다 …")` 삭제를 **놓침** → 정책 `eval-guard.json`에 `^\s*check\(` 추가 기능을 넣고 탐지 확인 |
| 게이트 순서 | intent가 `proposed`인 동안 spec 제출 차단, plan 없이 `check.py` 수정한 브랜치는 plan-gate FAIL |
| 사람 게이트 | 파일럿은 intent `proposed`에서 멈췄다. 승인은 사람 몫이라 에이전트가 대신하지 않음 |

## 4. lls-kit용 위험 등급 (초안)

`AGENTS.md`의 판단을 그대로 옮겼다. 파일럿 클론의 정책 파일 내용이다.

| 등급 | 경로 | 근거 (AGENTS.md) |
|---|---|---|
| T3 | `specdata/**`, `nrlls/spec38*.py`, `specmap*.json`, `golden/**`, `golden.py`, `check.py`, `loop.py`, `inputsize.py`, `regress.py` | 규격 표 전사, realm 배정, 게이트 자체 — "맡기면 안 되는 일" |
| T2 | `nrlls/**`, `campaigns/**`, 캠페인·규격 도구, `defects.json`, `CLAUDE.md`, `AGENTS.md` | 시뮬레이터 동작 변경, 기고문 가정 → 원문 1:1 대조 필요 |
| T1 | `web/**`, `server*.py`, `report*.py`, `resultservice.py`, `results/**`, `tests/**` | 기계로 판정 가능한 작업 |
| T0 | `docs/**`, `README.md`, `work/**` | 문서 |

## 5. 그대로 쓰면 안 되는 부분 (조정 필요)

1. **사람이 한 명이다.** 커밋 저자 둘(`kos2001`, `고돌이`)은 같은 사람의 두 머신이고, 그중 50건은 Claude 공동 작성이다. 그래서:
   - T3의 "사람 2인 승인"은 성립하지 않는다. lls-kit에서는 **T3 = 1인 승인 + 규격 원문 대조 증거**(조항·버전, `AGENTS.md` "에이전트에게 요구할 증거")로 바꾼다.
   - GitHub는 자기 PR 승인을 허용하지 않으므로 `ci.yml`의 "PR 리뷰 수" 검사는 쓸 수 없다. 승인은 아티팩트(`sdlc approve`)로만 기록하고, CI는 `sdlc validate`로 그것을 확인하게 해야 한다. **ai-sdlc에 "단독 소유자 모드"가 필요하다** (미구현).
   - 두 git ID가 같은 사람이므로 승인자 수를 ID로 세면 1인이 2인으로 보인다.
2. **결함 대장이 우선이다.** ai-sdlc의 incident(control band 위반)보다 `defects.json`의 `detected_by`/`closing_gate` 구조가 lls-kit에 맞다. incident 기능은 쓰지 않고, 새 결함 기록이 intent를 여는 연결만 둔다.
3. **control band = 동작점·baseline 회귀.** 운영 지표 대신 `regress.py`의 baseline 대비 신뢰구간 판정을 band로 쓸 수 있다 (예: 10% BLER 소요 SNR이 baseline ±0.3 dB 이탈 시 intent). 지표 변환기는 아직 없다.

## 6. 도입 순서 제안

| 단계 | 할 일 | 비용 |
|---|---|---|
| 0 | lls-kit에서 `check.py` 테스트 자동 탐색 (W-0001) | 작음. T3 오탐 제거 |
| 1 | `sdlc/`, `templates/`, 정책(§4, `eval-guard.json`), Hook 설정 추가. `CLAUDE.md`에 아티팩트 체인 규칙 한 절 | 작음 |
| 2 | 새 작업부터 W-NNNN 사용. 기존 25 PR은 소급하지 않음 | 작업당 intent/spec/plan 작성 |
| 3 | `.github/workflows/ci.yml` (`check.py` + `sdlc validate/transitions/plan-gate/eval-guard`) | 러너에 numpy·pyyaml·scipy 필요 (lls-kit엔 requirements 파일이 없음) |
| 4 | ai-sdlc 단독 소유자 모드 구현 후 승인 수 검사 연결 | ai-sdlc 쪽 작업 |
