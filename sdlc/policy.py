"""Policy files under policy/ and path-glob matching shared by hooks, risk, and CI."""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path

POLICY_DIR = "policy"


@functools.lru_cache(maxsize=512)
def glob_regex(pattern: str) -> re.Pattern:
    """Gitignore-style glob: '**' spans directories, '*' and '?' stay within one segment."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches(path: str, patterns) -> str | None:
    """First pattern matching the repo-relative posix path, or None."""
    for pattern in patterns:
        if glob_regex(pattern).match(path):
            return pattern
    return None


def load(root: Path, name: str) -> dict:
    path = root / POLICY_DIR / name
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def relative(root: Path, file_path: str) -> str | None:
    """Repo-relative posix path for a (possibly absolute) path; None if outside the repo."""
    p = Path(file_path)
    if not p.is_absolute():
        p = root / p
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def human_reviews(root: Path, tier: str) -> int | None:
    """`tiers[<tier>].human_reviews` from risk-tiers.json, or None if it is not usable.

    A bool is not a count: `True` would silently read as 1.
    """
    try:
        n = load(root, "risk-tiers.json").get("tiers", {})[tier]["human_reviews"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def required_approvals(kind: str, tier: str, root: Path | None = None) -> int:
    """How many humans a gate needs (policy/risk-tiers.json, `human_reviews`).

    Floor of 1, so a tier saying 0 still needs one. Unreadable policy or no root
    keeps the built-in rule: 2 for a T3 spec/plan, else 1. See W-0002.
    """
    if kind not in ("spec", "plan"):
        return 1
    if root is not None:
        n = human_reviews(root, tier)
        if n is not None:
            return max(1, n)
    return 2 if tier == "T3" else 1


SPEC_VERSION = re.compile(r"V\d+\.(?:x|\d+)(?:\.(?:y|\d+))?|RFC\s*\d+", re.I)


def t3_evidence(art: Artifact, intent: Artifact, err) -> None:
    """A T3 spec shows what it rests on: a clause *with a version*, or why not one.

    A repo lowering `human_reviews` to 1 buys that with evidence (W-0002). A clause
    alone is not it - "38.214 5.1.3" means different tables in different releases.
    Gates and policy rest on defects, not specs; the intent's `sources` say which.
    """
    if str(art.meta.get("risk_tier")) != "T3":
        return
    sources = intent.meta.get("sources") or []
    if not sources:
        err("T3 needs sources in intent.md: the clause and version it rests on, "
            "or why the source text is not the evidence")
        return
    kinds = {str(s.get("kind")) for s in sources if isinstance(s, dict)}
    if "spec" in kinds and not SPEC_VERSION.search(json.dumps(sources, ensure_ascii=False) + art.body):
        err("T3 cites a clause without a version "
            "(e.g. '38.214 V18.10.0 5.1.3', 'RFC 3095 5.9.2')")
