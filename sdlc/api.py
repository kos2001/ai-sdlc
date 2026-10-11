"""Read model for the web app: work items, their audit trail from git, gates, and flow metrics.

Everything here is derived from the repository (artifacts + git history); nothing is stored
elsewhere. Gate decisions are deliberately absent: approvals stay a human CLI action.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import statistics
from pathlib import Path

from . import artifacts, drafts, events, gates, gitutil, policy, risk, trace

STAGES = ("intent", "spec", "plan")
SEP = "\x1f"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)


def history(root: Path, rel: str) -> list[dict]:
    """Status transitions of one artifact, oldest first, reconstructed from git.

    Each entry: {status, at, author, commit, subject}. Uncommitted edits appear last
    with commit None so the UI can flag them.
    """
    try:
        log = gitutil.run(["log", f"--format=%H{SEP}%an <%ae>{SEP}%aI{SEP}%s", "--", rel], root)
    except gitutil.GitError:
        log = ""
    entries, last = [], None
    for line in reversed(log.splitlines()):
        sha, author, at, subject = line.split(SEP, 3)
        text = gitutil.show(root, sha, rel)
        status = artifacts.load_text(text, rel, root).status if text else "deleted"
        if status != last:
            entries.append({"status": status, "at": at, "author": author, "commit": sha[:7], "subject": subject})
            last = status
    current = artifacts.load(root / rel, root)
    if (root / rel).exists() and current.status != last:
        entries.append({"status": current.status or "unreadable", "at": None, "author": None,
                        "commit": None, "subject": "uncommitted change"})
    return entries


def _stage_of(chain: dict) -> str:
    statuses = {k: v["status"] for k, v in chain.items() if v}
    if "rejected" in statuses.values():
        return "rejected"
    if statuses.get("plan") == "done":
        return "done"
    if statuses.get("plan") == "accepted":
        return "build"
    for kind in ("plan", "spec"):
        if kind in statuses:
            return kind
    return "intent"


def _artifact_summary(art: artifacts.Artifact, index: dict, coverage: dict) -> dict:
    tier = str(art.meta.get("risk_tier", ""))
    if art.kind == "plan":
        spec = index.get(art.path.parent.joinpath("spec.md").relative_to(art.root).as_posix())
        tier = str(spec.meta.get("risk_tier", "")) if spec else ""
    approvals = [a for a in art.meta.get("approvals") or [] if isinstance(a, dict)]
    return {
        "path": art.rel,
        "status": art.status or "unreadable",
        "tier": tier or None,
        "approvals": approvals,
        "needed": policy.required_approvals(art.kind, tier, art.root),
        "issues": [i.message for i in artifacts.validate(art, index, coverage)],
    }


def _title(art: artifacts.Artifact) -> str:
    for line in art.body.splitlines():
        if line.startswith("# "):
            return line[2:].split(" — ")[0].strip()
    return art.work_id


def work_items(root: Path) -> list[dict]:
    arts = artifacts.discover(root)
    index = {a.rel: a for a in arts}
    coverage = trace.coverage(root)
    items: dict[str, dict] = {}
    for art in arts:
        if art.kind not in STAGES:
            continue
        folder = art.path.parent.relative_to(root).as_posix()
        item = items.setdefault(folder, {"dir": folder, "chain": {k: None for k in STAGES}})
        item["chain"][art.kind] = _artifact_summary(art, index, coverage)
        if art.kind == "intent" or "id" not in item:
            item.update(id=art.work_id or folder.rsplit("/", 1)[-1], title=_title(art))
        if art.kind == "intent":
            item.update(owner=str(art.meta.get("owner", "")), origin=str(art.meta.get("origin", "human")),
                        tier=str(art.meta.get("risk_tier", "")))
        if art.kind == "spec":
            acs = artifacts.acceptance_ids(art.body)
            done = coverage.get(art.work_id, set())
            item["trace"] = {"criteria": acs, "covered": [a for a in acs if a in done]}
    result = []
    for item in items.values():
        item["stage"] = _stage_of(item["chain"])
        spec_tier = (item["chain"]["spec"] or {}).get("tier")
        item["tier"] = spec_tier or item.get("tier") or None
        item.setdefault("trace", {"criteria": [], "covered": []})
        item["issues"] = sum(len(c["issues"]) for c in item["chain"].values() if c)
        item["awaiting"] = [k for k, c in item["chain"].items() if c and c["status"] == "proposed"]
        result.append(item)
    return sorted(result, key=lambda i: i["id"], reverse=True)


def work_item(root: Path, work_id: str) -> dict | None:
    item = next((w for w in work_items(root) if w["id"] == work_id), None)
    if item is None:
        return None
    for kind, summary in item["chain"].items():
        if not summary:
            continue
        raw = (root / summary["path"]).read_bytes()
        art = artifacts.load_text(raw.decode("utf-8"), summary["path"], root)
        summary["revision"] = drafts.revision(raw)
        summary["body"] = art.body
        summary["meta"] = {k: v for k, v in art.meta.items() if k != "approvals"}
        summary["history"] = history(root, summary["path"])
    return item


def incidents(root: Path) -> list[dict]:
    out = []
    for art in artifacts.discover(root):
        if art.kind != "incident" or art.load_error:
            continue
        out.append({"id": art.work_id, "path": art.rel, "status": art.status, "service": art.meta.get("service"),
                    "band": art.meta.get("band"), "detected_at": art.meta.get("detected_at"),
                    "followup_intent": art.meta.get("followup_intent") or None})
    return sorted(out, key=lambda i: i["id"], reverse=True)


def gate_waits(root: Path, items: list[dict]) -> list[float]:
    """Hours between an artifact becoming proposed and becoming accepted, across all history."""
    waits = []
    for item in items:
        for summary in item["chain"].values():
            if not summary:
                continue
            proposed = None
            for h in history(root, summary["path"]):
                if h["at"] is None:
                    continue
                if h["status"] == "proposed":
                    proposed = _parse_time(h["at"])
                elif h["status"] == "accepted" and proposed:
                    waits.append((_parse_time(h["at"]) - proposed).total_seconds() / 3600)
                    proposed = None
    return waits


def default_base(root: Path) -> str | None:
    for ref in ("origin/main", "main", "origin/master", "master"):
        try:
            gitutil.run(["rev-parse", "--verify", "--quiet", ref], root)
            return ref
        except gitutil.GitError:
            continue
    return None


def branch_check(root: Path, base: str | None = None) -> dict:
    branch = gitutil.run(["rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    base = base or default_base(root)
    if not base:
        return {"branch": branch, "base": None, "note": "no base branch found"}
    if gitutil.run(["rev-parse", base], root).strip() == gitutil.run(["rev-parse", "HEAD"], root).strip():
        return {"branch": branch, "base": base, "note": f"{branch} is at {base}; nothing to compare"}
    from .cli import transition_issues  # local import: cli imports this module's siblings
    plan = gates.plan_gate(root, base, "HEAD", branch)
    evals = gates.eval_guard(root, base, "HEAD")
    return {
        "branch": branch, "base": base,
        "risk": risk.assess_diff(root, base),
        "gates": [
            {"name": "plan-gate", "ok": plan.ok, "messages": plan.messages},
            {"name": "eval-guard", "ok": evals.ok, "messages": evals.messages},
            {"name": "transitions", "ok": not (t := transition_issues(root, base)), "messages": [str(i) for i in t] or ["transitions: ok"]},
        ],
        "events": events.derive(root, base),
    }


def overview(root: Path) -> dict:
    items = work_items(root)
    by_stage: dict[str, int] = {}
    for item in items:
        by_stage[item["stage"]] = by_stage.get(item["stage"], 0) + 1
    waiting = [{"id": i["id"], "title": i["title"], "kind": k, "path": i["chain"][k]["path"],
                "have": len(i["chain"][k]["approvals"]), "needed": i["chain"][k]["needed"], "tier": i["tier"]}
               for i in items for k in i["awaiting"]]
    waits = gate_waits(root, items)
    try:
        branch = gitutil.run(["rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    except gitutil.GitError:
        branch = None
    return {
        "repo": root.name, "branch": branch, "generated_at": _now().isoformat(timespec="seconds"),
        "workspace_id": hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest(),
        "work_items": len(items), "by_stage": by_stage, "waiting": waiting,
        "issues": sum(i["issues"] for i in items),
        "incidents_open": sum(1 for i in incidents(root) if i["status"] != "closed"),
        "gate_wait_hours": {"count": len(waits), "median": round(statistics.median(waits), 1) if waits else None,
                            "max": round(max(waits), 1) if waits else None},
        "trace": {"criteria": sum(len(i["trace"]["criteria"]) for i in items),
                  "covered": sum(len(i["trace"]["covered"]) for i in items)},
    }
