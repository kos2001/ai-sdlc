"""`python3 -m sdlc <command>` — the deterministic half of the AI-native SDLC.

Agents generate; these commands check, gate, and route. Every command exits
non-zero on a violation so it can back a hook or a CI job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import artifacts, cli_ops, gitutil, hooks, risk, trace, workitems


def _root(args) -> Path:
    return Path(args.root).resolve() if args.root else gitutil.toplevel(Path.cwd())


def _print_issues(issues) -> int:
    for issue in issues:
        print(f"ERROR {issue}", file=sys.stderr)
    return 1 if issues else 0


def validate_all(root: Path, only: set[str] | None = None) -> list[artifacts.Issue]:
    arts = artifacts.discover(root)
    index = {a.rel: a for a in arts}
    cov = trace.coverage(root)
    issues = []
    for art in arts:
        if only is None or art.rel in only:
            issues.extend(artifacts.validate(art, index, cov))
    return issues


def cmd_validate(args) -> int:
    root = _root(args)
    only = None
    if args.changed:
        only = {p for p in gitutil.working_changes(root) if artifacts.is_artifact_path(p)}
    issues = validate_all(root, only)
    code = _print_issues(issues)
    if not code:
        print("artifacts: ok")
    return code


def transition_issues(root: Path, base: str, head: str = "HEAD") -> list[artifacts.Issue]:
    ref = gitutil.merge_base(root, base, head)
    issues = []
    for status, path in gitutil.changed_files(root, base, head):
        if status == "D" or not artifacts.is_artifact_path(path):
            if status == "D" and artifacts.is_artifact_path(path):
                issues.append(artifacts.Issue(path, "artifacts are never deleted; mark them superseded/rejected instead"))
            continue
        old_text = gitutil.show(root, ref, path)
        new_text = gitutil.show(root, head, path)
        if new_text is None:
            continue
        old = artifacts.load_text(old_text, path, root) if old_text is not None else None
        issues.extend(artifacts.check_transition(old, artifacts.load_text(new_text, path, root)))
    return issues


def cmd_transitions(args) -> int:
    root = _root(args)
    code = _print_issues(transition_issues(root, args.base, args.head))
    if not code:
        print("transitions: ok")
    return code


def cmd_new(args) -> int:
    root = _root(args)
    owner = args.owner or gitutil.identity(root)
    path = workitems.new_work(root, args.title, owner, args.tier)
    print(path.relative_to(root))
    return 0


def _work_dir(root: Path, ref: str) -> Path:
    candidate = (root / ref).resolve()
    if candidate.is_dir():
        return candidate
    matches = sorted((root / artifacts.WORK_DIR).glob(f"*/{ref}-*"))
    if len(matches) != 1:
        raise workitems.GateError(f"cannot resolve work item {ref!r}")
    return matches[0]


def _artifact_path(root: Path, ref: str, stage: str | None) -> Path:
    path = (root / ref).resolve()
    if path.is_file():
        return path
    if not stage:
        raise workitems.GateError("pass an artifact path, or a work id with --stage")
    return _work_dir(root, ref) / f"{stage}.md"


def cmd_stage(args) -> int:
    root = _root(args)
    path = workitems.add_stage(root, _work_dir(root, args.work), args.stage)
    print(path.relative_to(root))
    return 0


def cmd_submit(args) -> int:
    root = _root(args)
    art = workitems.submit(_artifact_path(root, args.artifact, args.stage), root)
    print(f"{art.rel}: proposed")
    return 0


def cmd_approve(args) -> int:
    root = _root(args)
    by = args.by or gitutil.identity(root)
    art = workitems.approve(_artifact_path(root, args.artifact, args.stage), root, by, args.role)
    print(f"{art.rel}: {art.status} ({len(art.meta['approvals'])} approval(s))")
    return 0


def cmd_reject(args) -> int:
    root = _root(args)
    by = args.by or gitutil.identity(root)
    art = workitems.reject(_artifact_path(root, args.artifact, args.stage), root, by, args.reason)
    print(f"{art.rel}: rejected")
    return 0


def cmd_done(args) -> int:
    root = _root(args)
    art = workitems.complete(_artifact_path(root, args.artifact, args.stage), root)
    print(f"{art.rel}: done")
    return 0


def cmd_trace(args) -> int:
    rows = trace.report(_root(args), args.work)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['id']} [{r['status']}] covered {len(r['covered'])}/{len(r['criteria'])}"
                  + (f" missing: {', '.join(r['missing'])}" if r["missing"] else ""))
    return 1 if args.strict and any(r["missing"] for r in rows) else 0


def cmd_risk(args) -> int:
    root = _root(args)
    if args.paths:
        result = risk.assess(root, args.paths, args.floor)
    else:
        result = risk.assess_diff(root, args.base, args.head, args.floor)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"risk tier: {result['tier']} — human reviews: {result['human_reviews']}, release: {result['release']}")
        for r in result["reasons"]:
            if r["tier"] == result["tier"]:
                print(f"  {r['tier']} {r['path']} ({r['rule']})")
    return 0


def cmd_hook(args) -> int:
    return hooks.run(args.event, _root(args))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdlc", description=__doc__.splitlines()[0])
    p.add_argument("--root", help="repository root (default: git toplevel)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("validate", help="validate every artifact (schema, chain, approvals)")
    s.add_argument("--changed", action="store_true", help="only artifacts changed in the working tree")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("transitions", help="check status transitions between two revisions")
    s.add_argument("--base", required=True)
    s.add_argument("--head", default="HEAD")
    s.set_defaults(func=cmd_transitions)

    s = sub.add_parser("new", help="start a work item with a draft intent.md")
    s.add_argument("title")
    s.add_argument("--owner", help="accountable product owner (default: git identity)")
    s.add_argument("--tier", default="T1", choices=artifacts.TIERS)
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("stage", help="create the next draft artifact (spec or plan)")
    s.add_argument("work", help="work id (W-0001) or work directory")
    s.add_argument("stage", choices=("spec", "plan"))
    s.set_defaults(func=cmd_stage)

    for name, func, helptext in (("submit", cmd_submit, "draft -> proposed"),
                                 ("approve", cmd_approve, "record a human approval"),
                                 ("reject", cmd_reject, "proposed -> rejected"),
                                 ("done", cmd_done, "accepted -> done")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("artifact", help="artifact path, or work id with --stage")
        s.add_argument("--stage", choices=("intent", "spec", "plan"))
        if name in ("approve", "reject"):
            s.add_argument("--by", help="approver (default: git identity)")
        if name == "approve":
            s.add_argument("--role", required=True, help="e.g. product-owner, architect, tech-lead")
        if name == "reject":
            s.add_argument("--reason", required=True)
        s.set_defaults(func=func)

    s = sub.add_parser("trace", help="acceptance criteria -> tagged tests/evals coverage")
    s.add_argument("work", nargs="?")
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true", help="exit 1 when any AC is uncovered")
    s.set_defaults(func=cmd_trace)

    s = sub.add_parser("risk", help="risk tier of a diff (or explicit paths) from policy/risk-tiers.json")
    s.add_argument("--base", default="origin/main")
    s.add_argument("--head", default="HEAD")
    s.add_argument("--floor", choices=artifacts.TIERS, help="minimum tier (e.g. from a PR label)")
    s.add_argument("--json", action="store_true")
    s.add_argument("paths", nargs="*")
    s.set_defaults(func=cmd_risk)

    cli_ops.register(sub)

    s = sub.add_parser("hook", help="Claude Code hook handler (reads hook JSON on stdin)")
    s.add_argument("event", choices=("pre-tool-use", "post-tool-use", "stop", "user-prompt-submit"))
    s.set_defaults(func=cmd_hook)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (workitems.GateError, gitutil.GitError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
