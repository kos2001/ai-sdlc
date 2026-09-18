/* View: the full product story (/about) inside the app. The page runs in embed mode: the app owns navigation and language. */
(() => {
  const { esc, t, route, setTitle } = App;

  route(/^\/guide(?:\/(\w+))?$/, "guide", async (view, m) => {
    setTitle(t("gd.crumb"), t("gd.title"));
    const section = m && m[1] ? `#${m[1]}` : "";
    view.innerHTML = `
      <p class="muted guide-lede">${esc(t("gd.lede"))} <a href="/about?lang=${I18N.lang}${section}" target="_blank" rel="noopener">${esc(t("gd.open"))}</a></p>
      <iframe class="guide" src="/about?embed=1&amp;lang=${I18N.lang}${section}" title="${esc(t("gd.title"))}" loading="eager"></iframe>`;
  });
})();
