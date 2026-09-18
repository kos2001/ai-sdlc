"""Acceptance-criteria traceability: spec AC-n -> tests/evals tagged 'W-NNNN:AC-n'."""

from __future__ import annotations

import re
from pathlib import Path

from . import artifacts

TAG = re.compile(r"\b(W-\d{4,}):(AC-\d+)\b")
SEARCH_DIRS = ("tests", "evals")
TEXT_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".kt", ".rb", ".rs", ".cs",
                 ".json", ".yaml", ".yml", ".md", ".sh", ".feature"}


def coverage(root: Path) -> dict[str, set[str]]:
    """work id -> AC ids referenced by at least one file under tests/ or evals/."""
    covered: dict[str, set[str]] = {}
    for top in SEARCH_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for work_id, ac in TAG.findall(text):
                    covered.setdefault(work_id, set()).add(ac)
    return covered


def report(root: Path, work_id: str | None = None) -> list[dict]:
    cov = coverage(root)
    rows = []
    for art in artifacts.discover(root):
        if art.kind != "spec" or art.load_error or (work_id and art.work_id != work_id):
            continue
        acs = artifacts.acceptance_ids(art.body)
        done = cov.get(art.work_id, set())
        rows.append({
            "id": art.work_id,
            "spec": art.rel,
            "status": art.status,
            "criteria": acs,
            "covered": [a for a in acs if a in done],
            "missing": [a for a in acs if a not in done],
        })
    return rows
