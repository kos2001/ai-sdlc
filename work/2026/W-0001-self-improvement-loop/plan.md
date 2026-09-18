---
id: W-0001
type: plan
status: draft
spec: ./spec.md
approvals: []
---

# Self-improvement loop — Plan

## Steps
- [x] `sdlc/lessons.py` and `sdlc lessons` commands
- [x] tests for the loop and six invariant tests as controls for this repo's real mistakes
- [x] seed `lessons/ledger.json` with the 11 real lessons
- [x] `make check` runs `lessons check`
- [x] `/api/lessons`, the Improvement loop screen (ko/en), demo lessons
- [x] `retrospect` skill, CLAUDE.md rule, README (ko/en)

## Test strategy
- W-0001:AC-1 `tests/test_lessons.py` test_close_requires_a_control_that_exists
- W-0001:AC-2 `tests/test_lessons.py` test_rule_control_is_written_into_claude_md
- W-0001:AC-3 `tests/test_lessons.py` test_check_fails_when_a_control_regresses
- W-0001:AC-4 `tests/test_lessons.py` test_status_measures_prevention_and_controls
- W-0001:AC-5 `tests/test_server.py` test_lessons_endpoint_reports_the_loop

## Rollout
Merges behind PR #1; no runtime flag. Roll back by reverting the PR.

## Control bands
Prevention rate (`sdlc lessons status`): baseline 2/11; review monthly, expect it to rise.
