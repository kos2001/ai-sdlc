/* Research-driven navigation, tested on the runner's isolated repository only. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require(process.env.SDLC_PLAYWRIGHT || "playwright");
const [base, repo] = process.argv.slice(2);
const output = process.env.SDLC_SCREENSHOTS || "/private/tmp/ai-sdlc-frontend-qa";

async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.SDLC_CHROMIUM ? { executablePath: process.env.SDLC_CHROMIUM } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "en-US" });
  const errors = [], posts = [];
  const track = async (ctx) => {
    ctx.on("page", (page) => { page.on("pageerror", (e) => errors.push(e.message)); page.on("request", (r) => { if (r.method() === "POST") posts.push(r.url()); }); });
    await ctx.route("https://fonts.googleapis.com/**", (r) => r.abort());
    await ctx.route("https://fonts.gstatic.com/**", (r) => r.abort());
  };
  await track(context);
  const page = await context.newPage();
  const ready = (p = page) => p.waitForFunction(() => document.querySelector("#board-filters") && !document.querySelector("#view").hasAttribute("aria-busy"));
  const go = async (hash = "/board", lang = "en", p = page) => { await p.goto(`${base}/?lang=${lang}#${hash}`); if (hash.startsWith("/board")) await ready(p); };
  const ids = () => page.locator("#board-results .wcard .id, #board-results tbody td:first-child .mono").allTextContents().then((rows) => rows.map((s) => s.match(/W-\d+/)[0]).sort());
  const check = async (name, fn) => { await fn(); assert.deepEqual(errors, []); console.log(`PASS ${name}`); };
  const overview = await (await context.request.get(`${base}/api/overview`)).json();
  const items = await (await context.request.get(`${base}/api/work`)).json();
  const key = `sdlc.personal.v1.${overview.workspace_id}`;
  const saved = () => page.evaluate((k) => JSON.parse(localStorage.getItem(k)), key);
  const before = new Map();
  for (const w of items) for (const a of Object.values(w.chain)) if (a) before.set(a.path, await fs.readFile(path.join(repo, a.path), "utf-8"));
  let viewId;
  try {
    await check("W-0005:AC-1 structured query, quoted phrases, OR, negation and errors", async () => {
      await go();
      const query = page.locator("#filter-q");
      await query.fill('stage:spec tier:T3 owner:"Dana Park"'); assert.deepEqual(await ids(), ["W-0002"]);
      await query.fill("stage:spec,done -tier:T1"); assert.deepEqual(await ids(), ["W-0001", "W-0002"]);
      await query.fill("id:W-0002"); assert.deepEqual(await ids(), ["W-0002"]);
      await query.fill('"Refund webhook"'); assert.deepEqual(await ids(), ["W-0002"]);
      await query.fill("is:waiting -tier:T3"); assert.deepEqual(await ids(), items.filter((w) => w.awaiting.length && w.tier !== "T3").map((w) => w.id).sort());
      await query.fill("stage:unknown"); assert.equal(await page.locator("#search-error").isVisible(), true); assert.deepEqual(await ids(), []);
      await query.fill('owner:"Dana'); assert.match(await page.locator("#search-error").innerText(), /quotation/);
      await query.fill("unknown:term"); assert.equal(await page.locator("#search-error").isVisible(), false); assert.deepEqual(await ids(), []);
      for (const text of ["O'Brien", "owner:O'Brien", "don't", "-"]) {
        await query.fill(text); assert.equal(await page.locator("#search-error").isVisible(), false, "natural apostrophes remain literal text");
      }
      await query.fill(""); assert.equal((await ids()).length, items.length);
    });
    await check("W-0005:AC-1 saved view CRUD, dirty filters, rename, reload and shared URL", async () => {
      await page.locator("#filter-q").fill("refund"); await page.locator("#filter-tier").selectOption("T3");
      await page.locator('[data-layout="list"]').click();
      await page.locator("#view-name").fill("Approval queue"); await page.locator('#saved-view-form button[type="submit"]').click();
      viewId = await page.locator("#saved-view").inputValue(); assert.ok(viewId);
      await page.locator("#filter-q").fill("W-0001"); await page.locator("#filter-tier").selectOption("");
      assert.match(await page.locator("#view-state").innerText(), /differ/);
      await page.locator("#view-name").fill("Release queue"); await page.locator("[data-view-rename]").click();
      assert.equal(await page.locator("#filter-q").inputValue(), "W-0001", "renaming preserves unsaved filters");
      assert.equal((await saved()).views[0].state.q, "refund");
      await page.locator("[data-view-update]").click();
      assert.equal((await saved()).views[0].state.q, "W-0001");
      await go(); await page.locator("#saved-view").selectOption(viewId);
      assert.equal(await page.locator("#filter-q").inputValue(), "W-0001");
      assert.equal(await page.locator("#filter-tier").inputValue(), "");
      assert.equal(await page.locator('[data-layout="list"]').getAttribute("aria-pressed"), "true");
      await page.reload(); await ready(); assert.equal(await page.locator("#saved-view").inputValue(), viewId);
      await page.locator("[data-view-share]").click(); const link = await page.locator("#view-link").inputValue();
      assert.doesNotMatch(link, /saved=/); assert.match(link, /q=W-0001/);
      const fresh = await browser.newContext(); await track(fresh); const shared = await fresh.newPage();
      await shared.goto(link); await ready(shared); assert.equal(await shared.locator("#board-results tbody tr").count(), 1);
      assert.equal(await shared.locator("#saved-view option").count(), 1); await fresh.close();
      await page.locator("#view-name").fill("release queue"); await page.locator('#saved-view-form button[type="submit"]').click();
      assert.match(await page.locator("#view-error").innerText(), /already exists/);
      await page.locator("#view-name").fill('<img src=x onerror="window.viewAttack=1">'); await page.locator("[data-view-rename]").click();
      assert.equal(await page.locator("#saved-views img").count(), 0); assert.equal(await page.evaluate(() => window.viewAttack), undefined);
      const cancelled = page.waitForEvent("dialog"); const cancelClick = page.locator("[data-view-delete]").click();
      await (await cancelled).dismiss(); await cancelClick; assert.equal((await saved()).views.length, 1);
      const confirmed = page.waitForEvent("dialog"); const deleteClick = page.locator("[data-view-delete]").click();
      await (await confirmed).accept(); await deleteClick; assert.equal((await saved()).views.length, 0);
      assert.equal(await page.locator("#filter-q").inputValue(), "W-0001");
      await page.locator("[data-reset]").click(); await page.locator("#filter-stage").selectOption("spec");
      await page.locator("#view-name").fill("My spec queue"); await page.locator('#saved-view-form button[type="submit"]').click();
      viewId = await page.locator("#saved-view").inputValue();
    });
    await check("W-0005:AC-1 W-0005:AC-5 favorites, recent work and personalized quick switch", async () => {
      await go(); await page.locator('[data-favorite="W-0002"]').click();
      await page.locator("#filter-focus").selectOption("favorite"); assert.deepEqual(await ids(), ["W-0002"]);
      await page.locator('[data-favorite="W-0002"]').click(); assert.deepEqual(await ids(), []);
      assert.equal(await page.locator("#filter-q").evaluate((el) => el === document.activeElement), true);
      await page.locator("[data-reset]").click(); await page.locator('[data-favorite="W-0001"]').click();
      await page.locator('[data-layout="list"]').click(); await page.locator('[data-favorite="W-0002"]').click();
      await page.locator('#board-results tbody tr').filter({ hasText: "W-0002" }).locator('td:first-child a').click();
      await page.locator('#tab-spec').waitFor();
      assert.equal(await page.locator('[data-favorite="W-0002"]').getAttribute("aria-pressed"), "true");
      await page.locator('[data-favorite="W-0002"]').click(); await page.reload(); await page.locator('#tab-spec').waitFor();
      assert.equal(await page.locator('[data-favorite="W-0002"]').getAttribute("aria-pressed"), "false");
      assert.deepEqual((await saved()).favorites, ["W-0001"]); assert.equal((await saved()).recent[0], "W-0002");
      await page.keyboard.press("Control+k"); await page.waitForFunction(() => !document.querySelector('#quick-results').hasAttribute('aria-busy'));
      assert.match(await page.locator('#quick-results [role=option]').first().innerText(), /W-0001.*\nFavorite/s);
      await page.locator("#quick-input").fill("My spec queue"); await page.keyboard.press("Enter"); await ready();
      assert.equal(await page.locator("#filter-stage").inputValue(), "spec"); assert.equal(await page.locator("#saved-view").inputValue(), viewId);
      await page.locator("[data-reset]").click(); await page.locator("#filter-q").fill("is:favorite"); assert.deepEqual(await ids(), ["W-0001"]);
      await page.locator("#filter-q").fill("is:recent"); assert.deepEqual(await ids(), ["W-0002"]);
    });
    await check("W-0005:AC-1 same-name workspace isolation", async () => {
      const original = await saved();
      await page.route("**/api/overview", (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ ...overview, workspace_id: "b".repeat(64) }) }));
      await go(); await page.reload(); await ready(); // workspace identity reload
      assert.equal(await page.locator("#saved-view option").count(), 1);
      assert.equal(await page.locator('[data-favorite="W-0001"]').getAttribute("aria-pressed"), "false");
      await page.locator('[data-favorite="W-0002"]').click(); assert.deepEqual(await saved(), original);
      await page.unroute("**/api/overview"); await go(); await page.reload(); await ready();
      assert.equal(await page.locator('[data-favorite="W-0001"]').getAttribute("aria-pressed"), "true");
      assert.equal(await page.locator("#saved-view option").count(), 2);
    });
    await check("W-0005:AC-7 corrupt preferences and blocked browser storage", async () => {
      await page.evaluate((k) => localStorage.setItem(k, "{broken"), key); await go(); await page.reload(); await ready();
      assert.match(await page.locator("#view-state").innerText(), /Corrupt/);
      await page.locator("#view-name").fill("Recovered"); await page.locator('#saved-view-form button[type="submit"]').click();
      assert.equal((await saved()).version, 1);
      const recovered = await saved();
      await page.evaluate(({ key, value }) => localStorage.setItem(key, JSON.stringify({ ...value, favorites: Array.from({ length: 100 }, (_, i) => `W-${9000+i}`) })), { key, value: recovered });
      await go(); await page.reload(); await ready(); await page.locator('[data-favorite="W-0002"]').click();
      assert.equal(await page.locator('[data-favorite="W-0002"]').getAttribute('aria-pressed'), 'false');
      assert.match(await page.locator('#toast').innerText(), /100 favorites/);
      assert.equal((await saved()).favorites.length, 100);
      await page.evaluate(({ key, value }) => localStorage.setItem(key, JSON.stringify(value)), { key, value: recovered }); await go(); await page.reload(); await ready();
      for (const mode of ["read", "write"]) {
        const blocked = await browser.newContext(); await track(blocked);
        await blocked.addInitScript((mode) => {
          if (mode === "read") Storage.prototype.getItem = () => { throw new DOMException("Blocked", "SecurityError"); };
          Storage.prototype.setItem = () => { throw new DOMException("Full", "QuotaExceededError"); };
        }, mode);
        const p = await blocked.newPage(); await go("/board", "en", p);
        await p.locator('[data-favorite="W-0002"]').click(); assert.equal(await p.locator('[data-favorite="W-0002"]').getAttribute("aria-pressed"), "true");
        await p.locator("#view-name").fill("In memory"); await p.locator('#saved-view-form button[type="submit"]').click();
        assert.match(await p.locator("#view-state").innerText(), /only in this tab/);
        await p.locator('.nav [data-route="incidents"]').click(); await p.locator('#incident-results').waitFor();
        await p.locator('.nav [data-route="board"]').click(); await ready(p); assert.equal(await p.locator('#saved-view option').count(), 2);
        await p.reload(); await ready(p); assert.equal(await p.locator('#saved-view option').count(), 1);
        await blocked.close();
      }
    });
    await check("W-0005:AC-5 W-0005:AC-7 cross-tab sync preserves draft input", async () => {
      await go(); const other = await context.newPage(); await go("/board", "en", other);
      await page.locator('[data-favorite="W-0002"]').click();
      await other.waitForFunction(() => document.querySelector('[data-favorite="W-0002"]').getAttribute('aria-pressed') === 'true');
      const draft = items.find((w) => Object.values(w.chain).some((a) => a?.status === "draft")); assert.ok(draft);
      const kind = Object.entries(draft.chain).find(([, a]) => a?.status === "draft")[0];
      await go(`/work/${draft.id}?tab=${kind}`, "en", other); await other.locator('#draft-body').waitFor();
      const body = (await other.locator('#draft-body').inputValue()) + '\nKeep this local input\n';
      await other.locator('#draft-body').fill(body); await page.locator('[data-favorite="W-0001"]').click();
      await other.waitForFunction(() => Preferences.isFavorite('W-0001'));
      assert.equal(await other.locator('#draft-body').inputValue(), body);
      const confirm = other.waitForEvent('dialog'); await other.keyboard.press('Control+k'); await other.locator('#quick-input').fill('Recovered');
      const enter = other.locator('#quick-input').press('Enter'); await (await confirm).dismiss(); await enter;
      assert.equal(await other.locator('#draft-body').inputValue(), body);
      await other.close({ runBeforeUnload: false });
    });
    await check("W-0005:AC-8 saved views and shortcuts fit locales, themes and mobile", async () => {
      await fs.mkdir(output, { recursive: true });
      for (const width of [375, 1440]) for (const lang of ["ko", "en"]) for (const scheme of ["light", "dark"]) {
        await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 }); await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce' });
        await go('/board', lang); await page.locator('.personal-panel summary').click(); await page.locator('.search-help summary').click();
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${width} ${lang} ${scheme}`);
        assert.equal(await page.locator('#view input,#view select').evaluateAll((fields) => fields.every((f) => f.labels.length)), true);
        assert.doesNotMatch(await page.locator('#view').innerText(), /\b(personal|views|search)\.[A-Za-z]+/);
        await page.screenshot({ path: path.join(output, `saved-${width}-${lang}-${scheme}.png`), fullPage: true });
        await page.locator('#quick-open').click(); await page.waitForFunction(() => !document.querySelector('#quick-results').hasAttribute('aria-busy'));
        assert.equal(await page.locator('#quick-dialog').evaluate((el) => { const r=el.getBoundingClientRect(); return r.left>=0 && r.right<=innerWidth && r.bottom<=innerHeight; }), true);
        await page.screenshot({ path: path.join(output, `personal-quick-${width}-${lang}-${scheme}.png`), fullPage: true });
        await page.keyboard.press('Escape');
      }
    });
    assert.deepEqual(posts, [], 'Personal navigation sends no artifact mutations');
    for (const [relative, content] of before) assert.equal(await fs.readFile(path.join(repo, relative), 'utf-8'), content, relative);
    console.log('Discovery checks passed; no POSTs and all work files preserved');
  } catch (error) {
    await page.screenshot({ path: path.join(output, 'discovery-failure.png'), fullPage: true }); throw error;
  } finally { await browser.close(); }
}
main().catch((err) => { console.error(err); process.exitCode = 1; });
