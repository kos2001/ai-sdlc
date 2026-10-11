/* Board and list share filters; the URL is the source of navigation state. */
(() => {
  const { esc, t, api, route, setTitle, statusChip, tierChip, stageName } = App;
  const stages = ["intent", "spec", "plan", "build", "done", "rejected"];
  const hues = { intent: "plan", spec: "design", plan: "build", build: "test", done: "deploy", rejected: "maintain" };
  const current = (w) => w.chain[["build", "done"].includes(w.stage) ? "plan" : w.stage] || w.chain.intent;
  route(/^\/board$/, "board", async (view, m, params) => {
    setTitle(t("bd.crumb"), t("bd.title"));
    const [items] = await Promise.all([api("/api/work"), Preferences.ready()]);
    if (!view.isConnected) return;
    const pick = (key, choices, fallback = "") => choices.includes(params.get(key)) ? params.get(key) : fallback;
    const state = {
      q: params.get("q") || "", stage: pick("stage", [...stages, "active"]), tier: pick("tier", ["T0", "T1", "T2", "T3"]),
      focus: pick("focus", ["waiting", "issues", "untraced", "favorite"]), sort: pick("sort", ["newest", "oldest", "title", "risk"], "newest"),
      view: pick("view", ["board", "list"], "board"),
    };
    view.innerHTML = `<div id="saved-views"></div><div id="personal-shortcuts"></div><form class="filters" id="board-filters">
      ${Filters.search(state.q)}
      ${Filters.select("stage", "ui.stage", [...Filters.all(), ["active", t("ui.active")], ...stages.map((s) => [s, stageName(s)])], state.stage)}
      ${Filters.select("tier", "ui.tier", [...Filters.all(), ...["T0", "T1", "T2", "T3"].map((s) => [s, s])], state.tier)}
      ${Filters.select("focus", "ui.focus", [...Filters.all(), ...["waiting", "issues", "untraced", "favorite"].map((s) => [s, t(`ui.${s}`)])], state.focus)}
      ${Filters.select("sort", "ui.sort", ["newest", "oldest", "title", "risk"].map((s) => [s, t(`ui.${s}`)]), state.sort)}
      <button class="btn" type="button" data-reset>${esc(t("ui.reset"))}</button>
      <div class="view-switch" role="group" aria-label="${esc(t("ui.view"))}">${["board", "list"].map((v) => `<button class="btn" type="button" data-layout="${v}" aria-pressed="${state.view === v}">${esc(t(`ui.${v}`))}</button>`).join("")}</div>
    </form><details class="search-help"><summary>${esc(t("search.help"))}</summary><p>${esc(t("search.syntax"))}</p><code>stage:spec tier:T3 owner:"Dana Park" -stage:done</code><p>${esc(t("search.flags"))}</p></details><p id="search-error" class="err" role="alert" hidden></p><div id="board-results"></div>`;
    const form = view.querySelector("#board-filters");
    const draw = () => {
      const query = WorkSearch.parse(state.q);
      const error = view.querySelector("#search-error");
      error.hidden = !query.error; error.textContent = query.error ? t(query.error, { token: query.token }) : "";
      const found = items.filter((w) => WorkSearch.matches(w, query)
        && (!state.stage || (state.stage === "active" ? !["done", "rejected"].includes(w.stage) : w.stage === state.stage))
        && (!state.tier || w.tier === state.tier)
        && (!state.focus || (state.focus === "favorite" ? Preferences.isFavorite(w.id) : state.focus === "waiting" ? w.awaiting.length > 0 : state.focus === "issues" ? w.issues > 0 : w.trace.covered.length < w.trace.criteria.length)));
      found.sort((a, b) => state.sort === "title" ? a.title.localeCompare(b.title, I18N.locale)
        : state.sort === "risk" ? (b.tier || "").localeCompare(a.tier || "") || b.id.localeCompare(a.id)
        : state.sort === "oldest" ? a.id.localeCompare(b.id) : b.id.localeCompare(a.id));
      const result = view.querySelector("#board-results");
      form.querySelectorAll("[data-layout]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.layout === state.view)));
      const columns = stages.filter((s) => (s !== "rejected" || items.some((w) => w.stage === s))
        && (!state.stage || (state.stage === "active" ? !["done", "rejected"].includes(s) : s === state.stage)));
      result.innerHTML = Filters.result(found.length, items.length) + (!found.length
        ? `<div class="empty">${esc(t(items.length ? "ui.noResults" : "bd.empty"))}</div>`
        : state.view === "list" ? list(found)
        : `<div class="board" style="grid-template-columns:repeat(${columns.length},minmax(200px,1fr))">${columns.map((c) => {
          const members = found.filter((w) => w.stage === c);
          return `<section class="col" style="--c:var(--st-${hues[c]})" aria-label="${esc(stageName(c))}"><h3><span>${ICONS.stage(c)}${esc(stageName(c))}</span><span class="mono">${members.length}</span></h3>${members.map(card).join("") || `<p class="fine">${esc(t("bd.none"))}</p>`}</section>`;
        }).join("")}</div>`);
      SavedViews.refresh();
      Personal.refresh();
    };
    form.onsubmit = (e) => e.preventDefault();
    const change = (e) => {
      state[e.target.name] = e.target.value;
      App.updateQuery({ ...state, sort: state.sort === "newest" ? "" : state.sort, view: state.view === "board" ? "" : state.view });
      draw();
    };
    form.querySelector("input").oninput = change;
    form.querySelectorAll("select").forEach((s) => (s.onchange = change));
    form.querySelector("[data-reset]").onclick = () => {
      Object.assign(state, { q: "", stage: "", tier: "", focus: "", sort: "newest" });
      for (const [key, value] of Object.entries(state)) if (form.elements[key]) form.elements[key].value = value;
      App.updateQuery({ q: "", stage: "", tier: "", focus: "", sort: "" }); draw();
    };
    form.querySelectorAll("[data-layout]").forEach((b) => (b.onclick = () => {
      state.view = b.dataset.layout; App.updateQuery({ view: state.view === "board" ? "" : state.view }); draw();
    }));
    SavedViews.mount(view.querySelector("#saved-views"), state, params.get("saved"), () => {
      for (const [key, value] of Object.entries(state)) if (form.elements[key]) form.elements[key].value = value;
      App.updateQuery({ ...state, sort: state.sort === "newest" ? "" : state.sort, view: state.view === "board" ? "" : state.view }); draw();
    });
    Personal.mount(view, items);
    const personalChanged = () => {
      if (!view.isConnected) return;
      const focused = document.activeElement?.dataset.favorite;
      draw();
      if (focused) (view.querySelector(`[data-favorite="${focused}"]`) || form.elements.q).focus();
    };
    window.addEventListener("personalchange", personalChanged);
    window.addEventListener("viewchange", () => window.removeEventListener("personalchange", personalChanged), { once: true });
    draw();
  });
  function card(w) {
    const a = current(w), tr = w.trace;
    const pct = tr.criteria.length ? tr.covered.length / tr.criteria.length * 100 : 0;
    return `<article class="wcard"><a class="wcard-main" href="${esc(App.workHref(w.id))}"><span class="id">${esc(w.id)}${w.origin === "maintain-loop" ? ` · ${esc(t("bd.loop"))}` : ""}</span>
      <span class="t">${esc(w.title)}</span><span class="meta">${tierChip(w.tier)}${a ? statusChip(a.status) : ""}${w.issues ? `<span class="chip bad">${esc(t("bd.issues", { n: w.issues }))}</span>` : ""}</span>
      <span class="fine owner">${esc(w.owner || "—")}</span>${a?.status === "proposed" ? `<span class="fine">${esc(t("bd.approvals", { have: a.approvals.length, need: a.needed }))}</span>` : ""}
      ${tr.criteria.length ? `<span class="fine">${esc(t("bd.ac", { c: tr.covered.length, n: tr.criteria.length }))}</span><span class="bar"><i style="width:${pct}%"></i></span>` : ""}</a>
      <div class="wcard-controls">${Personal.button(w.id)}<button class="btn small peek-trigger" type="button" data-peek="${esc(w.id)}" aria-label="${esc(t("peek.work", { id: w.id }))}">${esc(t("peek.label"))}<span aria-hidden="true">↗</span></button></div></article>`;
  }
  function list(items) {
    return `<div class="table-wrap"><table><thead><tr>${["col.work", "ui.stage", "col.tier", "col.status", "new.owner", "peek.label"].map((k) => `<th scope="col">${esc(t(k))}</th>`).join("")}</tr></thead><tbody>${items.map((w) => `<tr><td><a href="${esc(App.workHref(w.id))}"><span class="mono">${esc(w.id)}</span> ${esc(w.title)}</a></td><td>${esc(stageName(w.stage))}</td><td>${tierChip(w.tier)}</td><td>${current(w) ? statusChip(current(w).status) : "—"}</td><td>${esc(w.owner || "—")}</td><td><div class="wcard-controls">${Personal.button(w.id)}<button class="btn small" type="button" data-peek="${esc(w.id)}" aria-label="${esc(t("peek.work", { id: w.id }))}">${esc(t("peek.label"))}</button></div></td></tr>`).join("")}</tbody></table></div>`;
  }
})();
