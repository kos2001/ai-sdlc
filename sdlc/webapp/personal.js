/* Favorites and recent links use current API titles, never persisted artifact text. */
const Personal = (() => {
  const { esc, t } = App;
  let mounted = null;
  function button(id) {
    const on = Preferences.isFavorite(id);
    return `<button class="btn small favorite-toggle" type="button" data-favorite="${esc(id)}" aria-pressed="${on}" aria-label="${esc(t(on ? "personal.remove" : "personal.add", { id }))}"><span aria-hidden="true">${on ? "★" : "☆"}</span></button>`;
  }
  function entries(items) {
    const byId = new Map(items.map((w) => [w.id, w]));
    const ids = [...new Set([...Preferences.favorites, ...Preferences.recent])];
    return ids.map((id) => byId.get(id)).filter(Boolean).map((w) => ({ ...w, personal: Preferences.isFavorite(w.id) ? "personal.favorite" : "personal.recent" }));
  }
  function draw() {
    if (!mounted?.view.isConnected) return;
    const root = mounted.view.querySelector("#personal-shortcuts"), items = mounted.items;
    const byId = new Map(items.map((w) => [w.id, w]));
    const links = (ids) => ids.map((id) => byId.get(id)).filter(Boolean).slice(0, 10).map((w) => `<a href="${esc(App.workHref(w.id))}" title="${esc(w.title)}"><span class="mono">${esc(w.id)}</span> ${esc(w.title)}</a>`).join("");
    const favorites = links(Preferences.favorites), recent = links(Preferences.recent);
    root.innerHTML = `<details class="personal-panel" ${root.querySelector("details")?.open ? "open" : ""}><summary>${esc(t("personal.shortcuts"))} <span class="fine">★ ${Preferences.favorites.filter((id) => byId.has(id)).length} · ${esc(t("personal.recent"))} ${Preferences.recent.filter((id) => byId.has(id)).length}</span></summary>
      <div class="personal-group"><b>${esc(t("personal.favorite"))}</b><div>${favorites || `<span class="fine">${esc(t("personal.empty"))}</span>`}</div></div>
      <div class="personal-group"><b>${esc(t("personal.recent"))}</b><div>${recent || `<span class="fine">${esc(t("personal.noRecent"))}</span>`}</div></div></details>`;
  }
  function sync() {
    document.querySelectorAll("[data-favorite]").forEach((b) => {
      const on = Preferences.isFavorite(b.dataset.favorite);
      b.setAttribute("aria-pressed", String(on));
      b.setAttribute("aria-label", t(on ? "personal.remove" : "personal.add", { id: b.dataset.favorite }));
      b.querySelector("span").textContent = on ? "★" : "☆";
    });
    draw();
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-favorite]");
    if (b) { const on = Preferences.toggle(b.dataset.favorite); if (typeof on === "boolean") App.toast(t(on ? "personal.added" : "personal.removed")); }
  });
  window.addEventListener("personalchange", sync);
  window.addEventListener("langchange", sync);
  window.addEventListener("viewchange", () => { mounted = null; });
  return { button, entries, refresh: draw, mount(view, items) { mounted = { view, items }; draw(); } };
})();
