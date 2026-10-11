/* One keyboard-accessible switcher, with fresh work data every time it opens. */
(() => {
  const { esc, t, api, workHref } = App;
  let dialog, input, list, info, error, retry, items = [], choices = [], selected = 0, generation = 0;
  const screens = [
    ["/board", "nav.board"], ["/", "nav.overview"], ["/branch", "nav.branch"],
    ["/incidents", "nav.incidents"], ["/lessons", "nav.lessons"], ["/intro", "nav.intro"], ["/guide", "nav.guide"],
  ];
  function select(index) {
    selected = index;
    list.querySelectorAll("[role=option]").forEach((el, i) => el.setAttribute("aria-selected", String(i === selected)));
    const active = list.children[selected];
    if (active) {
      input.setAttribute("aria-activedescendant", active.id);
      active.scrollIntoView({ block: "nearest" });
    } else input.removeAttribute("aria-activedescendant");
  }
  function draw() {
    const q = input.value.trim().toLocaleLowerCase(I18N.locale);
    const routes = screens.map(([path, label]) => ({ href: `#${path}`, title: t(label), meta: t("quick.screen") }));
    const personal = Personal.entries(items);
    const ids = new Set(personal.map((w) => w.id));
    const works = [...personal, ...items.filter((w) => !ids.has(w.id))].map((w) => ({ href: workHref(w.id), title: `${w.id} · ${w.title}`, meta: `${w.personal ? `${t(w.personal)} · ` : ""}${App.stageName(w.stage)} · ${w.owner || "—"}` }));
    const views = Preferences.views.map((v) => ({ href: Preferences.href(v.state, v.id), title: v.name, meta: t("views.title") }));
    const found = [...works.filter((r, i) => i < personal.length), ...views, ...routes, ...works.slice(personal.length)].filter((r) => !q || `${r.title} ${r.meta}`.toLocaleLowerCase(I18N.locale).includes(q));
    choices = found.slice(0, 15);
    info.textContent = t(found.length ? "quick.count" : "ui.noResults", { n: found.length });
    list.innerHTML = choices.map((r, i) => `<button type="button" role="option" tabindex="-1" id="quick-choice-${i}" aria-selected="false"><span>${esc(r.title)}</span><small>${esc(r.meta)}</small><span class="quick-enter" aria-hidden="true">↵</span></button>`).join("");
    [...list.children].forEach((el, i) => {
      el.onclick = () => { const href = choices[i].href; dialog.close(); location.hash = href; };
      el.onpointermove = () => select(i);
    });
    select(0);
  }
  async function load() {
    const token = ++generation;
    error.hidden = true; retry.hidden = true;
    list.setAttribute("aria-busy", "true");
    try {
      const [data] = await Promise.all([api("/api/work"), Preferences.ready()]);
      if (!dialog.open || token !== generation) return;
      items = data; draw();
    } catch (err) {
      if (!dialog.open || token !== generation) return;
      error.textContent = t("load.fail", { msg: err.message }); error.hidden = false; retry.hidden = false;
    } finally { if (token === generation) list.removeAttribute("aria-busy"); }
  }
  function open() {
    if (document.querySelector("dialog[open]")) return;
    dialog.innerHTML = `<div class="quick-head"><h2 id="quick-title">${esc(t("quick.title"))}</h2><button class="btn small" type="button" data-close>${esc(t("quick.close"))} <kbd>Esc</kbd></button></div>
      <label class="field" for="quick-input"><span>${esc(t("ui.search"))}</span><input id="quick-input" type="search" autocomplete="off" role="combobox" aria-expanded="true" aria-autocomplete="list" aria-controls="quick-results" aria-describedby="quick-hint" placeholder="${esc(t("quick.placeholder"))}"></label>
      <p id="quick-count" role="status" class="fine"></p><div id="quick-results" role="listbox" aria-label="${esc(t("quick.results"))}"></div>
      <p class="err" id="quick-error" role="alert" hidden></p><button class="btn small" type="button" data-retry hidden>${esc(t("ui.retry"))}</button>
      <p class="quick-hint" id="quick-hint">${esc(t("quick.hint"))}</p>`;
    input = dialog.querySelector("input"); list = dialog.querySelector("[role=listbox]");
    info = dialog.querySelector("#quick-count"); error = dialog.querySelector("#quick-error"); retry = dialog.querySelector("[data-retry]");
    dialog.querySelector("[data-close]").onclick = () => dialog.close();
    retry.onclick = load; input.oninput = draw;
    input.onkeydown = (e) => {
      if (e.isComposing) return;
      if (e.key === "Escape") { e.preventDefault(); dialog.close(); return; }
      if (["ArrowDown", "ArrowUp", "Enter"].includes(e.key)) e.preventDefault();
      if (!choices.length) return;
      if (e.key === "ArrowDown") select((selected + 1) % choices.length);
      if (e.key === "ArrowUp") select((selected + choices.length - 1) % choices.length);
      if (e.key === "Enter") list.children[selected].click();
    };
    items = []; draw(); dialog.showModal(); input.focus(); load();
  }
  window.addEventListener("DOMContentLoaded", () => {
    dialog = document.createElement("dialog"); dialog.id = "quick-dialog"; dialog.setAttribute("aria-labelledby", "quick-title");
    document.body.append(dialog);
    dialog.addEventListener("close", () => { ++generation; });
    dialog.onclick = (e) => {
      const r = dialog.getBoundingClientRect();
      if (e.target === dialog && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) dialog.close();
    };
    document.querySelector("#quick-open").onclick = open;
    document.addEventListener("keydown", (e) => {
      if (e.defaultPrevented || e.isComposing || e.altKey || !(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== "k") return;
      e.preventDefault(); if (dialog.open) dialog.close(); else open();
    });
    window.addEventListener("viewchange", () => { if (dialog.open) dialog.close(); });
    window.addEventListener("personalchange", () => { if (dialog.open) draw(); });
  });
})();
