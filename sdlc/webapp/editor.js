/* Draft buffers survive tab/language/refresh changes, but never overwrite stale files. */
const Editor = (() => {
  const { esc, t, api, markdown, toast } = App;
  const buffers = new Map();
  const key = (id, kind) => `${id}/${kind}`;
  const changed = (e) => e.body !== e.original || JSON.stringify(e.sources) !== e.originalSources;
  const entries = (id) => [...buffers].filter(([k]) => k.startsWith(`${id}/`)).map(([, e]) => e);
  const dirty = (id, kind) => kind ? !!buffers.get(key(id, kind)) && changed(buffers.get(key(id, kind))) : entries(id).some(changed);
  const pending = (id) => entries(id).some((e) => e.pending);
  function forget(id) { for (const k of buffers.keys()) if (k.startsWith(`${id}/`)) buffers.delete(k); }
  function canLeave(id, path) {
    if (pending(id)) { toast(t("ui.busy")); return false; }
    if (path === `/work/${id}`) return true;
    if (dirty(id) && !window.confirm(t("ui.leave"))) return false;
    forget(id); return true;
  }
  window.addEventListener("beforeunload", (e) => {
    if ([...buffers.values()].some((b) => changed(b) || b.pending)) { e.preventDefault(); e.returnValue = ""; }
  });
  function mount(panel, w, kind) {
    const a = w.chain[kind], k = key(w.id, kind);
    let e = buffers.get(k);
    if (!e || (!changed(e) && !e.pending && e.revision !== a.revision)) {
      e = { body: a.body, original: a.body, sources: structuredClone(a.meta.sources || []), revision: a.revision, pending: false, error: "", conflict: false };
      e.originalSources = JSON.stringify(e.sources);
      buffers.set(k, e);
    }
    panel.innerHTML = `<div class="editor"><p class="muted">${esc(t("ui.editNote"))}</p>
      <form id="draft-form"><div class="editor-columns"><label class="field" for="draft-body"><span>${esc(t("ui.body"))}</span>
      <textarea id="draft-body" name="body" spellcheck="false">${esc(e.body)}</textarea></label>
      <section class="preview"><h2>${esc(t("ui.preview"))}</h2><div class="doc" id="draft-preview"></div></section></div>
      ${kind === "intent" ? `<fieldset class="source-set"><legend>${esc(t("ui.sources"))}</legend><div id="source-rows"></div><button class="btn small" type="button" data-add-source>${esc(t("ui.addSource"))}</button></fieldset>` : ""}
      <p class="err" id="draft-error" role="alert" hidden></p>
      <div class="editor-actions"><span id="draft-state" role="status"></span><button class="btn" type="button" data-reload hidden>${esc(t("ui.reload"))}</button>
      <button class="btn primary" type="submit" id="draft-save">${esc(t("ui.save"))}</button></div></form></div>`;
    const form = panel.querySelector("form"), input = panel.querySelector("textarea"), status = panel.querySelector("#draft-state");
    const saveButton = panel.querySelector("#draft-save"), error = panel.querySelector("#draft-error"), reload = panel.querySelector("[data-reload]");
    const update = () => {
      panel.querySelector("#draft-preview").innerHTML = markdown(e.body);
      status.textContent = t(e.pending ? "ui.saving" : changed(e) ? "ui.dirty" : "ui.saved");
      status.className = changed(e) ? "chip gate" : "chip ok";
      saveButton.disabled = e.pending || !changed(e) || e.conflict;
      error.textContent = e.error; error.hidden = !e.error;
      reload.hidden = !e.conflict;
      form.setAttribute("aria-busy", String(e.pending));
    };
    const sources = () => {
      const target = panel.querySelector("#source-rows");
      if (!target) return;
      target.innerHTML = e.sources.map((s, i) => `<div class="source-row">
        <label class="field" for="source-kind-${i}"><span>${esc(t("ui.sourceKind"))}</span><input id="source-kind-${i}" data-index="${i}" data-field="kind" value="${esc(s.kind)}" maxlength="2000" required placeholder="ticket / metric / feedback"></label>
        <label class="field" for="source-ref-${i}"><span>${esc(t("ui.sourceRef"))}</span><input id="source-ref-${i}" data-index="${i}" data-field="ref" value="${esc(s.ref)}" maxlength="2000" required></label>
        <button class="btn small" type="button" data-remove-source="${i}" aria-label="${esc(t("ui.removeSource", { n: i + 1 }))}">×</button></div>`).join("");
      target.querySelectorAll("input").forEach((field) => (field.oninput = () => { e.sources[Number(field.dataset.index)][field.dataset.field] = field.value; update(); }));
      target.querySelectorAll("[data-remove-source]").forEach((b) => (b.onclick = () => { e.sources.splice(Number(b.dataset.removeSource), 1); sources(); update(); panel.querySelector("[data-add-source]").focus(); }));
    };
    input.oninput = () => { e.body = input.value; update(); };
    const add = panel.querySelector("[data-add-source]");
    if (add) add.onclick = () => {
      if (e.sources.length >= 50) return;
      e.sources.push({ kind: "ticket", ref: "" }); sources(); update();
      panel.querySelector(`#source-ref-${e.sources.length - 1}`).focus();
    };
    reload.onclick = () => {
      if (!window.confirm(t("ui.reloadConfirm"))) return;
      buffers.delete(k); App.render("reload");
    };
    form.onsubmit = async (event) => {
      event.preventDefault();
      if (e.pending || e.conflict || !changed(e)) return;
      if (e.sources.some((s) => !s.kind.trim() || !s.ref.trim())) { e.error = t("ui.sourceRequired"); update(); return; }
      const data = { stage: kind, body: e.body, revision: e.revision };
      if (kind === "intent") data.sources = e.sources;
      e.pending = true; e.error = "";
      form.querySelectorAll("input,textarea,button").forEach((el) => (el.disabled = true)); update();
      try {
        const saved = await api(`/api/work/${w.id}/draft`, data);
        e.original = e.body; e.originalSources = JSON.stringify(e.sources); e.revision = saved.revision;
        toast(t("ui.saved"));
      } catch (err) {
        e.conflict = err.status === 409;
        e.error = e.conflict ? t("ui.conflict") : err.message;
      } finally {
        e.pending = false;
        form.querySelectorAll("input,textarea,button").forEach((el) => (el.disabled = false)); update();
      }
      if (!e.error && panel.isConnected) App.render("saved");
    };
    sources(); update();
  }
  return { mount, dirty, pending, canLeave, forget };
})();
