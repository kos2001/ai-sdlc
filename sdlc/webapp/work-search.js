/* A small, explicit query language: no eval, no regex supplied by users. */
const WorkSearch = (() => {
  const stages = ["intent", "spec", "plan", "build", "done", "rejected", "active"];
  const flags = ["waiting", "issues", "untraced", "favorite", "recent", "draft"];
  const current = (w) => w.chain[["build", "done"].includes(w.stage) ? "plan" : w.stage] || w.chain.intent;
  function parse(raw) {
    const tokens = []; let text = "", quote = "";
    for (let i = 0; i < raw.length; i++) {
      const c = raw[i];
      if (quote && c === "\\" && raw[i + 1] === quote) { text += raw[++i]; continue; }
      if (c === quote) quote = "";
      else if (!quote && ["\"", "'"].includes(c) && (!text || text === "-" || text.endsWith(":"))) quote = c;
      else if (!quote && /\s/.test(c)) { if (text) tokens.push(text); text = ""; }
      else text += c;
    }
    if (quote) return { error: "search.quote", token: "", terms: [] };
    if (text) tokens.push(text);
    const terms = [];
    for (const token of tokens) {
      const field = token.match(/^(-?)(stage|tier|owner|id|is):(.*)$/i);
      if (!field) { const not = token.startsWith("-") && token.length > 1; terms.push({ field: "text", values: [not ? token.slice(1) : token], not }); continue; }
      const k = field[2].toLowerCase(), values = field[3].split(",").map((v) => v.trim().toLowerCase());
      if (values.some((v) => !v || (k === "stage" && !stages.includes(v)) || (k === "tier" && !/^t[0-3]$/.test(v)) || (k === "is" && !flags.includes(v)))) return { error: "search.value", token, terms: [] };
      terms.push({ field: k, values, not: !!field[1] });
    }
    return { error: "", terms };
  }
  function matches(w, query) {
    if (query.error) return false;
    return query.terms.every((term) => {
      const match = term.values.some((v) => {
        if (term.field === "stage") return v === "active" ? !["done", "rejected"].includes(w.stage) : w.stage === v;
        if (term.field === "tier") return (w.tier || "").toLowerCase() === v;
        if (term.field === "id") return w.id.toLowerCase() === v;
        if (term.field === "owner") return (w.owner || "").toLowerCase().includes(v);
        if (term.field === "is") return {
          waiting: w.awaiting.length > 0, issues: w.issues > 0, untraced: w.trace.covered.length < w.trace.criteria.length,
          favorite: Preferences.isFavorite(w.id), recent: Preferences.recent.includes(w.id), draft: current(w)?.status === "draft",
        }[v];
        return `${w.id} ${w.title} ${w.owner}`.toLowerCase().includes(v.toLowerCase());
      });
      return term.not ? !match : match;
    });
  }
  return { parse, matches };
})();
