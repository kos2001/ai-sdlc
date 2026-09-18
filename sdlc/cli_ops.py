"""Gate, feedback, orchestration, and loop commands for `python3 -m sdlc` (split from cli.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import bands, events, feedback, gates, release


def _root(args) -> Path:
    from .cli import _root as root_of
    return root_of(args)


def _gate(result: gates.GateResult) -> int:
    stream = sys.stdout if result.ok else sys.stderr
    for m in result.messages:
        print(m, file=stream)
    return 0 if result.ok else 1


def cmd_plan_gate(args) -> int:
    return _gate(gates.plan_gate(_root(args), args.base, args.head, " ".join(args.refs)))


def cmd_eval_guard(args) -> int:
    return _gate(gates.eval_guard(_root(args), args.base, args.head))


def cmd_feedback(args) -> int:
    text = feedback.report(feedback.collect(feedback.load_comments([Path(f) for f in args.comments])))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text, end="")
    return 0


def cmd_events(args) -> int:
    found = events.derive(_root(args), args.base, args.head)
    if args.json:
        print(json.dumps(found))
    else:
        for e in found:
            print(f"{e['event']:<16} {e['work_id']:<14} -> {e['play']} (skill: {e['skill']})  {e['path']}")
    return 0


def cmd_bands(args) -> int:
    root = _root(args)
    metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    breaches, missing = bands.check(bands.load_bands(root), metrics)
    for m in missing:
        print(f"WARN {m}", file=sys.stderr)
    if args.action == "check":
        for b in breaches:
            print(f"BREACH {b.service}/{b.band}: {b.describe}")
        return 1 if breaches else 0
    results = [bands.open_loop(root, b) for b in breaches]
    print(json.dumps(results, indent=2))
    return 0


def cmd_release_record(args) -> int:
    text = release.record(_root(args), args.base, args.head, args.pr, args.approver)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text, end="")
    return 0


def register(sub) -> None:
    s = sub.add_parser("plan-gate", help="non-T0 changes need a work item with an accepted plan.md")
    s.add_argument("--base", default="origin/main")
    s.add_argument("--head", default="HEAD")
    s.add_argument("--refs", nargs="*", default=[], help="branch name / PR title to search for W-ids")
    s.set_defaults(func=cmd_plan_gate)

    s = sub.add_parser("eval-guard", help="fail when tests/evals are deleted, skipped, or untagged")
    s.add_argument("--base", default="origin/main")
    s.add_argument("--head", default="HEAD")
    s.set_defaults(func=cmd_eval_guard)

    s = sub.add_parser("feedback", help="tagged PR review comments -> rule/eval candidates")
    s.add_argument("comments", nargs="+", help="JSON from `gh api repos/O/R/pulls/comments --paginate`")
    s.add_argument("--out", help="write the markdown report here")
    s.set_defaults(func=cmd_feedback)

    s = sub.add_parser("events", help="artifact status changes -> next play to run")
    s.add_argument("--base", required=True)
    s.add_argument("--head", default="HEAD")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_events)

    s = sub.add_parser("bands", help="control bands: check metrics, or open incident + intent on breach")
    s.add_argument("action", choices=("check", "open"))
    s.add_argument("--metrics", required=True, help="JSON {metric: value or [samples...]}")
    s.set_defaults(func=cmd_bands)

    s = sub.add_parser("release-record", help="audit record for a release")
    s.add_argument("--base", required=True, help="previous release ref")
    s.add_argument("--head", default="HEAD")
    s.add_argument("--pr", default="")
    s.add_argument("--approver", action="append", default=[])
    s.add_argument("--out")
    s.set_defaults(func=cmd_release_record)
