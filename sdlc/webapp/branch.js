/* Branch comparison retains its input on errors. */
(() => {
  const { esc, t, api, route, setTitle, tierChip } = App;
  route(/^\/branch$/, "branch", async (view, m, params) => {
    setTitle(t("br.crumb"), t("br.title"));
    view.innerHTML = `<form class="filters" id="branch-form"><label class="field search-field" for="branch-base"><span>${esc(t("ui.ref"))}</span><input id="branch-base" name="base" value="${esc(params.get("base") || "")}" placeholder="${esc(t("ui.refPh"))}" maxlength="200"></label><button class="btn primary" type="submit">${esc(t("ui.compare"))}</button></form><div id="branch-results"></div>`;
    const form = view.querySelector("form"), result = view.querySelector("#branch-results"), input = view.querySelector("input"), button = view.querySelector("button");
    let busy = false;
    async function check() {
      if (busy) return;
      const base = input.value.trim();
      App.updateQuery({ base });
      busy = true; button.disabled = true;
      result.setAttribute("aria-busy", "true");
      result.innerHTML = `<div class="empty loading" role="status">${esc(t("ui.loading"))}</div>`;
      try {
        const b = await api(`/api/branch${base ? `?base=${encodeURIComponent(base)}` : ""}`);
        if (!view.isConnected) return;
        if (!b.risk) {
          result.innerHTML = `<div class="empty">${esc(b.note || t("br.none"))}</div>`;
          return;
        }
        const top = b.risk.reasons.filter((r) => r.tier === b.risk.tier);
        const lede = esc(t("br.lede", { branch: "\u0000b", base: "\u0000c" })).replace("\u0000b", `<code>${esc(b.branch)}</code>`).replace("\u0000c", `<code>${esc(b.base)}</code>`);
        result.innerHTML = `
          <p class="muted" style="margin-top:0">${lede}</p>
          <div class="grid tiles">
            <div class="card tile ${["T2", "T3"].includes(b.risk.tier) ? "warn" : ""}"><div class="lab">${esc(t("br.tier"))}</div><div class="num">${esc(b.risk.tier)}</div><div class="sub">${esc(t("br.tierSub", { n: b.risk.human_reviews, rel: b.risk.release }))}</div></div>
            <div class="card tile"><div class="lab">${esc(t("br.gates"))}</div><div class="num">${b.gates.filter((g) => g.ok).length}<small>${esc(t("br.passed", { n: b.gates.length }))}</small></div><div class="sub">plan-gate · eval-guard · transitions</div></div>
          </div>
          <div class="section"><h2>${esc(t("br.files"))}</h2>
            <div class="table-wrap"><table><thead><tr><th>${esc(t("col.path"))}</th><th>${esc(t("col.tier"))}</th><th>${esc(t("col.rule"))}</th></tr></thead><tbody>
              ${top.map((r) => `<tr><td><code>${esc(r.path)}</code></td><td>${tierChip(r.tier)}</td><td class="muted">${esc(r.rule)}</td></tr>`).join("")}
            </tbody></table></div></div>
          <div class="section"><h2>${esc(t("br.gatesH"))}</h2><div class="checks">
            ${b.gates.map((g) => `<div class="check">${g.ok ? `<span class="chip ok"><span class="dot"></span>${esc(t("br.pass"))}</span>` : `<span class="chip bad"><span class="dot"></span>${esc(t("br.fail"))}</span>`}
              <div><b>${esc(g.name)}</b><ul>${g.messages.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></div></div>`).join("")}
          </div></div>
          ${b.events.length ? `<div class="section"><h2>${esc(t("br.next"))}</h2><div class="checks">${b.events.map((e) => `<div class="check"><span class="chip">${esc(e.event)}</span><div>${esc(e.work_id)} → <b>${esc(e.play)}</b> <span class="muted">(skill: ${esc(e.skill)})</span></div></div>`).join("")}</div></div>` : ""}`;

      } catch (err) {
        if (!view.isConnected) return;
        result.innerHTML = `<div class="empty"><p class="err" role="alert">${esc(err.message)}</p><button class="btn" data-retry>${esc(t("ui.retry"))}</button></div>`;
        result.querySelector("[data-retry]").onclick = check;
      } finally { busy = false; button.disabled = false; result.removeAttribute("aria-busy"); }
    }
    form.onsubmit = (e) => { e.preventDefault(); check(); };
    await check();
  });
})();
