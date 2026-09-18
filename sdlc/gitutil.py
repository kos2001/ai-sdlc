"""Thin wrappers around the git CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def run(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def toplevel(start: Path) -> Path:
    try:
        return Path(run(["rev-parse", "--show-toplevel"], start).strip())
    except (GitError, FileNotFoundError):
        return start.resolve()


def changed_files(root: Path, base: str, head: str = "HEAD") -> list[tuple[str, str]]:
    """(status letter, path) for files changed between merge-base(base, head) and head.
    Renames are reported as a delete of the old path plus an add of the new one."""
    out = run(["diff", "--name-status", "--no-renames", f"{base}...{head}"], root)
    result = []
    for line in out.splitlines():
        if line.strip():
            status, path = line.split("\t", 1)
            result.append((status[0], path))
    return result


def working_changes(root: Path) -> list[str]:
    """Paths modified, added, or untracked in the working tree."""
    out = run(["status", "--porcelain", "--untracked-files=all"], root)
    return [line[3:].split(" -> ")[-1] for line in out.splitlines() if line.strip()]


def show(root: Path, ref: str, path: str) -> str | None:
    try:
        return run(["show", f"{ref}:{path}"], root)
    except GitError:
        return None


def merge_base(root: Path, base: str, head: str = "HEAD") -> str:
    return run(["merge-base", base, head], root).strip()


def identity(root: Path) -> str:
    name = email = ""
    try:
        name = run(["config", "user.name"], root).strip()
        email = run(["config", "user.email"], root).strip()
    except GitError:
        pass
    if not name and not email:
        raise GitError("git user.name/user.email not configured; approvals must name a person")
    return f"{name} <{email}>" if email else name
