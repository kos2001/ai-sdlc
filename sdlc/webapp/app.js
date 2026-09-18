/* ai-sdlc web app — core: API client, router, shared helpers. Views live in views.js. */
const App = (() => {
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ROLE = { intent: "product-owner", spec: "architect", plan: "tech-lead" };
  const STAGE_KO = { intent: "의도", spec: "명세", plan: "계획", build: "구현", done: "완료", rejected: "반려" };
  const STATUS_KO = { draft: "초안", proposed: "승인 대기", accepted: "승인됨", rejected: "반려", superseded: "대체됨", done: "완료", open: "열림", diagnosed: "진단됨", closed: "닫힘" };

  async function api(path, body) {
    const opts = body === undefined ? {} : {
      method: "POST", body: JSON.stringify(body),
      headers: { "Content-Type": "application/json", "X-SDLC": "1" },
    };
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => (t.hidden = true), 3200);
  }

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast("복사했습니다. 터미널에 붙여 넣어 실행하세요."); }
    catch { toast("복사하지 못했습니다. 명령을 직접 선택해 복사하세요."); }
  }

  const statusChip = (status) => {
    const cls = status === "proposed" ? "gate" : ["accepted", "done", "closed"].includes(status) ? "ok" : status === "rejected" || status === "open" ? "bad" : "";
    return `<span class="chip ${cls}"><span class="dot"></span>${esc(STATUS_KO[status] || status)}</span>`;
  };
  const tierChip = (tier) => (tier ? `<span class="chip ${tier === "T3" || tier === "T2" ? "gate" : ""}">${esc(tier)}</span>` : "");
  const approveCmd = (id, kind) => `python3 -m sdlc approve ${id} --stage ${kind} --role ${ROLE[kind]}`;
  const cmdBlock = (id, kind) => `<span class="cmd"><code>${esc(approveCmd(id, kind))}</code><button class="btn small" type="button" data-copy="${esc(approveCmd(id, kind))}">복사</button></span>`;
  const when = (iso) => {
    if (!iso) return "커밋 전";
    const d = new Date(iso);
    return d.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
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
  async function render() {
    const hash = location.hash.replace(/^#/, "") || "/";
    const r = routes.find((x) => x.re.test(hash)) || routes[0];
    document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("on", a.dataset.route === r.name));
    const view = $("#view");
    view.setAttribute("aria-busy", "true");
    try {
      await r.render(view, hash.match(r.re));
    } catch (err) {
      view.innerHTML = `<div class="empty">불러오지 못했습니다: ${esc(err.message)}<br><span class="fine">서버가 켜져 있는지 확인하세요: python3 -m sdlc serve</span></div>`;
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
    $("#new-work").onclick = () => { err.hidden = true; form.reset(); dlg.showModal(); $("#nf-title").focus(); };
    $("#nf-cancel").onclick = () => dlg.close();
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = Object.fromEntries(new FormData(form));
      try {
        const r = await api("/api/work", body);
        dlg.close();
        toast(`${r.id} 의도 초안을 만들었습니다: ${r.path}`);
        location.hash = `#/work/${r.id}`;
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    });
  }

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-copy]");
    if (b) copy(b.dataset.copy);
  });
  window.addEventListener("hashchange", render);
  window.addEventListener("DOMContentLoaded", () => {
    wireNewWork();
    if (!location.hash) history.replaceState(null, "", "#/intro"); // first stop: what is different, and why
    $("#refresh").onclick = () => { loadRepo(); render(); };
    loadRepo();
    render();
  });

  return { $, esc, api, toast, route, render, setTitle, loadRepo, markdown, statusChip, tierChip, cmdBlock, when, ROLE, STAGE_KO, STATUS_KO };
})();
