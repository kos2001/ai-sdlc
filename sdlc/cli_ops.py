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

    s = sub.add_parser("lessons", help="self-improvement loop: mistakes -> lessons -> controls that must hold")
    ls = s.add_subparsers(dest="action", required=True)
    a = ls.add_parser("status", help="the ledger and its measures")
    a.add_argument("--json", action="store_true")
    a = ls.add_parser("check", help="fail when a closed lesson's control has regressed")
    a.add_argument("--stale-days", type=int, default=30)
    a = ls.add_parser("add", help="record a mistake as an open lesson")
    a.add_argument("title")
    a.add_argument("--detected-by", required=True, choices=("gate", "test", "review", "human", "measurement", "incident"))
    a.add_argument("--what", required=True, help="what happened")
    a.add_argument("--cause", required=True, help="root cause")
    a.add_argument("--gate-existed", action="store_true", help="an existing gate caught it (prevention worked)")
    a.add_argument("--area", default="")
    a = ls.add_parser("close", help="close a lesson with a control that exists in the repository")
    a.add_argument("id")
    a.add_argument("--kind", required=True, choices=("test", "rule", "policy", "eval", "doc"))
    a.add_argument("--ref", help="path::needle that must stay in the repository")
    a.add_argument("--rule", help="with --kind rule: one-line rule appended to CLAUDE.md")
    s.set_defaults(func=cmd_lessons)

    s = sub.add_parser("serve", help="local web app for this repository (127.0.0.1 only)")
    s.add_argument("--port", type=int, default=8791)
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("demo", help="build a sample repository that exercises the whole loop")
    s.add_argument("dir", help="empty or missing directory to create")
    s.set_defaults(func=cmd_demo)


def cmd_serve(args) -> int:
    from . import server
    root = _root(args)
    try:
        httpd = server.serve(root, port=args.port)
    except OSError as exc:
        print(f"ERROR cannot listen on 127.0.0.1:{args.port} ({exc.strerror}); pick another with --port", file=sys.stderr)
        return 1
    print(f"ai-sdlc: http://127.0.0.1:{httpd.server_address[1]}/  (repository {root})  Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def cmd_demo(args) -> int:
    from . import demo
    root = demo.build(Path(args.dir).resolve())
    print(f"sample repository: {root}\nnext: python3 -m sdlc --root {root} serve")
    return 0


def cmd_lessons(args) -> int:
    from . import lessons
    root = _root(args)
    try:
        if args.action == "add":
            l = lessons.add(root, args.title, args.detected_by, args.what, args.cause, args.gate_existed, args.area)
            print(f"{l['id']} opened: {l['title']}")
            return 0
        if args.action == "close":
            l = lessons.close(root, args.id, args.kind, args.ref, args.rule)
            print(f"{l['id']} closed by {l['control']['kind']}: {l['control']['ref']}")
            return 0
        if args.action == "check":
            errors, warnings = lessons.check(root, args.stale_days)
            for w in warnings:
                print(f"WARN {w}", file=sys.stderr)
            for e in errors:
                print(f"ERROR {e}", file=sys.stderr)
            if not errors:
                print(f"lessons: ok ({len(lessons.load(root))} in ledger)")
            return 1 if errors else 0
    except lessons.LessonError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    st = lessons.status(root)
    if args.json:
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0
    rate = f"{st['prevention_rate']:.0%}" if st["prevention_rate"] is not None else "—"
    print(f"lessons {st['total']} · open {st['open']} · closed {st['closed']} · controls holding {st['controls_holding']}/{st['closed']}")
    print(f"caught by an existing gate: {st['caught_by_existing_gate']}/{st['total']} ({rate}) — the rest were found after the fact")
    print(f"detected by: {st['detected_by']} · controls: {st['controls']} · median days to close: {st['median_days_to_close']}")
    for l in st["lessons"]:
        mark = "open  " if l["status"] == "open" else "closed"
        print(f"  [{mark}] {l['id']} {l['title']}")
    return 0
