/* View: plain-language comparison of the traditional SDLC and the AI-native SDLC, tied to live data. */
(() => {
  const { esc, api, route, setTitle } = App;

  const GLANCE = [
    ["누가 일하나", "단계마다 다른 사람 — PM, 아키텍트, 엔지니어, QA, 릴리스 팀", "에이전트가 만들고, 사람은 정해진 지점에서 결정한다"],
    ["무엇으로 넘기나", "문서, 티켓, 회의, 사인오프", "Git에 커밋된 파일 하나 — 다음 단계는 그 파일을 읽고 시작한다"],
    ["통제는 언제 일어나나", "일이 끝난 뒤, 리뷰와 위원회에서", "에이전트가 행동하는 그 순간에 — Hook과 CI가 막는다"],
  ];

  const STAGES = [
    ["계획", "워크숍과 회의로 요구사항을 모아 PRD를 쓴다", "에이전트가 티켓·지표에서 근거를 모아 intent.md 초안을 쓴다", "근거가 붙은 한 파일"],
    ["설계", "분석가가 명세를 쓰고 설계 위원회를 기다린다", "요구사항과 설계를 한 세션에서 spec.md로 정리한다", "기다림 대신 한 세션"],
    ["구현", "사람이 코드와 테스트를 쓰고, 문서는 나중에", "승인된 plan.md대로 에이전트가 코드와 테스트를 만든다", "계획 승인 전엔 코드 없음"],
    ["테스트", "단계가 끝날 때 QA가 한 번에 검증한다", "평가가 구현 내내 돈다. 테스트를 지우면 CI가 멈춘다", "끝이 아니라 내내"],
    ["배포", "사람이 모든 줄을 읽고, 주간 위원회가 승인한다", "위험 등급만큼만 사람이 본다. 나머지는 자동 게이트", "주의를 위험에 집중"],
    ["운영", "사람이 대시보드를 보다가 버그를 적는다", "기준을 벗어나면 에이전트가 진단해 새 의도를 연다", "다시 계획으로 도는 루프"],
  ];

  // who does each job: P = person, A = agent, G = automatic gate, H = human gate
  const WHO = [
    ["요구사항 정리", "P", "A"], ["요구사항 승인", "P", "H"], ["설계 문서", "P", "A"], ["설계 승인", "P", "H"],
    ["코드와 테스트", "P", "A"], ["테스트가 약해지지 않았나", "P", "G"], ["코드 리뷰", "P", "A·H"],
    ["배포 승인", "P", "G·H"], ["운영 감시", "P", "A"], ["후속 작업 결정", "P", "H"],
  ];
  const BADGE = {
    P: ["사람", "who-p"], A: ["에이전트", "who-a"], G: ["자동 게이트", "who-g"], H: ["사람 게이트", "who-h"],
  };
  const badges = (code) => code.split("·").map((c) => `<span class="who ${BADGE[c][1]}">${BADGE[c][0]}</span>`).join("");

  const FAQ = [
    ["그럼 사람은 무엇을 하나요?", "판단이 필요한 곳에서 결정합니다. 의도를 받아들일지, 설계와 계획을 승인할지, 위험한 변경을 통과시킬지. 처음부터 문서를 쓰는 대신 에이전트가 표시해 둔 것을 검토합니다."],
    ["에이전트가 스스로 승인하면요?", "못 합니다. 승인 기록은 사람 이름만 받고, Hook이 에이전트의 승인 명령과 승인 필드 편집을 막고, 이 앱에는 승인 버튼 자체가 없습니다. 승인은 사람이 자기 터미널에서 합니다."],
    ["리뷰가 사라지는 건가요?", "아니요, 옮겨 갑니다. 문서와 일반 코드는 자동 게이트와 에이전트 리뷰로 충분하고, 인증·결제·규제처럼 위험한 변경에는 사람이 더 깊게(T3는 두 명) 봅니다."],
  ];

  route(/^\/intro$/, "intro", async (view) => {
    setTitle("Introduction", "전통 SDLC와 무엇이 다른가");
    view.innerHTML = `
      <p class="intro-lede">코드를 쓰는 일은 에이전트 덕분에 몇 시간으로 줄었습니다. 그런데 그 앞뒤의 계획·리뷰·배포가 예전 속도 그대로면 전체는 빨라지지 않습니다. AI-native SDLC는 <b>일은 에이전트가, 결정은 사람이, 규칙은 도구가</b> 맡도록 과정을 다시 짭니다.</p>

      <div class="glance" role="table" aria-label="한눈에 보는 차이">
        <div class="glance-head" role="row"><span role="columnheader"></span><span role="columnheader" class="g-old">전통 SDLC</span><span role="columnheader" class="g-new">AI-native SDLC</span></div>
        ${GLANCE.map(([q, o, n]) => `<div class="glance-row" role="row"><span role="rowheader">${esc(q)}</span><span role="cell" class="g-old">${esc(o)}</span><span role="cell" class="g-new">${esc(n)}</span></div>`).join("")}
      </div>

      <div class="section"><h2>단계마다 무엇이 달라지나</h2>
        <ol class="stage-list">${STAGES.map(([s, o, n, diff], i) => `<li>
          <span class="st-name"><span class="st-no">${i + 1}</span>${esc(s)}</span>
          <span class="st-old">${esc(o)}</span>
          <span class="st-arrow" aria-hidden="true">→</span>
          <span class="st-new">${esc(n)}</span>
          <span class="chip ok st-diff">${esc(diff)}</span>
        </li>`).join("")}</ol>
      </div>

      <div class="section"><h2>누가 무엇을 하나</h2>
        <div class="table-wrap"><table class="who-table"><thead><tr><th>일</th><th>전통 SDLC</th><th>AI-native SDLC</th></tr></thead><tbody>
          ${WHO.map(([job, o, n]) => `<tr><td>${esc(job)}</td><td>${badges(o)}</td><td>${badges(n)}</td></tr>`).join("")}
        </tbody></table></div>
        <p class="fine">사람 게이트 = 사람이 승인해야 다음 단계가 시작되는 지점. 자동 게이트 = CI와 Hook이 규칙으로 판정하는 지점.</p>
      </div>

      <div class="section"><h2>이 저장소에서 직접 보기</h2>
        <div class="grid live" id="intro-live"><div class="empty">불러오는 중…</div></div>
      </div>

      <div class="section"><h2>자주 묻는 질문</h2>
        ${FAQ.map(([q, a]) => `<details class="faq"><summary>${esc(q)}</summary><p>${esc(a)}</p></details>`).join("")}
      </div>

      <p class="fine" style="margin-top:28px">더 자세한 설명과 실제 저장소에서 잰 수치는 <a href="/about" target="_blank" rel="noopener">소개 사이트</a>에 있습니다.</p>`;

    try {
      const [o, items] = await Promise.all([api("/api/overview"), api("/api/work")]);
      const t3 = items.find((i) => i.tier === "T3" && i.awaiting.length);
      const done = items.find((i) => i.stage === "done");
      const loop = items.find((i) => i.origin === "maintain-loop");
      const cards = [
        o.waiting.length && [`#/`, `사람의 게이트 ${o.waiting.length}곳에서 멈춰 있음`, "에이전트는 제출까지만 합니다. 개요 화면에서 기다리는 결정과 실행할 명령을 확인하세요."],
        t3 && [`#/work/${t3.id}`, `${t3.id}: 위험한 변경은 사람 둘`, `${t3.title} — T3라서 ${t3.awaiting[0]}.md에 승인 ${t3.chain[t3.awaiting[0]].needed}건이 필요하고 지금 ${t3.chain[t3.awaiting[0]].approvals.length}건입니다.`],
        done && [`#/work/${done.id}`, `${done.id}: 문서 대신 커밋의 연쇄`, "감사 기록 탭에서 누가 초안을 쓰고 누가 승인했는지 git 기록으로 봅니다."],
        loop && [`#/work/${loop.id}`, `${loop.id}: 운영이 다시 계획으로`, "기준을 벗어난 지표가 인시던트와 새 의도를 열었습니다. 사람이 받아들이면 루프가 한 바퀴 돕니다."],
        o.gate_wait_hours.count && [`#/`, `게이트 대기 중앙값 ${o.gate_wait_hours.median}시간`, `승인 ${o.gate_wait_hours.count}건의 git 기록에서 잰 값입니다. 사람의 주의가 머무는 시간입니다.`],
      ].filter(Boolean);
      document.getElementById("intro-live").innerHTML = cards.length
        ? cards.map(([href, h, p]) => `<a class="card live-card" href="${href}"><b>${esc(h)}</b><span>${esc(p)}</span><span class="go">열기 →</span></a>`).join("")
        : `<div class="empty">아직 작업이 없습니다. <b>새 작업</b>으로 첫 의도를 만들어 보세요.</div>`;
    } catch (err) {
      document.getElementById("intro-live").innerHTML = `<div class="empty">데이터를 불러오지 못했습니다: ${esc(err.message)}</div>`;
    }
  });
})();
