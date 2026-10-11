/* A read-only work drawer: inspect without losing board filters or scroll. */
const Peek = (() => {
  const { esc, t, api, markdown, statusChip, tierChip, stageName, workHref } = App;
  let dialog, generation = 0;
  const close = () => { if (dialog?.open) dialog.close(); };
  async function load(id) {
    const token = ++generation;
    const content = dialog.querySelector("#peek-content");
    content.setAttribute("aria-busy", "true");
    content.innerHTML = `<p class="empty loading" role="status">${esc(t("ui.loading"))}</p>`;
    try {
      const w = await api(`/api/work/${id}`);
      if (!dialog.open || token !== generation) return;
      dialog.querySelector("#peek-title").textContent = `${w.id} · ${w.title}`;
      const kinds = ["intent", "spec", "plan"].filter((k) => w.chain[k]);
      const kind = kinds.at(-1), a = w.chain[kind];
      content.innerHTML = `<div class="work-meta">${tierChip(w.tier)}<span class="chip">${esc(stageName(w.stage))}</span><span class="chip">${esc(w.owner || "—")}</span></div>
        <div class="peek-chain">${kinds.map((k) => `<div><span class="mono">${k}.md</span>${statusChip(w.chain[k].status)}</div>`).join("")}</div>
        ${w.trace.criteria.length ? `<p class="fine">${esc(t("bd.ac", { c: w.trace.covered.length, n: w.trace.criteria.length }))}</p>` : ""}
        ${a?.issues.length ? `<div class="err" role="status">${a.issues.map(esc).join("<br>")}</div>` : ""}
        <p class="fine">${esc(t("peek.readOnly"))}</p><div class="doc">${markdown(a?.body || "")}</div>`;
      dialog.querySelector("#peek-actions").innerHTML = `<a class="btn" href="${esc(workHref(w.id))}">${esc(t("peek.detail"))}</a>
        ${a?.status === "draft" ? `<a class="btn primary" href="${esc(workHref(w.id, kind))}">${esc(t("ui.edit"))}</a>` : ""}`;
      dialog.querySelectorAll("a").forEach((a) => a.onclick = close);
    } catch (err) {
      if (!dialog.open || token !== generation) return;
      content.innerHTML = `<p class="err" role="alert">${esc(t("load.fail", { msg: err.message }))}</p><button class="btn" type="button" data-retry>${esc(t("ui.retry"))}</button>`;
      content.querySelector("[data-retry]").onclick = () => load(id);
    } finally { if (token === generation) content.removeAttribute("aria-busy"); }
  }
  function open(id) {
    if (document.querySelector("dialog[open]")) return;
    dialog.innerHTML = `<div class="peek-head"><div><span class="eyebrow">${esc(t("peek.label"))}</span><h2 id="peek-title">${esc(id)}</h2></div><button class="btn small" type="button" data-close aria-label="${esc(t("quick.close"))}">×</button></div>
      <div id="peek-content" role="region" tabindex="0" aria-label="${esc(t("ui.body"))}"></div><div id="peek-actions"></div>`;
    dialog.querySelector("[data-close]").onclick = close;
    dialog.showModal(); load(id);
  }
  window.addEventListener("DOMContentLoaded", () => {
    dialog = document.createElement("dialog"); dialog.id = "peek-dialog"; dialog.setAttribute("aria-labelledby", "peek-title"); document.body.append(dialog);
    dialog.addEventListener("close", () => { ++generation; });
    dialog.onclick = (e) => {
      const r = dialog.getBoundingClientRect();
      if (e.target === dialog && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) close();
    };
    document.addEventListener("click", (e) => { const b = e.target.closest("[data-peek]"); if (b) open(b.dataset.peek); });
    window.addEventListener("viewchange", close);
  });
  return { open, close };
})();
