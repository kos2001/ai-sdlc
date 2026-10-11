/* ai-sdlc web app — core: API client, router, shared helpers. Views live in views.js / detail.js / intro.js. */
const App = (() => {
  const { t } = I18N;
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ROLE = { intent: "product-owner", spec: "architect", plan: "tech-lead" };
  const stageName = (k) => t(`stage.${k}`);
  const statusName = (s) => t(`status.${s}`) === `status.${s}` ? s : t(`status.${s}`);

  async function api(path, body) {
    const opts = body === undefined ? {} : {
      method: "POST", body: JSON.stringify(body),
      headers: { "Content-Type": "application/json", "X-SDLC": "1" },
    };
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    if (!res.ok) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg; el.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => (el.hidden = true), 3200);
  }

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast(t("copy.ok")); }
    catch { toast(t("copy.fail")); }
  }

  const statusChip = (status) => {
    const cls = status === "proposed" ? "gate" : ["accepted", "done", "closed"].includes(status) ? "ok" : status === "rejected" || status === "open" ? "bad" : "";
    return `<span class="chip ${cls}"><span class="dot"></span>${esc(statusName(status))}</span>`;
  };
  const tierChip = (tier) => (tier ? `<span class="chip ${tier === "T3" || tier === "T2" ? "gate" : ""}">${esc(tier)}</span>` : "");
  const approveCmd = (id, kind) => `python3 -m sdlc approve ${id} --stage ${kind} --role ${ROLE[kind]}`;
  const cmdBlock = (id, kind) => `<span class="cmd"><code>${esc(approveCmd(id, kind))}</code><button class="btn small" type="button" data-copy="${esc(approveCmd(id, kind))}">${esc(t("copy.btn"))}</button></span>`;
  const when = (iso) => {
    if (!iso) return t("when.none");
    return new Date(iso).toLocaleString(I18N.locale, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
  };

  /* Markdown for artifacts: headings, lists, checkboxes, fenced code, inline code, bold. HTML comments dropped. */
  function markdown(src) {
    const lines = src.replace(/<!--[\s\S]*?-->/g, "").split("\n");
    let out = "", list = false, code = false;
    const inline = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    const close = () => { if (list) { out += "</ul>"; list = false; } };
    for (const line of lines) {
      if (line.startsWith("```")) { close(); out += code ? "</pre>" : "<pre>"; code = !code; continue; }
      if (code) { out += esc(line) + "\n"; continue; }
      const h = line.match(/^(#{1,3})\s+(.*)/);
      const li = line.match(/^\s*-\s+(\[( |x|X)\]\s+)?(.*)/);
      if (h) { close(); out += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; }
      else if (li) {
        if (!list) { out += "<ul>"; list = true; }
        const box = li[1] ? (li[2] === " " ? "☐ " : "☑ ") : "";
        out += `<li>${box}${inline(li[3])}</li>`;
      } else if (line.trim()) { close(); out += `<p>${inline(line)}</p>`; }
      else close();
    }
    close();
    return code ? out + "</pre>" : out;
  }

  /* Router */
  const routes = [];
  const route = (re, name, render) => routes.push({ re, name, render });
  let activeHash = "", guard = null;
  const setGuard = (fn) => { guard = fn; };
  const query = () => new URLSearchParams(location.hash.split("?")[1] || "");
  function updateQuery(values, replace = false) {
    const params = query();
    for (const [key, value] of Object.entries(values)) {
      if (value === "" || value == null) params.delete(key); else params.set(key, value);
    }
    const hash = `${location.hash.split("?")[0]}${params.size ? `?${params}` : ""}`;
    history[replace ? "replaceState" : "pushState"](null, "", hash);
    activeHash = hash;
  }
  async function render(reason = "navigate") {
    const hash = location.hash.replace(/^#/, "") || "/";
    const path = hash.split("?")[0];
    if (guard && !guard(path, reason)) {
      history.replaceState(null, "", activeHash);
      return;
    }
    guard = null;
    activeHash = `#${hash}`;
    const r = routes.find((x) => x.re.test(path)) || routes[0];
    document.querySelectorAll(".nav a").forEach((a) => {
      const on = a.dataset.route === r.name;
      a.classList.toggle("on", on);
      if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    // Replacing the root isolates every pending renderer from the current screen.
    const view = document.createElement("div");
    view.id = "view";
    view.setAttribute("aria-live", "polite");
    $("#view").replaceWith(view);
    view.setAttribute("aria-busy", "true");
    view.innerHTML = `<div class="empty loading" role="status">${esc(t("ui.loading"))}</div>`;
    try {
      await r.render(view, path.match(r.re), query());
    } catch (err) {
      if (!view.isConnected) return;
      view.innerHTML = `<div class="empty"><p role="alert">${esc(t("load.fail", { msg: err.message }))}</p><p class="fine">${esc(t("load.hint"))}</p><button class="btn" data-retry>${esc(t("ui.retry"))}</button></div>`;
      $("[data-retry]", view).onclick = () => render("retry");
    }
    view.removeAttribute("aria-busy");
  }
  const setTitle = (crumb, title) => { $("#crumb").textContent = crumb; $("#title").textContent = title; document.title = `${title} · ai-sdlc`; };

  async function loadRepo() {
    try {
      const o = await api("/api/overview");
      $("#repo-name").textContent = o.repo;
      $("#repo-branch").textContent = o.branch || "";
      return o;
    } catch { return null; }
  }

  function wireNewWork() {
    const dlg = $("#new-dialog"), form = $("#new-form"), err = $("#nf-err");
    let pending = false;
    $("#new-work").onclick = () => { err.hidden = true; form.reset(); dlg.showModal(); $("#nf-title").focus(); };
    $("#nf-cancel").onclick = () => { if (!pending) dlg.close(); };
    dlg.addEventListener("cancel", (e) => { if (pending) e.preventDefault(); });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (pending) return;
      const body = Object.fromEntries(new FormData(form));
      body.title = body.title.trim(); body.owner = body.owner.trim();
      if (!body.title || !body.owner) { err.textContent = t("ui.required"); err.hidden = false; return; }
      pending = true; err.hidden = true;
      form.querySelectorAll("button").forEach((b) => (b.disabled = true));
      form.setAttribute("aria-busy", "true");
      try {
        const r = await api("/api/work", body);
        dlg.close();
        toast(t("new.created", { id: r.id, path: r.path }));
        location.hash = `#/work/${r.id}?tab=intent`;
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
      finally {
        pending = false; form.removeAttribute("aria-busy");
        form.querySelectorAll("button").forEach((b) => (b.disabled = false));
      }
    });
  }

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-copy]");
    if (b) copy(b.dataset.copy);
    const l = e.target.closest("[data-lang]");
    if (l) I18N.set(l.dataset.lang);
  });
  window.addEventListener("hashchange", () => { if (location.hash !== activeHash) render(); });
  window.addEventListener("popstate", () => { if (location.hash !== activeHash) render(); });
  window.addEventListener("langchange", () => render("language"));
  window.addEventListener("DOMContentLoaded", () => {
    I18N.apply();
    $("#brand-mark").innerHTML = ICONS.mark(24);
    wireNewWork();
    if (!location.hash) history.replaceState(null, "", location.search + "#/intro"); // first stop: what is different, and why
    $("#refresh").onclick = () => { loadRepo(); render("refresh"); };
    loadRepo();
    render();
  });

  return { $, esc, t, api, toast, route, render, setTitle, loadRepo, markdown, statusChip, tierChip, cmdBlock, when, stageName, ROLE, query, updateQuery, setGuard };
})();
