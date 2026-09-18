/* Stage icons (24px line, currentColor) and the ai-sdlc mark. Shared by the web app; the product site inlines a copy. */
const ICONS = (() => {
  const PATHS = {
    plan: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    design: '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M4 10h16M10 10v10"/>',
    build: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 5l-3 14"/>',
    test: '<path d="M9 3h6M10 3v6.2L5.3 17.4A2.4 2.4 0 0 0 7.4 21h9.2a2.4 2.4 0 0 0 2.1-3.6L14 9.2V3"/><path d="M7.4 15h9.2"/>',
    deploy: '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5"/><path d="M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/>',
    maintain: '<path d="M3 12h4l2.2-5.5 4.4 11 2.2-5.5H21"/>',
  };
  // board columns and artifacts map onto stages
  const ALIAS = { intent: "plan", spec: "design", done: "deploy", rejected: "maintain" };
  const stage = (name, cls = "ico") => {
    const key = ALIAS[name] || String(name).toLowerCase();
    const p = PATHS[key];
    return p ? `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>` : "";
  };
  const COLORS = ["var(--st-plan)", "var(--st-design)", "var(--st-build)", "var(--st-test)", "var(--st-deploy)", "var(--st-maintain)"];
  const mark = (size = 26) => {
    const arc = (i) => {
      const a0 = ((-90 + i * 60 + 4.5) * Math.PI) / 180, a1 = ((-90 + (i + 1) * 60 - 4.5) * Math.PI) / 180;
      const p = (a) => `${(32 + 19 * Math.cos(a)).toFixed(2)} ${(32 + 19 * Math.sin(a)).toFixed(2)}`;
      return `<path d="M${p(a0)}A19 19 0 0 1 ${p(a1)}" fill="none" stroke="${COLORS[i]}" stroke-width="7"/>`;
    };
    return `<svg width="${size}" height="${size}" viewBox="0 0 64 64" aria-hidden="true">${[0, 1, 2, 3, 4, 5].map(arc).join("")}<circle cx="32" cy="32" r="5.2" fill="var(--gate)"/></svg>`;
  };
  return { stage, mark, PATHS };
})();
