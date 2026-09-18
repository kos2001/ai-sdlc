---
name: retrospect
description: "Turn a mistake into a lesson with a control, so it cannot happen again — the self-improvement loop. Use after fixing a bug you or another agent introduced, when a gate, review, test, or person catches something, when a claim turns out wrong, or when asked to run a retrospective on a work item."
---

# Retrospect (the self-improvement loop)

A fix without a control is a fix that can come back. Every mistake becomes a lesson in
`lessons/ledger.json`, and a lesson closes only with a control the repository can check.

## When
- A test, gate, review, or person caught something you (or another agent) did.
- A statement you made turned out wrong when measured.
- You fixed a bug. Record it in the same change as the fix.

## Procedure
1. **Record it honestly.**
   ```bash
   python3 -m sdlc lessons add "<what went wrong, as a statement>" \
     --detected-by gate|test|review|human|measurement|incident \
     --what "<what happened, observable>" --cause "<root cause, not the symptom>" \
     [--gate-existed]  # only if an existing gate caught it before anyone noticed
   ```
   `--gate-existed` is the prevention measure. Do not set it when a person, a review, or a later measurement found it.
2. **Choose the strongest control you can.** Prefer, in order:
   - `test` — a test that fails if the mistake returns (`tests/...py::def test_name`).
   - `policy` — a hook or risk rule (`policy/guard.json::<pattern>`); policy files are human-edited, so propose it.
   - `eval` — an eval case for behaviour a unit test can't pin down.
   - `rule` — a one-line agent rule when the mistake is judgment, not code. `--rule` writes it into CLAUDE.md.
   - `doc` — last resort.
3. **Close it with the control.**
   ```bash
   python3 -m sdlc lessons close L-012 --kind test --ref "tests/test_x.py::def test_guard"
   python3 -m sdlc lessons close L-013 --kind rule --rule "Re-measure over the full set before reporting a pattern."
   ```
   `close` refuses a control that isn't in the repository.
4. If no control is possible yet, leave it **open** and say why in `--cause`. Open lessons are warnings after 30 days.
5. Run `make check` — it includes `sdlc lessons check`, which fails if any closed lesson's control has disappeared.

## Don't
- Don't close a lesson with a control you haven't written.
- Don't delete or weaken a test that a lesson points to; `lessons check` will fail, and it should.
- Don't mark `--gate-existed` to make the numbers look better. The ledger is the measure of the loop.
