# Navigation feature research — 2026-10-11

사용자 요청: `github 및 web search을 통해서 추가할 기능들을 추가해 줘`.
GitHub API로 Plane의 실제 view/favorite store를 읽고 공식 웹 문서를 비교했다.
외부 코드는 복사하지 않고 현재 vanilla JavaScript 앱에 맞게 구현한다.

| 1차 자료 | 관찰 | 이 앱에 적용 |
|---|---|---|
| [GitHub Projects: managing views](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/managing-your-views) | 필터·정렬을 저장하고 변경 표시, 이름 변경·삭제를 제공 | 보드 조건의 명시적 저장·갱신과 URL 공유 |
| [Plane: views](https://docs.plane.so/core-concepts/views) | 보기에는 필터·레이아웃·정렬이 포함되며 원본 작업을 바꾸지 않음 | 개인 보기로 반복적인 탐색 재사용 |
| [Plane project view store](https://github.com/makeplane/plane/blob/bab49bb978ccb56af1d78dec6c6d54dfe8d03c1c/apps/web/store/project-view.store.ts) | createView/updateView/deleteView와 필터 정규화 | 보기 입력 검증 및 CRUD |
| [Plane favorite store](https://github.com/makeplane/plane/blob/bab49bb978ccb56af1d78dec6c6d54dfe8d03c1c/apps/web/store/favorite.store.ts) | workspace별 즐겨찾기와 제거 동작 | 저장소별 개인 즐겨찾기·빠른 이동 |
| [Linear: favorites](https://linear.app/docs/favorites) | 개인 바로가기를 별표로 토글하고 command menu에서 접근 | 카드/상세 별표와 빠른 이동에서 즐겨찾기 우선 표시 |
| [GitHub Projects: filtering](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/filtering-projects) | 필드 조건, 따옴표, 조건 결합, 쉼표 값, 부정 | stage/tier/owner/id/is 검색식과 예시 도움말 |

## Selection and tradeoffs
기존 승인된 W-0005의 탐색 기능을 확장한다. 개인 설정은 현재 브라우저와 저장소에
귀속되며 다른 기기·사람과 공유되지 않는다. 링크는 보기 이름 대신 실제 조건을
포함하여 개인 저장 데이터 없이도 열 수 있게 한다. 저장소를 이동하면 workspace_id가
달라지므로 개인 설정도 별도 공간으로 시작한다.

작업 관리 제품의 날짜·담당자 할당·일괄 단계 이동은 이 저장소의 승인 게이트와
상태 모델에 맞지 않아 추가하지 않는다. 최근 작업에는 본문을 저장하지 않고 ID만
보관하며 최신 API 결과로 제목을 표시한다. 원본 아티팩트는 변경하지 않는다.
