"""Orchestration: which play fires next, derived from artifact changes between two commits.

"An accepted intent.md triggers the requirements and design pass, an approved spec.md
triggers plan mode, a merged PR triggers the pipeline, and a breached control band in
production writes the next intent.md." CI calls `sdlc events` after every push to the
default branch and starts one agent run per event.
"""

from __future__ import annotations

from pathlib import Path

from . import artifacts, gitutil

# (artifact kind, new status) -> (event name, play, skill the agent run should use)
ROUTES = {
    ("intent", "accepted"): ("intent.accepted", "requirements-and-design", "write-spec"),
    ("spec", "accepted"): ("spec.accepted", "plan-mode", "plan-from-spec"),
    ("plan", "accepted"): ("plan.accepted", "build", "implement-plan"),
    ("incident", "open"): ("incident.opened", "closing-the-loop", "incident-to-intent"),
}


def derive(root: Path, base: str, head: str = "HEAD") -> list[dict]:
    events = []
    for status, path in gitutil.changed_files(root, base, head):
        if status == "D" or not artifacts.is_artifact_path(path):
            continue
        new_text = gitutil.show(root, head, path)
        if new_text is None:
            continue
        new = artifacts.load_text(new_text, path, root)
        if new.load_error:
            continue
        old_text = gitutil.show(root, gitutil.merge_base(root, base, head), path)
        old_status = artifacts.load_text(old_text, path, root).status if old_text else None
        if old_status == new.status:
            continue
        route = ROUTES.get((new.kind, new.status))
        if route:
            event, play, skill = route
            events.append({"event": event, "play": play, "skill": skill,
                           "work_id": new.work_id, "path": path})
    return events
