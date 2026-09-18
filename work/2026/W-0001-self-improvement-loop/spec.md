---
id: W-0001
type: spec
status: draft
intent: ./intent.md
skills_applied: [retrospect]
risk_tier: T2
approvals: []
---

# Self-improvement loop — Spec

## Requirements
- R1 A ledger (`lessons/ledger.json`) records each lesson: id, title, area, detected_by, detected_at, what happened, root cause, gate_existed, status, control.
- R2 A lesson closes only with a control `path::needle` that exists in the repository; a `rule` control is written into CLAUDE.md.
- R3 `make check` fails when a closed lesson's control disappears; stale open lessons warn.
- R4 Status reports total/open/closed, prevention rate, detectors, control kinds, and controls still in place — in the CLI and the web app.
- R5 Agents are instructed to record and close lessons in the same change as the fix.

## Design
`sdlc/lessons.py` (load/save, add, close, check, status) behind `sdlc lessons status|add|close|check`; `Makefile` adds
`lessons` to `check`; `/api/lessons` and a `lessons.js` view in the web app; `retrospect` skill and a CLAUDE.md rule.

## Acceptance criteria
- AC-1 A lesson cannot be closed with a control that is not in the repository.
- AC-2 A rule control is written into CLAUDE.md between the lessons markers.
- AC-3 `lessons check` fails when a closed lesson's control regresses.
- AC-4 Status reports the prevention rate and controls in place.
- AC-5 The web app serves the ledger at `/api/lessons`.

## Security & compliance notes
No new external input; the ledger is a versioned file. The web endpoint is read-only.

## Alternatives considered
Extending `feedback.py` only — rejected: it covers review comments, not mistakes found by tests, gates, measurement, or incidents.
