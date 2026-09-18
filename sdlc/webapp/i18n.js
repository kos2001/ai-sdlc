/* Korean / English. Language: ?lang= > saved choice > browser language. Korean strings live here, English in i18n-en.js. */
const I18N = (() => {
  const dict = { ko: {}, en: {} };
  const LANGS = ["ko", "en"];
  const pick = () => {
    try {
      const q = new URLSearchParams(location.search).get("lang");
      if (LANGS.includes(q)) return q;
      const saved = localStorage.getItem("sdlc.lang");
      if (LANGS.includes(saved)) return saved;
    } catch { /* storage may be blocked */ }
    return (navigator.language || "").toLowerCase().startsWith("ko") ? "ko" : "en";
  };
  let lang = pick();

  const t = (key, vars = {}) => String(dict[lang][key] ?? dict.ko[key] ?? key).replace(/\{(\w+)\}/g, (_, n) => (vars[n] ?? ""));

  function apply() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
    document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  }

  function set(next) {
    if (!LANGS.includes(next) || next === lang) return;
    lang = next;
    try { localStorage.setItem("sdlc.lang", next); } catch { /* per-viewer convenience only */ }
    apply();
    window.dispatchEvent(new Event("langchange"));
  }

  return { t, apply, set, add: (l, entries) => Object.assign(dict[l], entries), get lang() { return lang; }, get locale() { return lang === "ko" ? "ko-KR" : "en-US"; } };
})();

