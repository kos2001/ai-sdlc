/* View: one work item — the chain, its audit trail from git, acceptance-criteria coverage. */
(() => {
  const { $, esc, t, api, toast, route, setTitle, statusChip, tierChip, cmdBlock, markdown, when, stageName } = App;
  const KINDS = ["intent", "spec", "plan"];
  const HUE = { intent: "plan", spec: "design", plan: "build" };
  const isAgent = (who) => /claude|anthropic|\[bot\]/i.test(who || "");

  route(/^\/work\/(W-\d{4,})$/, "board", async (view, m) => {
    const w = await api(`/api/work/${m[1]}`);
    setTitle(`${w.id} · ${stageName(w.stage)}`, w.title);
    view.innerHTML = `
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,max-content));gap:8px">
        ${tierChip(w.tier)}<span class="chip">${esc(t("wd.owner", { o: w.owner || "—" }))}</span>${w.origin === "maintain-loop" ? `<span class="chip gate">${esc(t("wd.loop"))}</span>` : ""}
      </div>
      <div class="chain" style="margin-top:16px">${KINDS.map((k, i) => link(w, k, i)).join("")}</div>
      ${w.trace.criteria.length ? `<div class="section"><h2>${esc(t("wd.traceH"))}</h2><div class="card" style="display:flex;gap:8px;flex-wrap:wrap">
        ${w.trace.criteria.map((ac) => `<span class="chip ${w.trace.covered.includes(ac) ? "ok" : "bad"}">${w.trace.covered.includes(ac) ? "✓" : "✗"} ${esc(w.id)}:${esc(ac)}</span>`).join("")}
        <span class="fine" style="align-self:center">${esc(t("wd.traceNote"))}</span></div></div>` : ""}
      <div class="tabs" role="tablist">
        <button role="tab" type="button" data-tab="audit" aria-selected="true">${esc(t("wd.audit"))}</button>
        ${KINDS.filter((k) => w.chain[k]).map((k) => `<button role="tab" type="button" style="--c:var(--st-${HUE[k]})" data-tab="${k}" aria-selected="false">${k}.md</button>`).join("")}
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
      return `<div class="link missing" style="--c:var(--st-${HUE[kind]})"><h3><span>${ICONS.stage(kind)}${kind}.md</span></h3>
        <p style="margin:0;font-size:13px">${esc(ready ? t("wd.ready") : t("wd.after", { prev: KINDS[i - 1] }))}</p>
        ${ready ? `<button class="btn small primary" type="button" data-act="stage" data-kind="${kind}">${esc(t("wd.makeDraft", { kind }))}</button>` : ""}</div>`;
    }
    return `<div class="link" style="--c:var(--st-${HUE[kind]})"><h3><span>${ICONS.stage(kind)}${kind}.md</span>${statusChip(a.status)}</h3>
      <div class="fine">${esc(t("wd.approvals", { have: a.approvals.length, need: a.needed }))}${a.tier ? ` · ${esc(a.tier)}` : ""}</div>
      ${a.approvals.length ? `<ul>${a.approvals.map((p) => `<li>${esc(p.by)} <span class="muted">· ${esc(p.role)} · ${esc(p.at)}</span></li>`).join("")}</ul>` : ""}
      ${a.issues.length ? `<ul style="color:var(--bad)">${a.issues.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
      ${a.status === "draft" ? `<button class="btn small primary" type="button" data-act="submit" data-kind="${kind}">${esc(t("wd.submit"))}</button>` : ""}
      ${a.status === "proposed" ? `<div class="fine">${esc(t("wd.decide"))}</div>${cmdBlock(w.id, kind)}` : ""}</div>`;
  }

  function audit(w) {
    const rows = KINDS.filter((k) => w.chain[k]).flatMap((k) => w.chain[k].history.map((h) => ({ ...h, kind: k })));
    rows.sort((a, b) => (a.at ? Date.parse(a.at) : Infinity) - (b.at ? Date.parse(b.at) : Infinity));
    if (!rows.length) return `<div class="empty" style="margin-top:16px">${esc(t("wd.noHistory"))}</div>`;
    return `<p class="fine" style="margin:14px 0 0">${esc(t("wd.auditNote"))}</p>
      <ol class="timeline">${rows.map((h) => `<li>
        <span class="when">${esc(when(h.at))}</span>
        <span class="mark ${h.author ? (isAgent(h.author) ? "agent" : "human") : ""}" aria-hidden="true"></span>
        <div class="what"><b>${esc(h.kind)}.md</b> → ${statusChip(h.status)} <span class="who">${h.author ? `${esc(h.author)} · <code>${esc(h.commit)}</code> · ${esc(h.subject)}` : esc(t("wd.uncommitted"))}</span></div>
      </li>`).join("")}</ol>`;
  }

  function doc(a) {
    const front = Object.entries(a.meta).map(([k, v]) => `${k}: ${Array.isArray(v) ? JSON.stringify(v) : v}`).join("\n");
    return `<div class="doc"><div class="front">${esc(front)}</div>${markdown(a.body)}<p class="fine"><code>${esc(a.path)}</code> — ${esc(t("wd.docNote"))}</p></div>`;
  }

  async function act(w, btn) {
    btn.disabled = true;
    const kind = btn.dataset.kind;
    try {
      if (btn.dataset.act === "stage") {
        const r = await api(`/api/work/${w.id}/stage`, { stage: kind });
        toast(t("wd.staged", { path: r.path }));
      } else {
        await api(`/api/work/${w.id}/submit`, { stage: kind });
        toast(t("wd.submitted", { id: w.id, kind }));
      }
      App.render();
    } catch (err) {
      toast(t("wd.failed", { msg: err.message }));
      btn.disabled = false;
    }
  }
})();
