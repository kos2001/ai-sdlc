/* Explicit personal view saves; URL filters stay authoritative and shareable. */
const SavedViews = (() => {
  const { esc, t } = App;
  let mounted = null;
  function mount(root, state, selected, apply) {
    root.innerHTML = `<section class="saved-panel" aria-label="${esc(t("views.title"))}"><form id="saved-view-form">
      <label class="field" for="saved-view"><span>${esc(t("views.title"))}</span><select id="saved-view"></select></label>
      <label class="field view-name" for="view-name"><span>${esc(t("views.name"))}</span><input id="view-name" maxlength="80" autocomplete="off" placeholder="${esc(t("views.namePh"))}"></label>
      <button class="btn" type="submit">${esc(t("views.create"))}</button>
      <button class="btn small" type="button" data-view-update>${esc(t("views.update"))}</button>
      <button class="btn small" type="button" data-view-rename>${esc(t("views.rename"))}</button>
      <button class="btn small" type="button" data-view-delete>${esc(t("views.delete"))}</button>
      <button class="btn small" type="button" data-view-share>${esc(t("views.share"))}</button>
      </form><p id="view-state" role="status" class="fine"></p><p id="view-error" class="err" role="alert" hidden></p>
      <label class="field" for="view-link" id="view-link-field" hidden><span>${esc(t("views.link"))}</span><input id="view-link" readonly></label></section>`;
    const select = root.querySelector("select"), name = root.querySelector("#view-name"), error = root.querySelector("#view-error");
    const m = { root, state, selected: Preferences.views.some((v) => v.id === selected) ? selected : "", select, name, error };
    mounted = m;
    const choose = (id) => {
      m.selected = id;
      const row = Preferences.views.find((v) => v.id === id);
      name.value = row?.name || "";
      if (row) { Object.assign(state, row.state); apply(); }
      App.updateQuery({ saved: id || "" }, true);
      refresh();
    };
    select.onchange = () => choose(select.value);
    const run = (fn) => {
      error.hidden = true;
      try { fn(); } catch (err) { error.textContent = err.message; error.hidden = false; }
    };
    root.querySelector("form").onsubmit = (e) => { e.preventDefault(); run(() => choose(Preferences.saveView(name.value, state))); };
    root.querySelector("[data-view-update]").onclick = () => run(() => {
      const row = Preferences.views.find((v) => v.id === m.selected);
      choose(Preferences.saveView(row?.name || "", state, m.selected));
    });
    root.querySelector("[data-view-rename]").onclick = () => run(() => {
      const row = Preferences.views.find((v) => v.id === m.selected);
      if (row) { Preferences.saveView(name.value, row.state, row.id); refresh(); }
    });
    root.querySelector("[data-view-delete]").onclick = () => {
      const row = Preferences.views.find((v) => v.id === m.selected);
      if (row && window.confirm(t("views.deleteConfirm", { name: row.name }))) { Preferences.removeView(row.id); choose(""); }
    };
    root.querySelector("[data-view-share]").onclick = async () => {
      const url = `${location.origin}${location.pathname}${location.search}${Preferences.href(state)}`;
      const field = root.querySelector("#view-link"); root.querySelector("#view-link-field").hidden = false;
      field.value = url; field.focus(); field.select();
      try { await navigator.clipboard.writeText(url); App.toast(t("views.copied")); }
      catch { App.toast(t("views.copyHint")); }
    };
    name.value = Preferences.views.find((v) => v.id === m.selected)?.name || "";
    refresh();
  }
  function refresh() {
    if (!mounted?.root.isConnected) return;
    const m = mounted, rows = Preferences.views;
    if (!rows.some((v) => v.id === m.selected)) m.selected = "";
    m.select.innerHTML = `<option value="">${esc(t("views.unsaved"))}</option>` + rows.map((v) => `<option value="${esc(v.id)}">${esc(v.name)}</option>`).join("");
    m.select.value = m.selected;
    const row = rows.find((v) => v.id === m.selected);
    m.root.querySelectorAll("[data-view-update],[data-view-rename],[data-view-delete]").forEach((b) => { b.disabled = !row; });
    const dirty = row && JSON.stringify(Preferences.state(m.state)) !== JSON.stringify(row.state);
    m.root.querySelector("#view-state").textContent = [t(dirty ? "views.changed" : row ? "views.saved" : "views.local"), Preferences.notice ? t(Preferences.notice) : ""].filter(Boolean).join(" · ");
  }
  window.addEventListener("personalchange", refresh);
  window.addEventListener("viewchange", () => { mounted = null; });
  return { mount, refresh };
})();
