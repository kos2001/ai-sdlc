/* View: one work item — the chain, its audit trail from git, acceptance-criteria coverage. */
(() => {
  const { $, esc, api, toast, route, setTitle, statusChip, tierChip, cmdBlock, markdown, when, STAGE_KO } = App;
  const KINDS = ["intent", "spec", "plan"];
  const isAgent = (who) => /claude|anthropic|\[bot\]/i.test(who || "");

  route(/^\/work\/(W-\d{4,})$/, "board", async (view, m) => {
    const w = await api(`/api/work/${m[1]}`);
    setTitle(`${w.id} · ${STAGE_KO[w.stage]}`, w.title);
    view.innerHTML = `
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,max-content));gap:8px">
        ${tierChip(w.tier)}<span class="chip">담당 ${esc(w.owner || "—")}</span>${w.origin === "maintain-loop" ? '<span class="chip gate">운영에서 온 의도</span>' : ""}
      </div>
      <div class="chain" style="margin-top:16px">${KINDS.map((k, i) => link(w, k, i)).join("")}</div>
      ${w.trace.criteria.length ? `<div class="section"><h2>수락 기준 추적</h2><div class="card" style="display:flex;gap:8px;flex-wrap:wrap">
        ${w.trace.criteria.map((ac) => `<span class="chip ${w.trace.covered.includes(ac) ? "ok" : "bad"}">${w.trace.covered.includes(ac) ? "✓" : "✗"} ${esc(w.id)}:${esc(ac)}</span>`).join("")}
        <span class="fine" style="align-self:center">태그된 테스트가 없는 기준이 남아 있으면 plan을 완료로 바꿀 수 없습니다.</span></div></div>` : ""}
      <div class="tabs" role="tablist">
        <button role="tab" type="button" data-tab="audit" aria-selected="true">감사 기록</button>
        ${KINDS.filter((k) => w.chain[k]).map((k) => `<button role="tab" type="button" data-tab="${k}" aria-selected="false">${k}.md</button>`).join("")}
      </div>
      <div id="tab-body"></div>`;
    const show = (tab) => {
      view.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
      $("#tab-body").innerHTML = tab === "audit" ? audit(w) : doc(w.chain[tab]);
    };
    view.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => show(b.dataset.tab)));
    view.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => act(w, b)));
    show("audit");
  });

  function link(w, kind, i) {
    const a = w.chain[kind];
    if (!a) {
      const prev = w.chain[KINDS[i - 1]];
      const ready = prev && ["accepted", "done"].includes(prev.status);
      return `<div class="link missing"><h3><span>${kind}.md</span></h3>
        <p style="margin:0;font-size:13px">${ready ? "이전 단계가 승인됐습니다. 초안을 만들 수 있습니다." : `${KINDS[i - 1]}.md가 승인된 뒤에 시작합니다.`}</p>
        ${ready ? `<button class="btn small primary" type="button" data-act="stage" data-kind="${kind}">${kind}.md 초안 만들기</button>` : ""}</div>`;
    }
    return `<div class="link"><h3><span>${kind}.md</span>${statusChip(a.status)}</h3>
      <div class="fine">승인 ${a.approvals.length} / ${a.needed}${a.tier ? ` · ${esc(a.tier)}` : ""}</div>
      ${a.approvals.length ? `<ul>${a.approvals.map((p) => `<li>${esc(p.by)} <span class="muted">· ${esc(p.role)} · ${esc(p.at)}</span></li>`).join("")}</ul>` : ""}
      ${a.issues.length ? `<ul style="color:var(--bad)">${a.issues.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
      ${a.status === "draft" ? `<button class="btn small primary" type="button" data-act="submit" data-kind="${kind}">제출 (draft → proposed)</button>` : ""}
      ${a.status === "proposed" ? `<div class="fine">사람이 터미널에서 결정:</div>${cmdBlock(w.id, kind)}` : ""}</div>`;
  }

  function audit(w) {
    const rows = KINDS.filter((k) => w.chain[k]).flatMap((k) => w.chain[k].history.map((h) => ({ ...h, kind: k })));
    rows.sort((a, b) => (a.at ? Date.parse(a.at) : Infinity) - (b.at ? Date.parse(b.at) : Infinity));
    if (!rows.length) return `<div class="empty" style="margin-top:16px">아직 커밋된 기록이 없습니다.</div>`;
    return `<p class="fine" style="margin:14px 0 0">git 기록에서 다시 만든 상태 변화입니다. 초록은 에이전트, 주황은 사람의 커밋입니다.</p>
      <ol class="timeline">${rows.map((h) => `<li>
        <span class="when">${esc(when(h.at))}</span>
        <span class="mark ${h.author ? (isAgent(h.author) ? "agent" : "human") : ""}" aria-hidden="true"></span>
        <div class="what"><b>${esc(h.kind)}.md</b> → ${statusChip(h.status)} <span class="who">${h.author ? `${esc(h.author)} · <code>${esc(h.commit)}</code> · ${esc(h.subject)}` : "작업 트리에 커밋되지 않은 변경"}</span></div>
      </li>`).join("")}</ol>`;
  }

  function doc(a) {
    const front = Object.entries(a.meta).map(([k, v]) => `${k}: ${Array.isArray(v) ? JSON.stringify(v) : v}`).join("\n");
    return `<div class="doc"><div class="front">${esc(front)}</div>${markdown(a.body)}<p class="fine"><code>${esc(a.path)}</code> — 편집은 에디터나 에이전트로. 이 앱은 읽고 게이트로 보내기만 합니다.</p></div>`;
  }

  async function act(w, btn) {
    btn.disabled = true;
    const kind = btn.dataset.kind;
    try {
      if (btn.dataset.act === "stage") {
        const r = await api(`/api/work/${w.id}/stage`, { stage: kind });
        toast(`${r.path} 초안을 만들었습니다. 내용을 채운 뒤 제출하세요.`);
      } else {
        await api(`/api/work/${w.id}/submit`, { stage: kind });
        toast(`${w.id} ${kind}.md를 제출했습니다. 이제 사람의 게이트입니다.`);
      }
      App.render();
    } catch (err) {
      toast(`하지 못했습니다: ${err.message}`);
      btn.disabled = false;
    }
  }
})();
