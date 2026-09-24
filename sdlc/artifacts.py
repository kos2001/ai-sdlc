"""Artifact model: schemas, status machine, and validation rules.

An artifact is a Markdown file with frontmatter that ends one SDLC stage and
starts the next:

    work/<YYYY>/<W-NNNN>-<slug>/intent.md   Plan
    work/<YYYY>/<W-NNNN>-<slug>/spec.md     Design
    work/<YYYY>/<W-NNNN>-<slug>/plan.md     Build (plan mode)
    incidents/<YYYY>/<INC-YYYY-NNN>.md      Maintain
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import frontmatter, policy

WORK_DIR = "work"
INCIDENT_DIR = "incidents"
STAGE_FILES = ("intent.md", "spec.md", "plan.md")

STATUSES = ("draft", "proposed", "accepted", "rejected", "superseded", "done")
INCIDENT_STATUSES = ("open", "diagnosed", "closed")
APPROVED = frozenset({"accepted", "done"})
TIERS = ("T0", "T1", "T2", "T3")
ORIGINS = ("human", "maintain-loop")

# Legal status transitions. Staying in the same status is always legal.
TRANSITIONS = {
    "draft": {"proposed"},
    "proposed": {"accepted", "rejected", "draft"},
    "accepted": {"superseded", "done"},
    "rejected": set(),
    "superseded": set(),
    "done": set(),
    "open": {"diagnosed", "closed"},
    "diagnosed": {"closed"},
    "closed": set(),
}

REQUIRED = {
    "intent": ("id", "type", "status", "owner", "sources", "risk_tier", "origin", "approvals"),
    "spec": ("id", "type", "status", "intent", "skills_applied", "risk_tier", "approvals"),
    "plan": ("id", "type", "status", "spec", "approvals"),
    "incident": ("id", "type", "status", "band", "service", "detected_at", "followup_intent"),
}

# Identities that must never appear as approvers: agents produce, humans approve.
AGENT_IDENTITY = re.compile(r"claude|anthropic|\[bot\]|github-actions", re.IGNORECASE)
AC_ID = re.compile(r"\bAC-(\d+)\b")
WORK_ID = re.compile(r"^W-\d{4,}$")
INCIDENT_ID = re.compile(r"^INC-\d{4}-\d{3,}$")
CHECKBOX = re.compile(r"^\s*- \[( |x|X)\] ", re.MULTILINE)


@dataclass
class Issue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class Artifact:
    path: Path
    root: Path
    meta: dict
    body: str
    load_error: str | None = None
    issues: list[Issue] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return self.path.relative_to(self.root).as_posix()

    @property
    def kind(self) -> str:
        return expected_type(self.rel) or ""

    @property
    def status(self) -> str:
        return str(self.meta.get("status", ""))

    @property
    def work_id(self) -> str:
        return str(self.meta.get("id", ""))


def expected_type(rel: str) -> str | None:
    parts = rel.split("/")
    if parts[0] == WORK_DIR and len(parts) == 4 and parts[-1] in STAGE_FILES:
        return parts[-1][: -len(".md")]
    if parts[0] == INCIDENT_DIR and len(parts) == 3 and parts[-1].startswith("INC-") and parts[-1].endswith(".md"):
        return "incident"
    return None


def is_artifact_path(rel: str) -> bool:
    return expected_type(rel) is not None


def load(path: Path, root: Path) -> Artifact:
    try:
        meta, body = frontmatter.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, frontmatter.FrontmatterError) as exc:
        return Artifact(path, root, {}, "", load_error=str(exc))
    return Artifact(path, root, meta, body)


def load_text(text: str, rel: str, root: Path) -> Artifact:
    try:
        meta, body = frontmatter.load(text)
    except frontmatter.FrontmatterError as exc:
        return Artifact(root / rel, root, {}, "", load_error=str(exc))
    return Artifact(root / rel, root, meta, body)


def discover(root: Path) -> list[Artifact]:
    found = []
    for pattern in (f"{WORK_DIR}/*/*/*.md", f"{INCIDENT_DIR}/*/INC-*.md"):
        for path in sorted(root.glob(pattern)):
            if is_artifact_path(path.relative_to(root).as_posix()):
                found.append(load(path, root))
    return found


def section(body: str, heading: str) -> str:
    """Text under '## heading' up to the next '## ' heading."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def _uncommented(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _meaningful(text: str) -> bool:
    """True when a section has content beyond HTML comments and whitespace."""
    return bool(_uncommented(text).strip())


