# AI-native SDLC — agent operating rules

This repo runs the Plan → Design → Build → Test → Deploy → Maintain loop through committed artifacts.
Design rationale: `docs/design/ai-native-sdlc-design.md`.

## Commands
- `make check` — unit tests + artifact validation + lesson controls. Run it before saying work is done.
- `python3 -m sdlc lessons status` — the self-improvement ledger (`lessons/ledger.json`).
- `python3 -m sdlc validate` — schema, chain, and approval rules for every artifact.
- `python3 -m sdlc new "<title>" --tier T1` / `stage <W-id> spec|plan` / `submit <path>` — create and propose artifacts.
- `python3 -m sdlc trace <W-id>` — which acceptance criteria have tagged tests.

## The artifact chain (never skip a link)
1. Every change starts from `work/<YYYY>/<W-id>-<slug>/intent.md`. No intent → ask for one, don't code.
2. Read the upstream artifact before writing the next: intent → spec → plan → code + tests.
3. Do not start code until `plan.md` is `accepted`. If implementation departs from the plan, update `plan.md` in the same commit.
4. Tag every test that proves an acceptance criterion with `W-NNNN:AC-n` in a comment or test name.
5. Mark plan steps `- [x]` as you finish them; `sdlc done` refuses while any box is open or any AC is untraced.

## Gates are human
- Never run `sdlc approve`, never write into `approvals:`, never set `status: accepted|done` by hand. You may `submit` (draft → proposed).
- Never lower a `risk_tier`. Raise it if the change touches auth, payments, PII, crypto, or infra permissions.
- Artifacts are never deleted; they become `rejected` or `superseded`.

## Protected paths (hooks block edits; propose changes in chat instead)
`policy/**`, `.claude/settings.json`, `.claude/hooks/**`, `.github/workflows/**`.

## Code conventions
- Python 3.11+, standard library only in `sdlc/`. Tests use `unittest` under `tests/`.
- Commands exit non-zero on violations so hooks and CI can rely on them.

## Things agents get wrong here
<!-- Append a line when the same review comment appears twice (Play 4: feedback loop). -->
- When something you did is caught — by a test, gate, review, measurement, or person — record it with the
  retrospect skill (`sdlc lessons add`) in the same change as the fix, and close it with a control that
  would catch it next time (`sdlc lessons close`). Never weaken a test a lesson points to.

## Lessons learned (maintained by `sdlc lessons`)
<!-- lessons:start -->
- Before reporting a pattern from data, re-measure it over the full set and cite the count. (L-005)
<!-- lessons:end -->
