/* Personal navigation only. Work files and approvals never enter this store. */
const Preferences = (() => {
  const empty = () => ({ version: 1, favorites: [], recent: [], views: [] });
  const idOK = (id) => typeof id === "string" && /^W-\d{4,}$/.test(id);
  const unique = (ids, max) => [...new Set(Array.isArray(ids) ? ids.filter(idOK) : [])].slice(0, max);
  let key = "", data = empty(), notice = "", memoryOnly = false;
  const keys = ["q", "stage", "tier", "focus", "sort", "view"];
  const choices = {
    stage: ["", "active", "intent", "spec", "plan", "build", "done", "rejected"], tier: ["", "T0", "T1", "T2", "T3"],
    focus: ["", "waiting", "issues", "untraced", "favorite"], sort: ["newest", "oldest", "title", "risk"], view: ["board", "list"],
  };
  function state(value = {}) {
    if (!value || typeof value !== "object") value = {};
    return Object.fromEntries(keys.map((k) => [k, k === "q" ? (typeof value.q === "string" ? value.q.slice(0, 2000) : "")
      : choices[k].includes(value[k]) ? value[k] : choices[k][0]]));
  }
  function decode(raw) {
    const value = JSON.parse(raw || "null");
    if (!value) return empty();
    if (value.version !== 1 || typeof value !== "object") throw new Error("Unsupported preferences");
    const seen = new Set();
    const views = (Array.isArray(value.views) ? value.views : []).filter((v) => {
      if (!v || typeof v.id !== "string" || !/^[\w-]{1,64}$/.test(v.id) || seen.has(v.id) || typeof v.name !== "string" || !v.name.trim()) return false;
      seen.add(v.id); return true;
    }).slice(0, 20).map((v) => ({ id: v.id, name: v.name.trim().slice(0, 80), state: state(v.state) }));
    return { version: 1, favorites: unique(value.favorites, 100), recent: unique(value.recent, 10), views };
  }
  const changed = () => window.dispatchEvent(new Event("personalchange"));
  function read() {
    try { data = decode(localStorage.getItem(key)); notice = ""; }
    catch (err) {
      data = empty();
      if (err instanceof SyntaxError || err.message === "Unsupported preferences") notice = "personal.corrupt";
      else { memoryOnly = true; notice = "personal.session"; }
    }
  }
  function configure(repo) {
    if (!/^[a-f0-9]{64}$/.test(repo?.workspace_id || "")) return;
    const next = `sdlc.personal.v1.${repo.workspace_id}`;
    if (next === key) return;
    key = next; memoryOnly = false; read(); changed();
  }
  async function ready() {
    if (key) return;
    configure(await App.loadRepo());
    if (!key) throw new Error(App.t("personal.unavailable"));
  }
  function commit() {
    if (!key) throw new Error(App.t("personal.unavailable"));
    if (!memoryOnly) {
      try { localStorage.setItem(key, JSON.stringify(data)); notice = ""; }
      catch { memoryOnly = true; notice = "personal.session"; }
    }
    changed();
  }
  const isFavorite = (id) => data.favorites.includes(id);
  function toggle(id) {
    if (!key || !idOK(id)) return;
    if (isFavorite(id)) data.favorites = data.favorites.filter((x) => x !== id);
    else {
      if (data.favorites.length >= 100) { App.toast(App.t("personal.favoriteLimit")); return; }
      data.favorites.unshift(id);
    }
    commit();
    return isFavorite(id);
  }
  function visit(id) {
    if (!key || !idOK(id) || data.recent[0] === id) return;
    data.recent = [id, ...data.recent.filter((x) => x !== id)].slice(0, 10); commit();
  }
  function saveView(name, filters, id = "") {
    name = name.trim();
    if (!name || name.length > 80) throw new Error(App.t("views.nameRequired"));
    if (data.views.some((v) => v.id !== id && v.name.toLocaleLowerCase() === name.toLocaleLowerCase())) throw new Error(App.t("views.duplicate"));
    const old = data.views.find((v) => v.id === id);
    if (id && !old) throw new Error(App.t("views.missing"));
    if (!old && data.views.length >= 20) throw new Error(App.t("views.limit"));
    const row = { id: old?.id || crypto.randomUUID(), name, state: state(filters) };
    if (old) data.views = data.views.map((v) => v.id === id ? row : v); else data.views.push(row);
    commit(); return row.id;
  }
  function removeView(id) { data.views = data.views.filter((v) => v.id !== id); commit(); }
  function href(filters, id = "") {
    const params = new URLSearchParams(), normalized = state(filters);
    for (const [k, v] of Object.entries(normalized)) if (v && !(k === "sort" && v === "newest") && !(k === "view" && v === "board")) params.set(k, v);
    if (id) params.set("saved", id);
    return `#/board${params.size ? `?${params}` : ""}`;
  }
  window.addEventListener("repodata", (e) => configure(e.detail));
  window.addEventListener("storage", (e) => { if (key && (e.key === key || e.key === null) && !memoryOnly) { read(); changed(); } });
  return { ready, state, href, toggle, visit, isFavorite, saveView, removeView,
    get favorites() { return [...data.favorites]; }, get recent() { return [...data.recent]; },
    get views() { return structuredClone(data.views); }, get notice() { return notice; } };
})();
