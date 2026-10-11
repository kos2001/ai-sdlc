/* Shared native, labelled controls; URL state is per screen. */
const Filters = (() => {
  const { esc, t } = App;
  const select = (name, label, options, value = "") => `<label class="field" for="filter-${name}"><span>${esc(t(label))}</span>
    <select id="filter-${name}" name="${esc(name)}">${options.map(([v, text]) => `<option value="${esc(v)}" ${value === v ? "selected" : ""}>${esc(text)}</option>`).join("")}</select></label>`;
  const search = (value = "", placeholder = "ui.searchPh") => `<label class="field search-field" for="filter-q"><span>${esc(t("ui.search"))}</span>
    <input id="filter-q" type="search" name="q" value="${esc(value)}" placeholder="${esc(t(placeholder))}" autocomplete="off"></label>`;
  const all = () => [["", t("ui.all")]];
  const result = (n, total) => `<p class="result-count" role="status">${esc(t("ui.results", { n, total }))}</p>`;
  return { select, search, all, result };
})();
