---
name: apply-feedback
description: "Turn the review feedback inbox (from `sdlc feedback`) into small PRs that update CLAUDE.md rules, add regression evals, or tune reviewer subagents. Use weekly, when the feedback workflow fires, or when asked to 'learn from review comments'."
---

# Apply feedback (Play 4 — Feedback loop)

Input: the report written by `python3 -m sdlc feedback <comments.json> --out evals/feedback/inbox.md`.

## Procedure
1. **Promote rules seen twice.** Add each as one imperative line under "Things agents get wrong here" in the nearest `CLAUDE.md` (service-level if it is service-specific). Merge with an existing line rather than duplicating.
2. **Bugs → regression evals.** For each `[bug]`, add a failing-then-passing test under `tests/` or a case under `evals/`, citing the PR URL in a comment.
3. **False positives → reviewer tuning.** Add a "Do not flag" line to the matching `.claude/agents/*-reviewer.md` with the example.
4. Leave single-occurrence rules and `[style]` alone.
5. One PR per category, titled `feedback: ...`. These change agent instructions (tier T2), so a human owner approves; never merge them yourself.
