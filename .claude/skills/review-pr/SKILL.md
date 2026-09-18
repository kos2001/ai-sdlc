---
name: review-pr
description: "Run the layered agentic review of a change — risk tier, deterministic gates, then the four reviewer subagents in parallel — and publish evidence-backed findings. Use when asked to review a PR or branch, or when the pr-review workflow fires."
---

# Review PR (Play 10 — layered agentic review)

Follow `REVIEW.md` for severity, evidence, and output format.

## Procedure
1. **Context.** Identify the work item (`W-NNNN` in branch/PR title) and read its intent, spec, and plan.
2. **Deterministic layer first** — run and record results; never argue with them:
   - `python3 -m sdlc risk --base origin/main`
   - `python3 -m sdlc plan-gate --base origin/main --refs "<branch>" "<PR title>"`
   - `python3 -m sdlc eval-guard --base origin/main`
   - `python3 -m sdlc trace <W-id>` and `make check`
3. **Reviewer subagents, in parallel**, each given the diff range and the work item path:
   `spec-conformance-reviewer`, `security-reviewer`, `test-reviewer`, `perf-reviewer`.
4. **Merge findings.** Drop duplicates, keep the highest severity, discard anything without file:line evidence.
5. **Publish** one summary: tier and required human reviewers (from `sdlc risk`), gate results, findings table, AC coverage.
6. You may push fixes for your own findings on the PR branch (max 2 rounds). You never approve or merge.
