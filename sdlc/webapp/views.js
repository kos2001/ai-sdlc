/* Views: overview, board, branch check, incidents. The work item detail is in detail.js. */
(() => {
  const { esc, api, route, setTitle, statusChip, tierChip, cmdBlock, STAGE_KO } = App;
  const COLUMNS = ["intent", "spec", "plan", "build", "done"];

  route(/^\/$/, "overview", async (view) => {
    setTitle("Overview", "개요");
    const o = await api("/api/overview");
    const active = o.work_items - (o.by_stage.done || 0) - (o.by_stage.rejected || 0);
    const wait = o.gate_wait_hours;
    const tr = o.trace;
    view.innerHTML = `
      <div class="grid tiles">
        <div class="card tile"><div class="lab">진행 중인 작업</div><div class="num">${active}<small>/ ${o.work_items}</small></div><div class="sub">완료 ${o.by_stage.done || 0}건</div></div>
        <div class="card tile ${o.waiting.length ? "warn" : ""}"><div class="lab">사람의 게이트를 기다리는 것</div><div class="num">${o.waiting.length}<small>건</small></div><div class="sub">에이전트는 여기서 멈춘다</div></div>
        <div class="card tile"><div class="lab">게이트 대기 시간 중앙값</div><div class="num">${wait.median ?? "—"}<small>${wait.median != null ? "시간" : ""}</small></div><div class="sub">${wait.count ? `승인 ${wait.count}건 · 최장 ${wait.max}시간 (git 기록)` : "아직 승인 기록 없음"}</div></div>
        <div class="card tile"><div class="lab">수락 기준 추적</div><div class="num">${tr.covered}<small>/ ${tr.criteria}</small></div><div class="sub">W-NNNN:AC-n 태그된 테스트</div></div>
        <div class="card tile ${o.incidents_open ? "warn" : ""}"><div class="lab">열린 인시던트</div><div class="num">${o.incidents_open}<small>건</small></div><div class="sub">control band 이탈</div></div>
      </div>
      <div class="section"><h2>단계별 흐름</h2>
        <div class="pipeline">${COLUMNS.map((c) => `<a class="pipe ${c === "done" ? "done" : ""} ${o.waiting.some((w) => w.kind === c) ? "hot" : ""}" href="#/board" style="text-decoration:none"><b>${o.by_stage[c] || 0}</b><span>${STAGE_KO[c]}</span></a>`).join("")}</div>
      </div>
      <div class="section"><h2>승인 대기 — 사람이 터미널에서 결정</h2>
        <p class="muted" style="margin:0">이 앱에는 승인 버튼이 없습니다. 에이전트도 같은 HTTP를 부를 수 있기 때문입니다. 게이트 결정은 사람이 아래 명령을 자신의 터미널에서 실행합니다.</p>
        ${o.waiting.length ? `<div class="table-wrap"><table><thead><tr><th>작업</th><th>아티팩트</th><th>등급</th><th>승인</th><th>명령</th></tr></thead><tbody>
          ${o.waiting.map((w) => `<tr><td><a href="#/work/${esc(w.id)}">${esc(w.id)}</a> ${esc(w.title)}</td><td><code>${esc(w.kind)}.md</code></td><td>${tierChip(w.tier)}</td><td class="mono">${w.have} / ${w.needed}</td><td>${cmdBlock(w.id, w.kind)}</td></tr>`).join("")}
        </tbody></table></div>` : `<div class="empty">기다리는 게이트가 없습니다.</div>`}
      </div>
      ${o.issues ? `<div class="section"><h2>검증 실패</h2><div class="empty">아티팩트 검증 문제가 ${o.issues}건 있습니다. 작업 보드에서 빨간 표시를 확인하세요. <code>python3 -m sdlc validate</code></div></div>` : ""}`;
  });

  route(/^\/board$/, "board", async (view) => {
    setTitle("Board", "작업 보드");
    const items = await api("/api/work");
    if (!items.length) {
      view.innerHTML = `<div class="empty">아직 작업이 없습니다. 오른쪽 위 <b>새 작업</b>으로 의도 초안을 만드세요.</div>`;
      return;
    }
    const cols = [...COLUMNS, ...(items.some((i) => i.stage === "rejected") ? ["rejected"] : [])];
    view.innerHTML = `<div class="board">${cols.map((c) => {
      const inCol = items.filter((i) => i.stage === c);
      return `<section class="col" aria-label="${STAGE_KO[c]}"><h3><span>${STAGE_KO[c]}</span><span class="mono">${inCol.length}</span></h3>
        ${inCol.map(card).join("") || `<p class="fine" style="padding:0 4px">없음</p>`}</section>`;
    }).join("")}</div>`;
  });

  function card(i) {
    const cur = i.chain[i.stage === "build" || i.stage === "done" ? "plan" : i.stage] || i.chain.intent;
    const t = i.trace, pct = t.criteria.length ? (t.covered.length / t.criteria.length) * 100 : 0;
    return `<a class="wcard" href="#/work/${esc(i.id)}">
      <span class="id">${esc(i.id)}${i.origin === "maintain-loop" ? " · 운영에서 온 의도" : ""}</span>
      <span class="t">${esc(i.title)}</span>
      <span class="meta">${tierChip(i.tier)}${cur ? statusChip(cur.status) : ""}${cur && cur.status === "proposed" ? `<span class="chip">승인 ${cur.approvals.length}/${cur.needed}</span>` : ""}${i.issues ? `<span class="chip bad">검증 ${i.issues}</span>` : ""}</span>
      ${t.criteria.length ? `<span class="fine">수락 기준 ${t.covered.length}/${t.criteria.length}</span><span class="bar"><i style="width:${pct}%"></i></span>` : ""}
    </a>`;
  }

  route(/^\/branch$/, "branch", async (view) => {
    setTitle("Branch", "브랜치 점검");
    const b = await api("/api/branch");
    if (!b.risk) {
      view.innerHTML = `<div class="empty">${esc(b.note || "비교할 기준 브랜치가 없습니다.")}</div>`;
      return;
    }
    const top = b.risk.reasons.filter((r) => r.tier === b.risk.tier);
    view.innerHTML = `
      <p class="muted" style="margin-top:0"><code>${esc(b.branch)}</code> 을 <code>${esc(b.base)}</code> 와 비교합니다. CI가 PR에서 돌리는 것과 같은 검사입니다.</p>
      <div class="grid tiles">
        <div class="card tile ${["T2", "T3"].includes(b.risk.tier) ? "warn" : ""}"><div class="lab">위험 등급</div><div class="num">${esc(b.risk.tier)}</div><div class="sub">사람 리뷰 ${b.risk.human_reviews}명 · 릴리스 ${esc(b.risk.release)}</div></div>
        <div class="card tile"><div class="lab">게이트</div><div class="num">${b.gates.filter((g) => g.ok).length}<small>/ ${b.gates.length} 통과</small></div><div class="sub">plan-gate · eval-guard · transitions</div></div>
      </div>
      <div class="section"><h2>등급을 정한 파일</h2>
        <div class="table-wrap"><table><thead><tr><th>경로</th><th>등급</th><th>규칙</th></tr></thead><tbody>
          ${top.map((r) => `<tr><td><code>${esc(r.path)}</code></td><td>${tierChip(r.tier)}</td><td class="muted">${esc(r.rule)}</td></tr>`).join("")}
        </tbody></table></div></div>
      <div class="section"><h2>게이트</h2><div class="checks">
        ${b.gates.map((g) => `<div class="check">${g.ok ? '<span class="chip ok"><span class="dot"></span>통과</span>' : '<span class="chip bad"><span class="dot"></span>실패</span>'}
          <div><b>${esc(g.name)}</b><ul>${g.messages.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></div></div>`).join("")}
      </div></div>
      ${b.events.length ? `<div class="section"><h2>병합되면 이어질 플레이</h2><div class="checks">${b.events.map((e) => `<div class="check"><span class="chip">${esc(e.event)}</span><div>${esc(e.work_id)} → <b>${esc(e.play)}</b> <span class="muted">(skill: ${esc(e.skill)})</span></div></div>`).join("")}</div></div>` : ""}`;
  });

  route(/^\/incidents$/, "incidents", async (view) => {
    setTitle("Maintain", "인시던트");
    const list = await api("/api/incidents");
    view.innerHTML = list.length ? `<div class="table-wrap"><table><thead><tr><th>인시던트</th><th>상태</th><th>서비스 / band</th><th>감지</th><th>후속 의도</th></tr></thead><tbody>
      ${list.map((i) => {
        const w = (i.followup_intent || "").match(/W-\d{4,}/);
        return `<tr><td class="mono">${esc(i.id)}</td><td>${App.statusChip(i.status)}</td><td>${esc(i.service)} / ${esc(i.band)}</td><td class="mono">${esc(App.when(i.detected_at))}</td><td>${w ? `<a href="#/work/${w[0]}">${w[0]}</a>` : "—"}</td></tr>`;
      }).join("")}</tbody></table></div>` : `<div class="empty">인시던트가 없습니다. control band 위반은 <code>python3 -m sdlc bands open</code> 이 여기에 기록합니다.</div>`;
  });
})();