I18N.add("ko", {
  "lang.label": "언어", "nav.guide": "가이드 · 전체 이야기",
  "gd.crumb": "Guide", "gd.title": "AI-native SDLC 가이드", "gd.lede": "병목의 이동부터 루프, 단계별 비교, 실제 저장소 측정값, 12개 플레이, 거버넌스까지 한 페이지에 담았습니다.", "gd.open": "새 창에서 열기 ↗",
  "nav.intro": "소개 · 무엇이 다른가", "nav.overview": "개요", "nav.board": "작업 보드", "nav.branch": "브랜치 점검", "nav.incidents": "인시던트",
  "side.repo": "저장소", "side.about": "ai-sdlc 소개 ↗", "top.refresh": "새로고침", "top.new": "새 작업",
  "new.h": "새 작업 — 의도 초안", "new.lede": "intent.md 초안(draft)을 만듭니다. 근거와 문제를 채운 뒤 제출하면 제품 오너의 게이트로 갑니다.",
  "new.title": "제목", "new.titlePh": "예: Checkout latency for EU users", "new.owner": "책임 제품 오너", "new.ownerPh": "이름 <email>",
  "new.tier": "위험 등급", "tier.T0": "T0 · 문서", "tier.T1": "T1 · 일반 기능", "tier.T2": "T2 · API·스키마·의존성", "tier.T3": "T3 · 인증·결제·규제·통제",
  "new.cancel": "취소", "new.create": "초안 만들기", "new.created": "{id} 의도 초안을 만들었습니다: {path}",
  "stage.intent": "의도", "stage.spec": "명세", "stage.plan": "계획", "stage.build": "구현", "stage.done": "완료", "stage.rejected": "반려",
  "status.draft": "초안", "status.proposed": "승인 대기", "status.accepted": "승인됨", "status.rejected": "반려", "status.superseded": "대체됨",
  "status.done": "완료", "status.open": "열림", "status.diagnosed": "진단됨", "status.closed": "닫힘",
  "copy.btn": "복사", "copy.ok": "복사했습니다. 터미널에 붙여 넣어 실행하세요.", "copy.fail": "복사하지 못했습니다. 명령을 직접 선택해 복사하세요.",
  "when.none": "커밋 전", "load.fail": "불러오지 못했습니다: {msg}", "load.hint": "서버가 켜져 있는지 확인하세요: python3 -m sdlc serve",
  "ov.crumb": "Overview", "ov.title": "개요", "ov.active": "진행 중인 작업", "ov.doneN": "완료 {n}건", "ov.waiting": "사람의 게이트를 기다리는 것",
  "ov.waitingSub": "에이전트는 여기서 멈춘다", "ov.wait": "게이트 대기 시간 중앙값", "ov.hours": "시간", "ov.waitSub": "승인 {n}건 · 최장 {max}시간 (git 기록)",
  "ov.waitNone": "아직 승인 기록 없음", "ov.trace": "수락 기준 추적", "ov.traceSub": "W-NNNN:AC-n 태그된 테스트", "ov.incidents": "열린 인시던트",
  "ov.incSub": "control band 이탈", "unit.count": "건", "ov.flow": "단계별 흐름", "ov.queue": "승인 대기 — 사람이 터미널에서 결정",
  "ov.queueLede": "이 앱에는 승인 버튼이 없습니다. 에이전트도 같은 HTTP를 부를 수 있기 때문입니다. 게이트 결정은 사람이 아래 명령을 자신의 터미널에서 실행합니다.",
  "col.work": "작업", "col.artifact": "아티팩트", "col.tier": "등급", "col.approvals": "승인", "col.command": "명령", "ov.queueEmpty": "기다리는 게이트가 없습니다.",
  "ov.issuesH": "검증 실패", "ov.issues": "아티팩트 검증 문제가 {n}건 있습니다. 작업 보드에서 빨간 표시를 확인하세요.",
  "bd.crumb": "Board", "bd.title": "작업 보드", "bd.empty": "아직 작업이 없습니다. 오른쪽 위 새 작업으로 의도 초안을 만드세요.", "bd.none": "없음",
  "bd.loop": "운영에서 온 의도", "bd.approvals": "승인 {have}/{need}", "bd.issues": "검증 {n}", "bd.ac": "수락 기준 {c}/{n}",
  "br.crumb": "Branch", "br.title": "브랜치 점검", "br.none": "비교할 기준 브랜치가 없습니다.", "br.lede": "{branch} 을 {base} 와 비교합니다. CI가 PR에서 돌리는 것과 같은 검사입니다.",
  "br.tier": "위험 등급", "br.tierSub": "사람 리뷰 {n}명 · 릴리스 {rel}", "br.gates": "게이트", "br.passed": "/ {n} 통과",
  "br.files": "등급을 정한 파일", "col.path": "경로", "col.rule": "규칙", "br.gatesH": "게이트", "br.pass": "통과", "br.fail": "실패", "br.next": "병합되면 이어질 플레이",
  "in.crumb": "Maintain", "in.title": "인시던트", "col.incident": "인시던트", "col.status": "상태", "col.service": "서비스 / band", "col.detected": "감지",
  "col.followup": "후속 의도", "in.empty": "인시던트가 없습니다. control band 위반은 python3 -m sdlc bands open 이 여기에 기록합니다.",
  "wd.owner": "담당 {o}", "wd.loop": "운영에서 온 의도", "wd.traceH": "수락 기준 추적", "wd.traceNote": "태그된 테스트가 없는 기준이 남아 있으면 plan을 완료로 바꿀 수 없습니다.",
  "wd.audit": "감사 기록", "wd.ready": "이전 단계가 승인됐습니다. 초안을 만들 수 있습니다.", "wd.after": "{prev}.md가 승인된 뒤에 시작합니다.",
  "wd.makeDraft": "{kind}.md 초안 만들기", "wd.approvals": "승인 {have} / {need}", "wd.submit": "제출 (draft → proposed)", "wd.decide": "사람이 터미널에서 결정:",
  "wd.noHistory": "아직 커밋된 기록이 없습니다.", "wd.auditNote": "git 기록에서 다시 만든 상태 변화입니다. 초록은 에이전트, 주황은 사람의 커밋입니다.",
  "wd.uncommitted": "작업 트리에 커밋되지 않은 변경", "wd.docNote": "편집은 에디터나 에이전트로. 이 앱은 읽고 게이트로 보내기만 합니다.",
  "wd.staged": "{path} 초안을 만들었습니다. 내용을 채운 뒤 제출하세요.", "wd.submitted": "{id} {kind}.md를 제출했습니다. 이제 사람의 게이트입니다.", "wd.failed": "하지 못했습니다: {msg}",
});
