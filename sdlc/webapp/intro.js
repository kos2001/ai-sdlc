/* View: plain-language comparison of the traditional SDLC and the AI-native SDLC, tied to live data. Content: intro-data.js. */
(() => {
  const { esc, api, route, setTitle } = App;
  const BADGE_CLASS = { P: "who-p", A: "who-a", G: "who-g", H: "who-h" };
  const fill = (s, v) => String(s).replace(/\{(\w+)\}/g, (_, k) => v[k] ?? "");

  route(/^\/intro$/, "intro", async (view) => {
    const c = INTRO[I18N.lang] || INTRO.ko;
    const badges = (code) => code.split("·").map((k) => `<span class="who ${BADGE_CLASS[k]}">${esc(c.badge[k])}</span>`).join("");
    setTitle(c.crumb, c.title);
    view.style.setProperty("--old-label", JSON.stringify(`${c.oldShort} · `)); // mobile row labels
    view.innerHTML = `
      <p class="intro-lede">${c.lede}</p>

      <div class="glance" role="table" aria-label="${esc(c.glanceLabel)}">
        <div class="glance-head" role="row"><span role="columnheader"></span><span role="columnheader" class="g-old">${esc(c.old)}</span><span role="columnheader" class="g-new">${esc(c.now)}</span></div>
        ${c.glance.map(([q, o, n]) => `<div class="glance-row" role="row"><span role="rowheader">${esc(q)}</span><span role="cell" class="g-old">${esc(o)}</span><span role="cell" class="g-new">${esc(n)}</span></div>`).join("")}
      </div>

      <div class="section"><h2>${esc(c.stagesH)}</h2>
        <ol class="stage-list">${c.stages.map(([s, o, n, diff], i) => `<li>
          <span class="st-name"><span class="st-no">${i + 1}</span>${esc(s)}</span>
          <span class="st-old">${esc(o)}</span>
          <span class="st-arrow" aria-hidden="true">→</span>
          <span class="st-new">${esc(n)}</span>
          <span class="chip ok st-diff">${esc(diff)}</span>
        </li>`).join("")}</ol>
      </div>

      <div class="section"><h2>${esc(c.whoH)}</h2>
        <div class="table-wrap"><table class="who-table"><thead><tr><th>${esc(c.colJob)}</th><th>${esc(c.old)}</th><th>${esc(c.now)}</th></tr></thead><tbody>
          ${c.who.map(([job, o, n]) => `<tr><td>${esc(job)}</td><td>${badges(o)}</td><td>${badges(n)}</td></tr>`).join("")}
        </tbody></table></div>
        <p class="fine">${esc(c.whoNote)}</p>
      </div>

      <div class="section"><h2>${esc(c.liveH)}</h2>
        <div class="grid live" id="intro-live"><div class="empty">${esc(c.loading)}</div></div>
      </div>

      <div class="section"><h2>${esc(c.faqH)}</h2>
        ${c.faq.map(([q, a]) => `<details class="faq"><summary>${esc(q)}</summary><p>${esc(a)}</p></details>`).join("")}
      </div>

      <p class="fine" style="margin-top:28px">${c.more}</p>`;

    try {
      const [o, items] = await Promise.all([api("/api/overview"), api("/api/work")]);
      const t3 = items.find((i) => i.tier === "T3" && i.awaiting.length);
      const done = items.find((i) => i.stage === "done");
      const loop = items.find((i) => i.origin === "maintain-loop");
      const L = c.live;
      const cards = [];
      if (o.waiting.length) cards.push(["#/", fill(L.waiting[0], { n: o.waiting.length }), L.waiting[1]]);
      if (t3) {
        const k = t3.awaiting[0], a = t3.chain[k];
        cards.push([`#/work/${t3.id}`, fill(L.t3[0], { id: t3.id }), fill(L.t3[1], { title: t3.title, kind: k, need: a.needed, have: a.approvals.length })]);
      }
      if (done) cards.push([`#/work/${done.id}`, fill(L.done[0], { id: done.id }), L.done[1]]);
      if (loop) cards.push([`#/work/${loop.id}`, fill(L.loop[0], { id: loop.id }), L.loop[1]]);
      if (o.gate_wait_hours.count) cards.push(["#/", fill(L.wait[0], { h: o.gate_wait_hours.median }), fill(L.wait[1], { n: o.gate_wait_hours.count })]);
      document.getElementById("intro-live").innerHTML = cards.length
        ? cards.map(([href, h, p]) => `<a class="card live-card" href="${href}"><b>${esc(h)}</b><span>${esc(p)}</span><span class="go">${esc(c.open)}</span></a>`).join("")
        : `<div class="empty">${esc(c.liveEmpty)}</div>`;
    } catch (err) {
      document.getElementById("intro-live").innerHTML = `<div class="empty">${esc(fill(c.liveFail, { msg: err.message }))}</div>`;
    }
  });
})();