def acceptance_ids(spec_body: str) -> list[str]:
    ids = dict.fromkeys(f"AC-{n}" for n in AC_ID.findall(_uncommented(section(spec_body, "Acceptance criteria"))))
    return list(ids)


def plan_steps(plan_body: str) -> tuple[int, int]:
    """(total, checked) checkbox counts in the plan's Steps section."""
    marks = CHECKBOX.findall(_uncommented(section(plan_body, "Steps")))
    return len(marks), sum(1 for m in marks if m in "xX")


def _tier_rank(tier: str) -> int:
    return TIERS.index(tier) if tier in TIERS else -1


def _sibling(art: Artifact, name: str, index: dict[str, Artifact]) -> Artifact | None:
    return index.get(art.path.parent.joinpath(name).relative_to(art.root).as_posix())


def validate(art: Artifact, index: dict[str, Artifact], coverage: dict[str, set[str]] | None = None) -> list[Issue]:
    """Validate one artifact. `index` maps rel path -> Artifact for chain checks;
    `coverage` maps work id -> set of covered AC ids (see trace.coverage)."""
    issues: list[Issue] = []

    def err(msg: str) -> None:
        issues.append(Issue(art.rel, msg))

    if art.load_error:
        err(art.load_error)
        return issues

    kind = art.kind
    meta = art.meta
    for key in REQUIRED[kind]:
        if key not in meta:
            err(f"missing required field '{key}'")
    if meta.get("type") != kind:
        err(f"type must be '{kind}' for this path (got {meta.get('type')!r})")

    allowed = INCIDENT_STATUSES if kind == "incident" else STATUSES
    if art.status not in allowed:
        err(f"status {art.status!r} not in {', '.join(allowed)}")

    if kind == "incident":
        _validate_incident(art, err)
        return issues

    if not WORK_ID.match(art.work_id):
        err(f"id {art.work_id!r} must look like W-0001")
    elif not art.path.parent.name.startswith(art.work_id + "-"):
        err(f"id {art.work_id} does not match directory '{art.path.parent.name}'")

    tier = str(meta.get("risk_tier", ""))
    if kind in ("intent", "spec") and tier not in TIERS:
        err(f"risk_tier {tier!r} not in {', '.join(TIERS)}")

    approvals = meta.get("approvals", [])
    if not isinstance(approvals, list):
        err("approvals must be a list")
        approvals = []
    for a in approvals:
        if not isinstance(a, dict) or not all(a.get(k) for k in ("by", "role", "at")):
            err(f"approval entry needs by/role/at: {a!r}")
        elif AGENT_IDENTITY.search(str(a["by"])):
            err(f"approval by agent identity {a['by']!r} — only humans approve gates")

    if kind == "plan":
        spec = _sibling(art, "spec.md", index)
        tier = str(spec.meta.get("risk_tier", "")) if spec else ""
    if art.status in APPROVED:
        need = policy.required_approvals(kind, tier, art.root)
        if len(approvals) < need:
            err(f"status '{art.status}' needs {need} human approval(s), has {len(approvals)}")

    if kind == "intent":
        _validate_intent(art, err)
    elif kind == "spec":
        _validate_spec(art, index, err)
    elif kind == "plan":
        _validate_plan(art, index, coverage, err)
    return issues


