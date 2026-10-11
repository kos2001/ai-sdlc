/* Incident search and status filters shareable through the URL. */
(() => {
  const { esc, t, api, route, setTitle, statusChip } = App;
  route(/^\/incidents$/, "incidents", async (view, m, params) => {
    setTitle(t("in.crumb"), t("in.title"));
    const items = await api("/api/incidents");
    if (!view.isConnected) return;
    const states = ["active", "open", "diagnosed", "closed"];
    view.innerHTML = `<form class="filters">${Filters.search(params.get("q") || "", "ui.search")}
      ${Filters.select("status", "ui.status", [...Filters.all(), ...states.map((s) => [s, t(s === "active" ? "ui.active" : `status.${s}`)])], params.get("status") || "")}
      <button class="btn" type="reset">${esc(t("ui.reset"))}</button></form><div id="incident-results"></div>`;
    const form = view.querySelector("form");
    function draw() {
      const q = form.elements.q.value.trim().toLocaleLowerCase(I18N.locale), status = form.elements.status.value;
      const list = items.filter((i) => (!q || `${i.id} ${i.service} ${i.band} ${i.followup_intent || ""}`.toLocaleLowerCase(I18N.locale).includes(q))
        && (!status || (status === "active" ? i.status !== "closed" : i.status === status)));
      view.querySelector("#incident-results").innerHTML = Filters.result(list.length, items.length) + (list.length
        ? `<div class="table-wrap"><table><thead><tr>${["col.incident", "col.status", "col.service", "col.detected", "col.followup"].map((k) => `<th scope="col">${esc(t(k))}</th>`).join("")}</tr></thead><tbody>${list.map((i) => {
          const work = (i.followup_intent || "").match(/W-\d{4,}/);
          return `<tr><td class="mono">${esc(i.id)}</td><td>${statusChip(i.status)}</td><td>${esc(i.service)} / ${esc(i.band)}</td><td class="mono">${esc(App.when(i.detected_at))}</td><td>${work ? `<a href="#/work/${work[0]}">${work[0]}</a>` : "—"}</td></tr>`;
        }).join("")}</tbody></table></div>` : `<div class="empty">${esc(t(items.length ? "ui.noResults" : "in.empty"))}</div>`);
    }
    const changed = () => { App.updateQuery({ q: form.elements.q.value, status: form.elements.status.value }); draw(); };
    form.onsubmit = (e) => e.preventDefault();
    form.elements.q.oninput = changed; form.elements.status.onchange = changed;
    form.onreset = (e) => { e.preventDefault(); form.elements.q.value = ""; form.elements.status.value = ""; changed(); };
    draw();
  });
})();
