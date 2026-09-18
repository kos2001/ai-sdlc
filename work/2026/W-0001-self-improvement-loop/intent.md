---
id: W-0001
type: intent
status: proposed
owner: kos2001 <oseok.kim2001@gmail.com>
sources:
  - kind: measurement
    ref: "lls-kit defects.json: 13 of 15 defects found before any gate existed"
  - kind: measurement
    ref: "ai-sdlc build session 2026-09-18: 11 mistakes, 2 caught first by an existing gate"
  - kind: feedback
    ref: "owner request 2026-09-18: 자기 개선 루프를 만들어 줘"
risk_tier: T2
origin: human
approvals: []
---

# Self-improvement loop

> Written after the implementation (PR #2) so the change enters the artifact chain; the owner decides whether it is accepted.

## Problem
Mistakes made while building with agents are fixed but not remembered. In lls-kit, 13 of 15 defects were found before
any gate for them existed, and 10 were found by a person. Building ai-sdlc itself produced 11 mistakes in one session
(hook false positives, a missed test style, an oversized file, a wrong claim from partial data, an encoding bug, a
broken logo); only 2 were caught first by an existing gate. Nothing stops a fixed mistake from quietly coming back.

## Desired outcome
Every caught mistake is recorded with its root cause and closed only by a control the repository can check; CI fails
when such a control disappears. The share of lessons caught first by an existing gate is measured (starting at 2/11)
and visible to people and agents.

## Constraints
Standard library only; files under 12 KB; works in the CLI, CI (`make check`), and the web app; Korean and English UI.

## Out of scope
Automatic creation of lessons from CI failures or hook logs; changing the protected hook (tracked as open lessons L-001, L-011).

## Open questions
Should lessons also be linked to work items (`W-NNNN`) once more work runs through the chain?
