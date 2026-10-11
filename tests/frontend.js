/* Browser regressions against scripts/check_frontend.py's isolated repository.
   SDLC_PLAYWRIGHT=absolute/module/path node tests/frontend.js URL REPO */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require(process.env.SDLC_PLAYWRIGHT || "playwright");
const [base, repo] = process.argv.slice(2);
const output = process.env.SDLC_SCREENSHOTS || "/private/tmp/ai-sdlc-frontend-qa";
const payload = "# Browser draft\n\n## Problem\nFinding work is slow.\n\n## Desired outcome\nFind work in 10 seconds.\n";

async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.SDLC_CHROMIUM ? { executablePath: process.env.SDLC_CHROMIUM } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "en-US" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  const ready = () => page.waitForFunction(() => document.querySelector("#view") && !document.querySelector("#view").hasAttribute("aria-busy"));
  const go = async (hash, lang = "en") => { await page.goto(`${base}/?lang=${lang}#${hash}`); await ready(); };
  const nav = async (name) => { await page.locator(`.nav [data-route="${name}"]`).click(); await ready(); };
  const text = (selector) => page.locator(selector).innerText();
  const count = (selector) => page.locator(selector).count();
  const check = async (name, fn) => { await fn(); assert.deepEqual(errors, [], name); console.log(`PASS ${name}`); };
  const getWork = async (id) => (await context.request.get(`${base}/api/work/${id}`)).json();
  const post = (url, data) => context.request.post(`${base}${url}`, { data, headers: { "X-SDLC": "1" } });
  await fs.mkdir(output, { recursive: true });
  let workId, draftFile;
  try {
    await check("W-0005:AC-1 board filters, sorting, URLs, history and overview links", async () => {
      await go("/board");
      assert.equal(await count(".wcard"), 5);
      await page.locator("#filter-q").fill("refund");
      await page.locator("#filter-stage").selectOption("spec");
      await page.locator("#filter-tier").selectOption("T3");
      await page.locator("#filter-focus").selectOption("waiting");
      assert.equal(await count(".wcard"), 1);
      assert.match(await text(".wcard"), /W-0002/);
      await page.getByRole("button", { name: "List", exact: true }).click();
      assert.equal(await count("#board-results tbody tr"), 1);
      await page.reload(); await ready();
      assert.equal(await page.locator("#filter-q").inputValue(), "refund");
      assert.equal(await page.locator("#filter-tier").inputValue(), "T3");
      assert.equal(await count("#board-results tbody tr"), 1);
      await page.getByRole("button", { name: "한국어", exact: true }).click(); await ready();
      assert.equal(await page.locator("#filter-q").inputValue(), "refund");
      assert.equal(await count("#board-results tbody tr"), 1);
      await page.getByRole("button", { name: "English", exact: true }).click(); await ready();
      await page.locator("[data-reset]").click();
      await page.locator("#filter-sort").selectOption("title");
      const titles = await page.locator("#board-results tbody td:first-child").allTextContents();
      const names = titles.map((s) => s.trim().replace(/^W-\d+\s*/, ""));
      assert.deepEqual(names, [...names].sort((a, b) => a.localeCompare(b, "en-US")));
      for (const order of ["oldest", "newest"]) {
        await page.locator("#filter-sort").selectOption(order);
        const ids = await page.locator("#board-results tbody td:first-child .mono").allTextContents();
        const sorted = [...ids].sort((a, b) => a.localeCompare(b));
        assert.deepEqual(ids, order === "oldest" ? sorted : sorted.reverse());
      }
      await page.locator("#filter-sort").selectOption("risk");
      const tiers = await page.locator("#board-results tbody td:nth-child(3) .chip").allTextContents();
      assert.deepEqual(tiers, [...tiers].sort().reverse());
      await page.locator("#filter-focus").selectOption("untraced");
      assert.equal(await count("#board-results tbody tr"), 2);
      await page.locator("#filter-focus").selectOption("issues");
      assert.equal(await count("#board-results tbody tr"), 0);
      assert.match(await text("#board-results"), /No items match/);
      await page.goBack(); await ready();
      assert.equal(await page.locator("#filter-focus").inputValue(), "untraced");
      assert.equal(await count("#board-results tbody tr"), 2);
      await page.goForward(); await ready();
      assert.equal(await page.locator("#filter-focus").inputValue(), "issues");
      await nav("overview");
      assert.equal(await count(".tiles > .tile"), 5);
      await page.locator('.pipe[href="#/board?stage=spec"]').click(); await ready();
      assert.equal(await page.locator("#filter-stage").inputValue(), "spec");
      assert.equal(await count(".wcard"), 1);
      await nav("overview");
      await page.locator('a[href="#/board?focus=waiting"]').click(); await ready();
      assert.equal(await count(".wcard"), 3);
    });

    await check("W-0005:AC-7 duplicate creation and failed request recovery", async () => {
      await page.locator("#new-work").click();
      await page.locator("#nf-title").fill("Browser draft");
      await page.locator("#nf-owner").fill("Dana <dana@example.com>");
      await page.route("**/api/work", async (route) => route.request().method() === "POST"
        ? route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "Test failure" }) }) : route.continue());
      await page.locator('#new-form button[type="submit"]').click();
      await page.locator("#nf-err").waitFor({ state: "visible" });
      assert.equal(await page.locator("#nf-title").inputValue(), "Browser draft");
      assert.equal(await page.locator('#new-form button[type="submit"]').isEnabled(), true);
      await page.unroute("**/api/work");
      let release;
      const gate = new Promise((resolve) => { release = resolve; });
      let requests = 0;
      await page.route("**/api/work", async (route) => {
        if (route.request().method() !== "POST") return route.continue();
        requests++; await gate; return route.continue();
      });
      const sent = page.waitForRequest((r) => r.url().endsWith("/api/work") && r.method() === "POST");
      await page.locator('#new-form button[type="submit"]').click(); await sent;
      await page.locator("#nf-title").press("Enter");
      assert.equal(await page.locator('#new-form button[type="submit"]').isEnabled(), false);
      release();
      await page.locator("#draft-body").waitFor(); await ready();
      assert.equal(requests, 1);
      workId = page.url().match(/work\/(W-\d+)/)[1];
      draftFile = path.join(repo, (await getWork(workId)).chain.intent.path);
      await page.unroute("**/api/work");
    });

    await check("W-0005:AC-2 W-0005:AC-4 W-0005:AC-5 editing, safe preview, tabs and unsaved guards", async () => {
      const evil = '<script>window.previewAttack = true</script><img src=x onerror="window.previewAttack=true">';
      await page.locator("#draft-body").fill(payload + evil);
      assert.equal(await page.locator("#draft-preview script, #draft-preview img").count(), 0);
      assert.equal(await page.evaluate(() => window.previewAttack), undefined);
      assert.match(await text("#draft-preview"), /<script>/);
      await page.locator("#tab-intent").focus();
      await page.keyboard.press("Home");
      assert.equal(await page.locator("#tab-audit").getAttribute("aria-selected"), "true");
      assert.equal(await page.locator("#tab-intent").getAttribute("tabindex"), "-1");
      await page.keyboard.press("End");
      assert.equal(await page.locator("#draft-body").inputValue(), payload + evil);
      assert.equal(await page.locator("#tab-body").getAttribute("aria-labelledby"), "tab-intent");
      await page.keyboard.press("ArrowRight");
      assert.equal(await page.locator("#tab-audit").getAttribute("aria-selected"), "true");
      await page.keyboard.press("ArrowLeft");
      assert.equal(await page.locator("#draft-body").inputValue(), payload + evil);
      await page.getByRole("button", { name: "한국어", exact: true }).click(); await ready();
      assert.equal(await page.locator("#draft-body").inputValue(), payload + evil);
      await page.getByRole("button", { name: "English", exact: true }).click(); await ready();
      await page.locator("#refresh").click(); await ready();
      assert.equal(await page.locator("#draft-body").inputValue(), payload + evil);
      const dialog = page.waitForEvent("dialog");
      const click = page.locator('.nav [data-route="board"]').click();
      await (await dialog).dismiss(); await click;
      assert.match(page.url(), new RegExp(`work/${workId}`));
      assert.equal(await page.locator("#draft-body").inputValue(), payload + evil);
      await page.locator("#draft-body").fill(payload);
      await page.locator("[data-add-source]").click();
      await page.locator("#source-kind-0").fill("metric");
      await page.locator("#source-ref-0").fill("Remove me");
      await page.locator("[data-add-source]").click();
      await page.locator("#source-ref-1").fill("BROWSER-1");
      await page.getByRole("button", { name: "Remove evidence 1", exact: true }).click();
      await page.locator("#source-ref-0").fill("BROWSER-1");
      await page.locator('[data-act="submit"][data-kind="intent"]').click();
      assert.match(await text("#toast"), /Save your changes/);
      assert.equal((await getWork(workId)).chain.intent.status, "draft");
      await page.locator("#draft-save").click();
      await page.locator("#draft-state").filter({ hasText: "Saved" }).waitFor(); await ready();
      const saved = await getWork(workId);
      assert.equal(saved.chain.intent.body, payload);
      assert.deepEqual(saved.chain.intent.meta.sources, [{ kind: "ticket", ref: "BROWSER-1" }]);
      assert.match(await fs.readFile(draftFile, "utf-8"), /BROWSER-1/);
      await page.reload(); await ready();
      assert.equal(await page.locator("#draft-body").inputValue(), payload);
      assert.equal(await page.locator("#tab-intent").getAttribute("aria-selected"), "true");
    });

    await check("W-0005:AC-4 W-0005:AC-7 stale save, failures and duplicate save/submit", async () => {
      await page.locator("#draft-body").fill(payload + "\nLocal edit\n");
      const external = (await fs.readFile(draftFile, "utf-8")) + "\nExternal edit\n";
      await fs.writeFile(draftFile, external);
      await page.locator("#draft-save").click();
      await page.locator("[data-reload]").waitFor({ state: "visible" });
      assert.match(await page.locator("#draft-body").inputValue(), /Local edit/);
      assert.equal(await fs.readFile(draftFile, "utf-8"), external);
      const confirm = page.waitForEvent("dialog"); const click = page.locator("[data-reload]").click();
      await (await confirm).accept(); await click; await ready();
      assert.match(await page.locator("#draft-body").inputValue(), /External edit/);
      await page.locator("#draft-body").fill(payload + "\nRetry save\n");
      await page.route(`**/api/work/${workId}/draft`, (route) => route.fulfill({ status: 500, contentType: "application/json", body: '{"error":"Save unavailable"}' }));
      await page.locator("#draft-save").click();
      await page.locator("#draft-error").waitFor({ state: "visible" });
      assert.match(await page.locator("#draft-body").inputValue(), /Retry save/);
      assert.equal(await page.locator("#draft-save").isEnabled(), true);
      await page.unroute(`**/api/work/${workId}/draft`);
      for (const action of ["draft", "submit"]) {
        let release; const gate = new Promise((resolve) => { release = resolve; }); let requests = 0;
        await page.route(`**/api/work/${workId}/${action}`, async (route) => { requests++; await gate; return route.continue(); });
        const sent = page.waitForRequest((r) => r.url().endsWith(`/${workId}/${action}`));
        const response = page.waitForResponse((r) => r.url().endsWith(`/${workId}/${action}`));
        const button = action === "draft" ? page.locator("#draft-save") : page.locator('[data-act="submit"][data-kind="intent"]');
        await button.click(); await sent;
        await page.keyboard.press("Enter");
        assert.equal(await button.isEnabled(), false);
        release();
        await (await response).finished();
        if (action === "draft") { await page.locator("#draft-state").filter({ hasText: "Saved" }).waitFor(); await ready(); }
        else { await page.locator("#tab-body > .doc").waitFor(); await ready(); }
        assert.equal(requests, 1);
        await page.unroute(`**/api/work/${workId}/${action}`);
      }
      assert.equal((await getWork(workId)).chain.intent.status, "proposed");
      assert.equal(await count("#draft-body"), 0);
    });

    await check("W-0005:AC-6 branch comparison and collection filters", async () => {
      await nav("branch");
      await page.locator("#branch-base").fill("does-not-exist");
      await page.locator('#branch-form button[type="submit"]').click();
      await page.locator("#branch-results [role=alert]").waitFor();
      assert.equal(await page.locator("#branch-base").inputValue(), "does-not-exist");
      await page.locator("#branch-base").fill("main");
      await page.locator('#branch-form button[type="submit"]').click();
      await page.locator("#branch-results .tiles").waitFor();
      assert.match(page.url(), /base=main/);
      assert.match(await text("#branch-results"), /T1/);
      await nav("incidents");
      assert.equal(await count("#incident-results tbody tr"), 1);
      await page.locator("#filter-status").selectOption("closed");
      assert.match(await text("#incident-results"), /No items match/);
      await page.getByRole("button", { name: "Reset filters" }).click();
      await page.locator("#filter-q").fill("checkout");
      assert.equal(await count("#incident-results tbody tr"), 1);
      await nav("lessons");
      assert.equal(await count(".lesson"), 3);
      await page.locator("#filter-status").selectOption("open");
      assert.equal(await count(".lesson"), 1);
      await page.locator("#filter-detector").selectOption("gate");
      assert.equal(await count(".lesson"), 1);
      await page.locator("#filter-q").fill("not found");
      assert.match(await text("#lesson-results"), /No items match/);
      await page.getByRole("button", { name: "Reset filters" }).click();
      assert.equal(await count(".lesson"), 3);
    });

    await check("W-0005:AC-7 late responses cannot replace the latest route/title", async () => {
      let release; const gate = new Promise((resolve) => { release = resolve; });
      await page.route("**/api/work/W-0001", async (route) => { await gate; await route.continue(); });
      const sent = page.waitForRequest((r) => r.url().endsWith("/api/work/W-0001"));
      await page.goto(`${base}/?lang=en#/work/W-0001`); await sent;
      await nav("incidents");
      const finished = page.waitForResponse((r) => r.url().endsWith("/api/work/W-0001"));
      release(); await finished;
      assert.equal(await text("#title"), "Incidents");
      assert.equal(await count("#incident-results tbody tr"), 1);
      await page.unroute("**/api/work/W-0001");
      let releaseIntro; const introGate = new Promise((resolve) => { releaseIntro = resolve; });
      await page.route("**/api/work", async (route) => { await introGate; await route.continue(); });
      const introSent = page.waitForRequest((r) => r.url().endsWith("/api/work"));
      await page.goto(`${base}/?lang=en#/intro`); await introSent;
      await nav("incidents");
      const introFinished = page.waitForResponse((r) => r.url().endsWith("/api/work"));
      releaseIntro(); await introFinished;
      assert.equal(await text("#title"), "Incidents");
      await page.unroute("**/api/work");
      await page.route("**/api/work", (route) => route.fulfill({ status: 503, contentType: "application/json", body: '{"error":"Unavailable"}' }));
      await nav("board");
      await page.locator("[data-retry]").waitFor();
      await page.unroute("**/api/work");
      await page.locator("[data-retry]").click(); await ready();
      assert.equal(await count(".wcard"), 6);
    });

    await check("W-0005:AC-8 mobile/desktop, ko/en, light/dark and reduced motion", async () => {
      const created = await (await post("/api/work", { title: "Responsive editor", owner: "Dana", tier: "T1" })).json();
      const editable = await getWork(created.id);
      assert.equal((await post(`/api/work/${created.id}/draft`, { stage: "intent", body: payload,
        sources: [{ kind: "ticket", ref: "RESPONSIVE-1" }], revision: editable.chain.intent.revision })).status(), 200);
      for (const width of [375, 1440]) for (const lang of ["ko", "en"]) for (const scheme of ["light", "dark"]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
        for (const route of ["/", "/intro", "/board", `/work/${workId}`, `/work/${created.id}?tab=intent`, "/branch", "/incidents", "/lessons"]) {
          await go(route, lang);
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${route} ${width} ${lang} ${scheme}`);
          assert.equal(await page.locator('#view input:not([type="hidden"]), #view select, #view textarea').evaluateAll((inputs) => inputs.every((input) => input.labels.length > 0)), true);
          assert.doesNotMatch(await text("#view"), /\bui\.[A-Za-z]+/);
        }
        await go("/board", lang);
        await page.screenshot({ path: path.join(output, `board-${width}-${lang}-${scheme}.png`), fullPage: true });
        await go(`/work/${created.id}?tab=intent`, lang);
        await page.screenshot({ path: path.join(output, `editor-${width}-${lang}-${scheme}.png`), fullPage: true });
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
      await go("/board");
      assert.equal(await page.locator(".wcard").first().evaluate((el) => getComputedStyle(el).transitionDuration), "0s");
      await page.locator("#filter-q").focus();
      assert.equal(await page.locator("#filter-q").evaluate((el) => getComputedStyle(el).outlineStyle), "solid");
      await page.keyboard.press("Tab");
      assert.equal(await page.locator("#filter-stage").evaluate((el) => el === document.activeElement), true);
    });
    console.log(`Frontend checks passed; screenshots: ${output}`);
  } catch (error) {
    console.error("Overflow diagnostics:", await page.locator("body *").evaluateAll((elements) => elements
      .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1 && !el.closest(".board,.table-wrap,.nav"))
      .slice(0, 12).map((el) => ({ tag: el.tagName, class: el.className, width: el.getBoundingClientRect().width, right: el.getBoundingClientRect().right }))));
    await page.screenshot({ path: path.join(output, "failure.png"), fullPage: true });
    throw error;
  } finally { await browser.close(); }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
