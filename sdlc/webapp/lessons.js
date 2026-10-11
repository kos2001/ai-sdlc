/* View: the self-improvement loop — lessons, what caught them, and the controls that now prevent them. */
(() => {
  const { esc, t, api, route, setTitle, statusChip } = App;
  const bars = (counts, label) => {
    const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<div class="lbar"><span>${esc(label(k))}</span><b>${n}</b>
      <i style="--w:${(n / total) * 100}%"></i></div>`).join("");
  };

  route(/^\/lessons$/, "lessons", async (view, m, params) => {
    setTitle(t("ls.crumb"), t("ls.title"));
    const s = await api("/api/lessons");
    if (!view.isConnected) return;
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
        <form class="filters">${Filters.search(params.get("q") || "", "ui.search")}
        ${Filters.select("status", "ui.status", [...Filters.all(), ...["open", "closed"].map((s) => [s, t(`status.${s}`)])], params.get("status") || "")}
        ${Filters.select("detector", "ui.detector", [...Filters.all(), ...Object.keys(s.detected_by).map((d) => [d, t(`det.${d}`)])], params.get("detector") || "")}
        <button class="btn" type="reset">${esc(t("ui.reset"))}</button></form><div id="lesson-results"></div>
      </div>`;
    const form = view.querySelector("form"), result = view.querySelector("#lesson-results");
    const draw = () => {
      const q = form.elements.q.value.trim().toLocaleLowerCase(I18N.locale);
      const status = form.elements.status.value, detector = form.elements.detector.value;
      const lessons = s.lessons.slice().reverse().filter((l) => (!status || l.status === status) && (!detector || l.detected_by === detector)
        && (!q || `${l.id} ${l.title} ${l.what_happened} ${l.root_cause} ${l.control?.ref || ""}`.toLocaleLowerCase(I18N.locale).includes(q)));
      result.innerHTML = Filters.result(lessons.length, s.lessons.length) + (lessons.length ? `<div class="checks">${lessons.map((l) => `<div class="check lesson ${l.status}">
          <span class="mono lid">${esc(l.id)}</span>
          <div><b>${esc(l.title)}</b> ${statusChip(l.status === "closed" ? "closed" : "open")} <span class="chip">${esc(t(`det.${l.detected_by}`))}</span>
            <p class="lwhat">${esc(l.what_happened)}</p>
            <p class="fine">${esc(t("ls.cause"))}: ${esc(l.root_cause)}</p>
            <p class="fine">${esc(t("ls.control"))}: ${l.control ? `<span class="chip ok">${esc(l.control.kind)}</span> <code>${esc(l.control.ref)}</code>` : esc(t("ls.none"))}</p></div>
        </div>`).join("")}</div>` : `<div class="empty">${esc(t("ui.noResults"))}</div>`);
    };
    const changed = () => { App.updateQuery({ q: form.elements.q.value, status: form.elements.status.value, detector: form.elements.detector.value }); draw(); };
    form.onsubmit = (e) => e.preventDefault();
    form.elements.q.oninput = changed;
    form.querySelectorAll("select").forEach((el) => (el.onchange = changed));
    form.onreset = (e) => { e.preventDefault(); for (const name of ["q", "status", "detector"]) form.elements[name].value = ""; changed(); };
    draw();
  });
})();
