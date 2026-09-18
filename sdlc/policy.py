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
