"""Deterministic risk tiering of a change (feeds Play 10 review routing and Play 11 release gates)."""

from __future__ import annotations

from pathlib import Path

from . import artifacts, gitutil, policy

TIERS = artifacts.TIERS


def rank(tier: str) -> int:
    return TIERS.index(tier)


def assess(root: Path, paths: list[str], floor: str | None = None) -> dict:
    """Tier for a set of changed paths: max over matching rules, the policy default for
    unmatched files, declared tiers of touched work items, and an optional floor."""
    config = policy.load(root, "risk-tiers.json")
    default = config["default"]
    reasons = []
    tier = "T0"
    work_dirs = set()
    for path in sorted(set(paths)):
        hits = [(rule["tier"], rule["name"]) for rule in config["rules"] if policy.matches(path, rule["paths"])]
        path_tier, rule_name = max(hits, key=lambda h: rank(h[0])) if hits else (default, "default")
        reasons.append({"path": path, "tier": path_tier, "rule": rule_name})
        if rank(path_tier) > rank(tier):
            tier = path_tier
        if artifacts.is_artifact_path(path) and path.startswith(artifacts.WORK_DIR + "/"):
            work_dirs.add(path.rsplit("/", 1)[0])
    for work_dir in sorted(work_dirs):
        for name in ("spec.md", "intent.md"):
            art = artifacts.load(root / work_dir / name, root)
            declared = str(art.meta.get("risk_tier", ""))
            if declared in TIERS:
                reasons.append({"path": f"{work_dir}/{name}", "tier": declared, "rule": "declared risk_tier"})
                if rank(declared) > rank(tier):
                    tier = declared
                break
    if floor in TIERS and rank(floor) > rank(tier):
        reasons.append({"path": "-", "tier": floor, "rule": "floor"})
        tier = floor
    return {"tier": tier, **config["tiers"][tier], "reasons": reasons}


def assess_diff(root: Path, base: str, head: str = "HEAD", floor: str | None = None) -> dict:
    paths = [p for _, p in gitutil.changed_files(root, base, head)]
    return assess(root, paths, floor)