def _validate_intent(art: Artifact, err) -> None:
    meta = art.meta
    if meta.get("origin") not in ORIGINS:
        err(f"origin must be one of {', '.join(ORIGINS)}")
    if not str(meta.get("owner", "")).strip():
        err("owner must name the accountable product owner")
    if art.status != "draft":
        sources = meta.get("sources") or []
        if not sources:
            err("sources must cite at least one ticket/metric/incident/interview once proposed")
        for s in sources:
            if not isinstance(s, dict) or not s.get("kind") or not s.get("ref"):
                err(f"source entry needs kind and ref: {s!r}")
        for heading in ("Problem", "Desired outcome"):
            if not _meaningful(section(art.body, heading)):
                err(f"section '## {heading}' is empty")


def _validate_spec(art: Artifact, index, err) -> None:
    intent = _sibling(art, "intent.md", index)
    if intent is None:
        err("spec has no sibling intent.md")
        return
    if art.status != "draft":
        if intent.status not in APPROVED:
            err(f"spec is '{art.status}' but intent.md is '{intent.status}' (intent must be accepted first)")
        if not acceptance_ids(art.body):
            err("section '## Acceptance criteria' must list AC-1, AC-2, ...")
        policy.t3_evidence(art, intent, err)
    if _tier_rank(str(art.meta.get("risk_tier"))) < _tier_rank(str(intent.meta.get("risk_tier"))):
        err(f"risk_tier {art.meta.get('risk_tier')} is lower than intent's {intent.meta.get('risk_tier')} — tiers can only go up")
    if art.meta.get("id") != intent.meta.get("id"):
        err("id differs from sibling intent.md")


def _validate_plan(art: Artifact, index, coverage, err) -> None:
    spec = _sibling(art, "spec.md", index)
    if spec is None:
        err("plan has no sibling spec.md")
        return
    if art.meta.get("id") != spec.meta.get("id"):
        err("id differs from sibling spec.md")
    if art.status == "draft":
        return
    if spec.status not in APPROVED:
        err(f"plan is '{art.status}' but spec.md is '{spec.status}' (spec must be accepted first)")
    total, checked = plan_steps(art.body)
    if total == 0:
        err("section '## Steps' must contain '- [ ]' checklist items")
    if art.status == "done":
        if checked < total:
            err(f"plan is done but {total - checked} of {total} steps are unchecked")
        if coverage is not None:
            missing = [ac for ac in acceptance_ids(spec.body) if ac not in coverage.get(art.work_id, set())]
            if missing:
                err(f"plan is done but no test/eval is tagged for {', '.join(f'{art.work_id}:{m}' for m in missing)}")


def _validate_incident(art: Artifact, err) -> None:
    if not INCIDENT_ID.match(art.work_id):
        err(f"id {art.work_id!r} must look like INC-2026-001")
    elif art.path.stem != art.work_id:
        err(f"file name must be {art.work_id}.md")
    follow = str(art.meta.get("followup_intent", "")).strip()
    if follow and not (art.root / follow).is_file():
        err(f"followup_intent {follow!r} does not exist")
    if art.status == "closed" and not follow and not str(art.meta.get("resolution", "")).strip():
        err("closed incident needs followup_intent or resolution")


def check_transition(old: Artifact | None, new: Artifact) -> list[Issue]:
    """Rules for how an artifact may change between two revisions."""
    if old is None or old.load_error or new.load_error:
        return []
    issues = []
    before, after = old.status, new.status
    if before != after and after not in TRANSITIONS.get(before, set()):
        issues.append(Issue(new.rel, f"illegal status transition {before} -> {after}"))
    old_apps = old.meta.get("approvals") or []
    new_apps = new.meta.get("approvals") or []
    if new_apps[: len(old_apps)] != old_apps:
        issues.append(Issue(new.rel, "approvals are append-only; existing entries were changed or removed"))
    if new.kind in ("intent", "spec") and _tier_rank(str(new.meta.get("risk_tier"))) < _tier_rank(str(old.meta.get("risk_tier"))):
        issues.append(Issue(new.rel, f"risk_tier lowered {old.meta.get('risk_tier')} -> {new.meta.get('risk_tier')}"))
    return issues
