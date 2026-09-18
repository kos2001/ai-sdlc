"""Claude Code hook handlers (Play 5: governance enforced as the agent acts).

Wired in .claude/settings.json as `python3 -m sdlc hook <event>`. Each handler reads
the hook JSON from stdin. Exit code 2 blocks (PreToolUse) or feeds stderr back to the
agent (PostToolUse, Stop); exit 0 allows. Handlers fail closed on malformed policy.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import artifacts, frontmatter, gitutil, policy, trace

BLOCK = 2
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


class Verdict(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _guard(root: Path) -> dict:
    return policy.load(root, "guard.json")


def _literal_prefix(pattern: str) -> str:
    return re.split(r"[*?]", pattern, maxsplit=1)[0]


def check_command(root: Path, command: str) -> None:
    guard = _guard(root)
    for rule in guard["blocked_commands"]:
        if re.search(rule["pattern"], command):
            raise Verdict(f"blocked command ({rule['reason']}): {command.strip()[:200]}")
    if re.search(guard["shell_write_pattern"], command):
        for pattern in guard["protected_paths"]:
            prefix = _literal_prefix(pattern)
            if prefix and prefix in command:
                raise Verdict(f"shell write touching protected path '{pattern}'; protected paths are changed by humans")


def _prospective_text(path: Path, tool: str, tool_input: dict) -> str | None:
    """File content after the tool would run, or None if it cannot be computed."""
    if tool == "Write":
        return tool_input.get("content", "")
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    for edit in edits or []:
        old, new = edit.get("old_string", ""), edit.get("new_string", "")
        if old not in current:
            return None  # the tool itself will fail; nothing to judge
        current = current.replace(old, new) if edit.get("replace_all") else current.replace(old, new, 1)
    return current


def _meta(text: str | None) -> dict | None:
    if text is None:
        return None
    try:
        return frontmatter.load(text)[0]
    except frontmatter.FrontmatterError:
        return None


def check_artifact_write(root: Path, rel: str, tool: str, tool_input: dict) -> None:
    """Agents may create and edit artifacts but never record approvals or pass a gate."""
    path = root / rel
    before = _meta(path.read_text(encoding="utf-8")) if path.is_file() else {}
    after = _meta(_prospective_text(path, tool, tool_input))
    if before is None or after is None:
        return  # unparseable content is reported by the PostToolUse validation instead
    gate_statuses = set(_guard(root)["gate_statuses"])
    if (after.get("approvals") or []) != (before.get("approvals") or []):
        raise Verdict(f"{rel}: approvals are recorded by humans with `sdlc approve`, not by the agent")
    new_status = str(after.get("status", ""))
    if new_status != str(before.get("status", "")) and new_status in gate_statuses:
        raise Verdict(f"{rel}: setting status '{new_status}' is a human gate decision")
    for key in ("rejected_by", "rejection_reason"):
        if after.get(key) != before.get(key):
            raise Verdict(f"{rel}: '{key}' is written by a human rejecting the artifact")
    tiers = artifacts.TIERS
    old_tier, new_tier = str(before.get("risk_tier", "")), str(after.get("risk_tier", ""))
    if old_tier in tiers and new_tier in tiers and tiers.index(new_tier) < tiers.index(old_tier):
        raise Verdict(f"{rel}: risk_tier can only be raised ({old_tier} -> {new_tier})")


def pre_tool_use(root: Path, event: dict) -> None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool == "Bash":
        check_command(root, tool_input.get("command", ""))
        return
    if tool not in WRITE_TOOLS:
        return
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    rel = policy.relative(root, file_path)
    if rel is None:
        return
    hit = policy.matches(rel, _guard(root)["protected_paths"])
    if hit:
        raise Verdict(f"{rel} is protected by '{hit}'; propose the change to a human instead of editing it")
    if artifacts.is_artifact_path(rel):
        check_artifact_write(root, rel, tool, tool_input)


def _validate_paths(root: Path, rels: set[str]) -> list[str]:
    arts = artifacts.discover(root)
    index = {a.rel: a for a in arts}
    cov = trace.coverage(root)
    return [str(i) for a in arts if a.rel in rels for i in artifacts.validate(a, index, cov)]


def post_tool_use(root: Path, event: dict) -> None:
    if event.get("tool_name") not in WRITE_TOOLS:
        return
    tool_input = event.get("tool_input") or {}
    rel = policy.relative(root, tool_input.get("file_path") or "")
    if rel is None or not artifacts.is_artifact_path(rel):
        return
    problems = _validate_paths(root, {rel})
    if problems:
        raise Verdict("artifact validation failed — fix before continuing:\n" + "\n".join(problems))


def stop(root: Path, event: dict) -> None:
    if event.get("stop_hook_active"):
        return  # already continued once because of this hook; don't loop
    try:
        changed = {p for p in gitutil.working_changes(root) if artifacts.is_artifact_path(p)}
    except gitutil.GitError:
        return
    problems = _validate_paths(root, changed)
    if problems:
        raise Verdict("changed artifacts are invalid; fix them or explain why before stopping:\n" + "\n".join(problems))


_WORK_REF = re.compile(r"\b(W-\d{4,})\b", re.IGNORECASE)


def user_prompt_submit(root: Path, event: dict) -> str:
    """Inject the active work item (from the branch name) as context."""
    try:
        branch = gitutil.run(["rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    except gitutil.GitError:
        return ""
    m = _WORK_REF.search(branch)
    if not m:
        return ""
    work_id = m.group(1).upper()
    dirs = sorted((root / artifacts.WORK_DIR).glob(f"*/{work_id}-*"))
    if not dirs:
        return f"Branch '{branch}' names {work_id}, but no work item exists. Start with the capture-intent skill."
    lines = [f"Active work item {work_id} ({dirs[0].relative_to(root).as_posix()}):"]
    for name in artifacts.STAGE_FILES:
        art = artifacts.load(dirs[0] / name, root)
        if not art.load_error:
            tier = art.meta.get("risk_tier")
            lines.append(f"- {name}: {art.status}" + (f", risk {tier}" if tier else ""))
        elif (dirs[0] / name).exists():
            lines.append(f"- {name}: unreadable ({art.load_error})")
    plan = artifacts.load(dirs[0] / "plan.md", root)
    if not plan.load_error and plan.status != "accepted":
        lines.append("Do not write implementation code until plan.md is accepted.")
    return "\n".join(lines)


HANDLERS = {
    "pre-tool-use": pre_tool_use,
    "post-tool-use": post_tool_use,
    "stop": stop,
}


def run(event_name: str, root: Path, stdin=sys.stdin) -> int:
    raw = stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print("sdlc hook: malformed hook input", file=sys.stderr)
        return BLOCK
    if event.get("cwd"):
        root = gitutil.toplevel(Path(event["cwd"]))
    try:
        if event_name == "user-prompt-submit":
            context = user_prompt_submit(root, event)
            if context:
                print(context)
            return 0
        HANDLERS[event_name](root, event)
    except Verdict as v:
        print(v.message, file=sys.stderr)
        return BLOCK
    except (OSError, ValueError, KeyError) as exc:  # broken policy must not silently allow
        print(f"sdlc hook: policy error, failing closed: {exc}", file=sys.stderr)
        return BLOCK
    return 0
