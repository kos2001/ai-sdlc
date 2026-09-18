"""Create work items and move artifacts through their gates."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from . import artifacts, frontmatter, trace

TEMPLATE_DIR = "templates"


class GateError(ValueError):
    pass


def today() -> str:
    return dt.date.today().isoformat()


def slugify(title: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:limit].rstrip("-") or "work"


def render_template(root: Path, name: str, values: dict[str, str]) -> str:
    text = (root / TEMPLATE_DIR / name).read_text(encoding="utf-8")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m.group(1), "")), text)


def next_work_id(root: Path) -> str:
    highest = 0
    for d in (root / artifacts.WORK_DIR).glob("*/W-*"):
        m = re.match(r"W-(\d+)-", d.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"W-{highest + 1:04d}"


def new_work(root: Path, title: str, owner: str, tier: str = "T1", origin: str = "human",
             year: int | None = None) -> Path:
    if tier not in artifacts.TIERS:
        raise GateError(f"tier must be one of {', '.join(artifacts.TIERS)}")
    work_id = next_work_id(root)
    year = year or dt.date.today().year
    work_dir = root / artifacts.WORK_DIR / str(year) / f"{work_id}-{slugify(title)}"
    work_dir.mkdir(parents=True, exist_ok=False)
    path = work_dir / "intent.md"
    path.write_text(render_template(root, "intent.md", {
        "id": work_id, "title": title, "owner": owner, "tier": tier, "origin": origin,
    }), encoding="utf-8")
    return path


def add_stage(root: Path, work_dir: Path, stage: str) -> Path:
    """Create spec.md (from intent) or plan.md (from spec) as a draft."""
    upstream = {"spec": "intent.md", "plan": "spec.md"}.get(stage)
    if upstream is None:
        raise GateError("stage must be 'spec' or 'plan'")
    target = work_dir / f"{stage}.md"
    if target.exists():
        raise GateError(f"{target.relative_to(root)} already exists")
    up = artifacts.load(work_dir / upstream, root)
    if up.load_error:
        raise GateError(f"cannot read {upstream}: {up.load_error}")
    title_match = re.search(r"^#\s+(.+?)(?:\s+—.*)?$", up.body, re.MULTILINE)
    target.write_text(render_template(root, f"{stage}.md", {
        "id": up.work_id,
        "title": title_match.group(1) if title_match else up.work_id,
        "tier": up.meta.get("risk_tier", "T1"),
    }), encoding="utf-8")
    return target


def _save(art: artifacts.Artifact) -> None:
    art.path.write_text(frontmatter.render(art.meta, art.body), encoding="utf-8")


def _require(art: artifacts.Artifact, *statuses: str) -> None:
    if art.load_error:
        raise GateError(art.load_error)
    if art.status not in statuses:
        raise GateError(f"{art.rel} is '{art.status}', expected {' or '.join(statuses)}")


def _save_if_valid(art: artifacts.Artifact, root: Path, verb: str) -> artifacts.Artifact:
    """Persist the new status only if the artifact validates in its new state."""
    index = {a.rel: a for a in artifacts.discover(root)}
    index[art.rel] = art
    issues = artifacts.validate(art, index, trace.coverage(root))
    if issues:
        raise GateError(f"cannot {verb}:\n  " + "\n  ".join(str(i) for i in issues))
    _save(art)
    return art


def submit(path: Path, root: Path) -> artifacts.Artifact:
    """draft -> proposed, only if the artifact would validate as proposed."""
    art = artifacts.load(path, root)
    _require(art, "draft")
    art.meta["status"] = "proposed"
    return _save_if_valid(art, root, "submit")


def _tier_for(art: artifacts.Artifact, root: Path) -> str:
    if art.kind == "plan":
        spec = artifacts.load(art.path.parent / "spec.md", root)
        return str(spec.meta.get("risk_tier", ""))
    return str(art.meta.get("risk_tier", ""))


def approve(path: Path, root: Path, by: str, role: str) -> artifacts.Artifact:
    """Record a human approval; flips proposed -> accepted once enough approvals exist."""
    if artifacts.AGENT_IDENTITY.search(by):
        raise GateError(f"{by!r} looks like an agent identity; only humans approve gates")
    art = artifacts.load(path, root)
    _require(art, "proposed")
    approvals = list(art.meta.get("approvals") or [])
    if any(isinstance(a, dict) and a.get("by") == by for a in approvals):
        raise GateError(f"{by} already approved {art.rel}")
    approvals.append({"by": by, "role": role, "at": today()})
    art.meta["approvals"] = approvals
    if len(approvals) >= artifacts.required_approvals(art.kind, _tier_for(art, root)):
        art.meta["status"] = "accepted"
    _save(art)
    return art


def reject(path: Path, root: Path, by: str, reason: str) -> artifacts.Artifact:
    art = artifacts.load(path, root)
    _require(art, "proposed")
    art.meta["status"] = "rejected"
    art.meta["rejected_by"] = by
    art.meta["rejection_reason"] = reason
    _save(art)
    return art


def complete(path: Path, root: Path) -> artifacts.Artifact:
    art = artifacts.load(path, root)
    _require(art, "accepted")
    art.meta["status"] = "done"
    return _save_if_valid(art, root, "complete")
