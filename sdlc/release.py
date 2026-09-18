"""Release record (Play 11): what shipped, from which PR, at which tier, approved by whom."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from . import artifacts, gates, gitutil, risk


def record(root: Path, base: str, head: str = "HEAD", pr: str = "", approvers: list[str] | None = None,
           now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    sha = gitutil.run(["rev-parse", head], root).strip()
    commits = gitutil.run(["log", "--format=%h %an: %s", f"{base}..{head}"], root).strip().splitlines()
    trailers = gitutil.run(["log", "--format=%(trailers:key=Co-Authored-By,valueonly)", f"{base}..{head}"], root)
    agents = sorted({t.strip() for t in trailers.splitlines() if t.strip()})
    changed = [p for _, p in gitutil.changed_files(root, base, head)]
    tier = risk.assess(root, changed)
    ids = gates.work_ids(" ".join(changed) + " " + " ".join(commits))
    lines = [
        f"# Release {sha[:12]}",
        "",
        f"- **When:** {now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Commit:** `{sha}`",
        f"- **PR:** {pr or 'n/a'}",
        f"- **Risk tier:** {tier['tier']} (release policy: {tier['release']}, human reviews required: {tier['human_reviews']})",
        f"- **Human approvers:** {', '.join(approvers) if approvers else 'none recorded'}",
        f"- **Agent co-authors:** {', '.join(agents) if agents else 'none'}",
        "",
        "## Work items",
    ]
    for work_id in ids:
        dirs = sorted((root / artifacts.WORK_DIR).glob(f"*/{work_id}-*"))
        if not dirs:
            continue
        states = []
        for name in artifacts.STAGE_FILES:
            art = artifacts.load(dirs[0] / name, root)
            if not art.load_error:
                who = ", ".join(a.get("by", "?") for a in art.meta.get("approvals") or [] if isinstance(a, dict))
                states.append(f"{name} {art.status}" + (f" by {who}" if who else ""))
        lines.append(f"- {work_id} (`{dirs[0].relative_to(root).as_posix()}`): " + "; ".join(states))
    if not ids:
        lines.append("- none referenced")
    lines += ["", "## Commits", *[f"- {c}" for c in commits]]
    return "\n".join(lines) + "\n"
