"""Self-improvement loop: every mistake becomes a lesson, and a lesson closes only with a control.

    lessons/ledger.json   one entry per lesson (the loop's memory, versioned like everything else)

A control is `path::needle` — a file in the repository and text that must stay in it: a test name,
a CLAUDE.md rule, a policy pattern. `check` fails when a closed lesson's control has disappeared,
so a fixed mistake cannot quietly come back. `status` measures the loop: how often an existing gate
caught the problem (prevention) versus a person finding it first, and how long lessons stay open.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import statistics
from pathlib import Path

LEDGER = Path("lessons") / "ledger.json"
KINDS = ("test", "rule", "policy", "eval", "doc")
DETECTORS = ("gate", "test", "review", "human", "measurement", "incident")
RULES_START, RULES_END = "<!-- lessons:start -->", "<!-- lessons:end -->"
REQUIRED = ("id", "title", "detected_by", "detected_at", "what_happened", "root_cause", "gate_existed", "status")


class LessonError(ValueError):
    pass


def _today() -> str:
    return dt.date.today().isoformat()


def load(root: Path) -> list[dict]:
    path = root / LEDGER
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise LessonError(f"{LEDGER} must be a JSON list")
    return data


def save(root: Path, lessons: list[dict]) -> None:
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lessons, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def control_holds(root: Path, ref: str) -> tuple[bool, str]:
    """`path::needle` — the file exists and (if given) still contains the needle."""
    path, _, needle = ref.partition("::")
    target = root / path
    if not path or not target.is_file():
        return False, f"{path or ref} does not exist"
    if needle and needle not in target.read_text(encoding="utf-8", errors="replace"):
        return False, f"{path} no longer contains {needle!r}"
    return True, "ok"


def next_id(lessons: list[dict]) -> str:
    nums = [int(m.group(1)) for l in lessons if (m := re.match(r"L-(\d+)$", str(l.get("id", ""))))]
    return f"L-{(max(nums) if nums else 0) + 1:03d}"


def add(root: Path, title: str, detected_by: str, what_happened: str, root_cause: str,
        gate_existed: bool, area: str = "", detected_at: str | None = None) -> dict:
    if detected_by not in DETECTORS:
        raise LessonError(f"detected_by must be one of {', '.join(DETECTORS)}")
    lessons = load(root)
    lesson = {"id": next_id(lessons), "title": title, "area": area, "detected_by": detected_by,
              "detected_at": detected_at or _today(), "what_happened": what_happened, "root_cause": root_cause,
              "gate_existed": bool(gate_existed), "status": "open", "control": None}
    lessons.append(lesson)
    save(root, lessons)
    return lesson


def _append_rule(root: Path, rule: str, lesson_id: str) -> str:
    """Add a one-line rule to CLAUDE.md between the lessons markers; returns the exact line."""
    path = root / "CLAUDE.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Agent rules\n"
    line = f"- {rule.strip()} ({lesson_id})"
    if RULES_START not in text:
        text = text.rstrip() + f"\n\n## Lessons learned (maintained by `sdlc lessons`)\n{RULES_START}\n{RULES_END}\n"
    if line not in text:
        text = text.replace(RULES_END, f"{line}\n{RULES_END}", 1)
        path.write_text(text, encoding="utf-8")
    return line


def close(root: Path, lesson_id: str, kind: str, ref: str | None = None, rule: str | None = None) -> dict:
    if kind not in KINDS:
        raise LessonError(f"control kind must be one of {', '.join(KINDS)}")
    lessons = load(root)
    lesson = next((l for l in lessons if l.get("id") == lesson_id), None)
    if lesson is None:
        raise LessonError(f"no lesson {lesson_id}")
    if kind == "rule":
        if not rule:
            raise LessonError("a rule control needs --rule 'the rule text'")
        ref = f"CLAUDE.md::{_append_rule(root, rule, lesson_id)}"
    if not ref:
        raise LessonError("a control needs --ref path::needle")
    ok, why = control_holds(root, ref)
    if not ok:
        raise LessonError(f"control does not hold: {why}")
    lesson.update(status="closed", closed_at=_today(), control={"kind": kind, "ref": ref})
    save(root, lessons)
    return lesson


def check(root: Path, stale_days: int = 30) -> tuple[list[str], list[str]]:
    """(errors, warnings). Errors: malformed entries, duplicate ids, closed lessons whose control is gone."""
    errors, warnings, seen = [], [], set()
    for l in load(root):
        lid = l.get("id", "?")
        missing = [k for k in REQUIRED if k not in l]
        if missing:
            errors.append(f"{lid}: missing {', '.join(missing)}")
            continue
        if lid in seen:
            errors.append(f"{lid}: duplicate id")
        seen.add(lid)
        if l["detected_by"] not in DETECTORS:
            errors.append(f"{lid}: detected_by {l['detected_by']!r} not in {', '.join(DETECTORS)}")
        if l["status"] == "closed":
            control = l.get("control") or {}
            if control.get("kind") not in KINDS or not control.get("ref"):
                errors.append(f"{lid}: closed without a control")
                continue
            ok, why = control_holds(root, control["ref"])
            if not ok:
                errors.append(f"{lid}: control regressed — {why} ({l['title']})")
        elif l["status"] == "open":
            age = (dt.date.today() - dt.date.fromisoformat(l["detected_at"])).days
            if age > stale_days:
                warnings.append(f"{lid}: open for {age} days — {l['title']}")
        else:
            errors.append(f"{lid}: status must be open or closed")
    return errors, warnings


def status(root: Path) -> dict:
    lessons = load(root)
    closed = [l for l in lessons if l.get("status") == "closed"]
    days = [(dt.date.fromisoformat(l["closed_at"]) - dt.date.fromisoformat(l["detected_at"])).days
            for l in closed if l.get("closed_at")]
    detected_by: dict[str, int] = {}
    for l in lessons:
        detected_by[l.get("detected_by", "?")] = detected_by.get(l.get("detected_by", "?"), 0) + 1
    controls: dict[str, int] = {}
    for l in closed:
        kind = (l.get("control") or {}).get("kind", "?")
        controls[kind] = controls.get(kind, 0) + 1
    holding = sum(1 for l in closed if control_holds(root, (l.get("control") or {}).get("ref", ""))[0])
    prevented = sum(1 for l in lessons if l.get("gate_existed"))
    return {
        "total": len(lessons), "open": len(lessons) - len(closed), "closed": len(closed),
        "caught_by_existing_gate": prevented,
        "prevention_rate": round(prevented / len(lessons), 2) if lessons else None,
        "detected_by": detected_by,
        "controls": controls,
        "controls_holding": holding,
        "median_days_to_close": statistics.median(days) if days else None,
        "lessons": lessons,
    }
