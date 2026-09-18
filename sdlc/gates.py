"""CI gates on a diff: plan-first (Play 6) and no silent weakening of tests/evals (Play 8)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import artifacts, gitutil, risk

WORK_REF = re.compile(r"\b(W-\d{4,})\b", re.IGNORECASE)
TEST_DIRS = ("tests/", "evals/")

# A removed line matching these means a test or eval disappeared.
TEST_DEFINITION = re.compile(
    r"^\s*(def\s+test_\w+|async\s+def\s+test_\w+|class\s+Test\w+|(it|test|describe)\s*\(|@Test\b|func\s+Test\w+)"
)
# An added line matching these means a test is being switched off.
SKIP_MARKER = re.compile(
    r"(@unittest\.skip|unittest\.skip\(|pytest\.mark\.(skip|xfail)|\b(it|test|describe)\.(skip|only)\(|\bx(it|describe)\(|@Disabled\b|t\.Skip\()"
)
AC_TAG = re.compile(r"\bW-\d{4,}:AC-\d+\b")


@dataclass
class GateResult:
    ok: bool
    messages: list[str]


def work_ids(text: str) -> list[str]:
    return list(dict.fromkeys(m.upper() for m in WORK_REF.findall(text)))


def plan_gate(root: Path, base: str, head: str = "HEAD", refs: str = "") -> GateResult:
    """Non-T0 changes must belong to a work item whose plan.md is accepted or done.
    `refs` is extra text to search for work ids (branch name, PR title)."""
    changed = [p for s, p in gitutil.changed_files(root, base, head)]
    code_paths = [p for p in changed if not artifacts.is_artifact_path(p)]
    assessed = risk.assess(root, code_paths) if code_paths else {"tier": "T0"}
    if assessed["tier"] == "T0":
        return GateResult(True, ["plan gate: only T0 changes (docs/artifacts); no plan required"])

    ids = work_ids(refs + " " + " ".join(changed))
    if not ids:
        return GateResult(False, [
            f"plan gate: {assessed['tier']} change without a work item. Name the branch or PR after a "
            "W-NNNN work item whose plan.md is accepted (see CLAUDE.md, 'The artifact chain')."])
    messages, ok = [], False
    for work_id in ids:
        dirs = sorted((root / artifacts.WORK_DIR).glob(f"*/{work_id}-*"))
        if not dirs:
            messages.append(f"plan gate: {work_id} has no work directory")
            continue
        text = gitutil.show(root, head, (dirs[0] / "plan.md").relative_to(root).as_posix())
        if text is None:
            messages.append(f"plan gate: {work_id} has no committed plan.md")
            continue
        plan = artifacts.load_text(text, (dirs[0] / "plan.md").relative_to(root).as_posix(), root)
        if plan.status in artifacts.APPROVED:
            ok = True
            messages.append(f"plan gate: {work_id} plan.md is {plan.status}")
        else:
            messages.append(f"plan gate: {work_id} plan.md is '{plan.status or 'unreadable'}', needs accepted")
    return GateResult(ok, messages)


def _diff_lines(root: Path, base: str, head: str, path: str) -> tuple[list[str], list[str]]:
    out = gitutil.run(["diff", "--unified=0", "--no-renames", f"{base}...{head}", "--", path], root)
    removed, added = [], []
    for line in out.splitlines():
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
    return removed, added


def eval_guard(root: Path, base: str, head: str = "HEAD") -> GateResult:
    """Flag deleted tests/evals, removed test definitions or AC tags, and new skip markers."""
    findings = []
    for status, path in gitutil.changed_files(root, base, head):
        if not path.startswith(TEST_DIRS):
            continue
        if status == "D":
            findings.append(f"{path}: test/eval file deleted")
            continue
        removed, added = _diff_lines(root, base, head, path)
        added_text = "\n".join(added)
        for line in removed:
            if TEST_DEFINITION.match(line) and line.strip() not in {a.strip() for a in added}:
                findings.append(f"{path}: removed test definition `{line.strip()[:80]}`")
            for tag in AC_TAG.findall(line):
                if tag not in added_text:
                    findings.append(f"{path}: removed acceptance tag {tag}")
        for line in added:
            if SKIP_MARKER.search(line):
                findings.append(f"{path}: added skip/only marker `{line.strip()[:80]}`")
    if not findings:
        return GateResult(True, ["eval guard: no tests or evals weakened"])
    return GateResult(False, findings + [
        "eval guard: weakening tests/evals needs explicit human approval (PR label 'eval-change-approved')."])
