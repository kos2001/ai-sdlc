"""Play 4: turn tagged human review comments into rule and eval candidates.

Reviewers prefix a comment with a tag:

    [rule]            a convention the agent should always follow -> CLAUDE.md candidate
    [bug]             a defect the agent introduced               -> regression eval candidate
    [false-positive]  an agent review finding that was wrong      -> reviewer prompt tuning
    [style]           taste; collected but never promoted automatically

Input is the JSON array returned by
`gh api repos/{owner}/{repo}/pulls/comments --paginate` (or a concatenation of such arrays).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

TAG = re.compile(r"^\s*\[(rule|bug|false-positive|style)\]\s*", re.IGNORECASE)
PROMOTE_AT = 2  # same lesson twice -> it belongs in CLAUDE.md, a skill, or a hook


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", text)).strip().lower().rstrip(".")


def load_comments(paths: list[Path]) -> list[dict]:
    comments = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        comments.extend(data if isinstance(data, list) else [data])
    return comments


def collect(comments: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for c in comments:
        body = (c.get("body") or "").strip()
        m = TAG.match(body)
        if not m:
            continue
        text = body[m.end():].split("\n", 1)[0].strip()
        grouped[m.group(1).lower()].append({
            "text": text,
            "path": c.get("path", ""),
            "line": c.get("line") or c.get("original_line"),
            "url": c.get("html_url", ""),
            "author": (c.get("user") or {}).get("login", ""),
        })
    return grouped


def repeated(items: list[dict]) -> list[tuple[str, list[dict]]]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[_normalise(item["text"])].append(item)
    return sorted(((v[0]["text"], v) for v in buckets.values() if len(v) >= PROMOTE_AT),
                  key=lambda kv: -len(kv[1]))


def report(grouped: dict[str, list[dict]]) -> str:
    lines = ["# Review feedback inbox", ""]
    rules = grouped.get("rule", [])
    promote = repeated(rules)
    lines += ["## Promote to CLAUDE.md (seen at least twice)", ""]
    lines += [f"- [ ] {text} — {len(items)}x: " + ", ".join(i["url"] or i["path"] for i in items)
              for text, items in promote] or ["_none_"]
    lines += ["", "## Regression eval candidates ([bug])", ""]
    lines += [f"- [ ] {b['text']} — `{b['path']}:{b['line']}` {b['url']}".rstrip() for b in grouped.get("bug", [])] or ["_none_"]
    lines += ["", "## Agent reviewer false positives", ""]
    lines += [f"- {f['text']} — `{f['path']}` {f['url']}".rstrip() for f in grouped.get("false-positive", [])] or ["_none_"]
    once = [r for r in rules if all(r not in items for _, items in promote)]
    lines += ["", "## Rules seen once (watch list)", ""]
    lines += [f"- {r['text']} — {r['url'] or r['path']}" for r in once] or ["_none_"]
    return "\n".join(lines) + "\n"
