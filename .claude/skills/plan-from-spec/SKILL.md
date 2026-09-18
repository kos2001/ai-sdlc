---
name: plan-from-spec
description: "Produce plan.md from an accepted spec.md using plan mode (read-only exploration first), including steps, test strategy mapped to acceptance criteria, rollout, and control bands. Use when a spec is accepted, when asked to 'plan' a W-NNNN item, or when the on-spec-accepted workflow fires."
---

# Plan from spec (Play 6 — Plan mode)

Input: accepted `spec.md`. Output: `plan.md` in status `proposed`. No implementation code in this skill.

## Procedure
1. Work read-only (plan mode): read the spec, `CLAUDE.md`, and every file the design names. Find existing helpers to reuse.
2. `python3 -m sdlc stage <W-id> plan`.
3. Write:
   - `## Steps` — ordered `- [ ]` checklist, each step naming files. Mark independent steps "(parallel)".
   - `## Test strategy` — for every `AC-n` in the spec, the test or eval that proves it and where it will live. Every AC appears here.
   - `## Rollout` — flag/canary, and the condition that triggers rollback.
   - `## Control bands` — metrics to watch after deploy with min/max thresholds; these become `bands/<service>.json` entries.
4. `python3 -m sdlc submit <plan path>`.
5. Stop and hand to the tech lead. Implementation starts only after `plan.md` is `accepted`; the plan gate in CI enforces this.

## While implementing later
- Tick steps `- [x]` as they land. If reality departs from the plan, edit the plan in the same commit.
- Tag tests with `<W-id>:AC-n`. `python3 -m sdlc trace <W-id>` shows what is still uncovered.
