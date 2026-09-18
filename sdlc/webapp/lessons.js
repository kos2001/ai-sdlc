/* View: the self-improvement loop — lessons, what caught them, and the controls that now prevent them. */
(() => {
  const { esc, t, api, route, setTitle, statusChip } = App;
  const bars = (counts, label) => {
    const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<div class="lbar"><span>${esc(label(k))}</span><b>${n}</b>
      <i style="--w:${(n / total) * 100}%"></i></div>`).join("");
  };

  route(/^\/lessons$/, "lessons", async (view) => {
    setTitle(t("ls.crumb"), t("ls.title"));
    const s = await api("/api/lessons");
    if (!s.total) {
      view.innerHTML = `<div class="empty">${esc(t("ls.empty"))}</div>`;
      return;
    }
    view.innerHTML = `
      <p class="muted" style="margin:0 0 18px;max-width:78ch">${esc(t("ls.lede"))}</p>
      <div class="grid tiles">
        <div class="card tile"><div class="lab">${esc(t("ls.total"))}</div><div class="num">${s.total}</div><div class="sub">${esc(t("ls.open", { n: s.open }))}</div></div>
        <div class="card tile ${s.prevention_rate < 0.5 ? "warn" : ""}"><div class="lab">${esc(t("ls.prevent"))}</div><div class="num">${Math.round(s.prevention_rate * 100)}<small>%</small></div><div class="sub">${esc(t("ls.preventSub", { n: s.caught_by_existing_gate, t: s.total }))}</div></div>
        <div class="card tile"><div class="lab">${esc(t("ls.holding"))}</div><div class="num">${s.controls_holding}<small>/ ${s.closed}</small></div><div class="sub">${esc(t("ls.holdingSub"))}</div></div>
      </div>
      <div class="grid lgrid">
        <div class="card"><h2 class="lh">${esc(t("ls.by"))}</h2>${bars(s.detected_by, (k) => t(`det.${k}`))}</div>
        <div class="card"><h2 class="lh">${esc(t("ls.controls"))}</h2>${bars(s.controls, (k) => k)}</div>
      </div>
      <div class="section"><h2>${esc(t("ls.list"))}</h2>
        <div class="checks">${s.lessons.slice().reverse().map((l) => `<div class="check lesson ${l.status}">
          <span class="mono lid">${esc(l.id)}</span>
          <div><b>${esc(l.title)}</b> ${statusChip(l.status === "closed" ? "closed" : "open")} <span class="chip">${esc(t(`det.${l.detected_by}`))}</span>
            <p class="lwhat">${esc(l.what_happened)}</p>
            <p class="fine">${esc(t("ls.cause"))}: ${esc(l.root_cause)}</p>
            <p class="fine">${esc(t("ls.control"))}: ${l.control ? `<span class="chip ok">${esc(l.control.kind)}</span> <code>${esc(l.control.ref)}</code>` : esc(t("ls.none"))}</p></div>
        </div>`).join("")}</div>
      </div>`;
  });
})();
