---
name: implement-plan
description: "Implement an accepted plan.md step by step on a W-NNNN branch: tests tagged to acceptance criteria, plan boxes ticked, make check green, then open a PR. Use when a plan.accepted event fires or when asked to build an approved W-NNNN item."
---

# Implement plan (Build)

Precondition: `plan.md` is `accepted` (the plan gate in CI rejects PRs otherwise).

## Procedure
1. Branch `feature/<w-id>-<slug>` (lower-case is fine; the W-id must appear).
2. For each step in `## Steps`, in order (parallel steps may go to subagents in separate worktrees):
   - Write the test first, tagged `<W-id>:AC-n` for the criterion it proves.
   - Implement until it passes. Follow CLAUDE.md conventions.
   - Tick the box `- [x]` in the same commit. If you had to deviate, edit the step text in that commit and say why.
3. `python3 -m sdlc trace <W-id> --strict` — every AC covered.
4. `make check` green. Never skip, delete, or loosen tests to get there (`sdlc eval-guard` will catch it).
5. Push the branch and open a PR titled `<W-id>: <summary>` using the template; the review-pr skill and CI take over.
6. Do not run `sdlc done`, approve, or merge. The tech lead marks the plan done after merge.
