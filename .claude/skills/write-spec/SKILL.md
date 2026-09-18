---
name: write-spec
description: "Turn an accepted intent.md into a proposed spec.md (requirements, design, numbered acceptance criteria) in one working session, applying the org's standards skills. Use when an intent is accepted, when asked to 'write the spec/design' for a W-NNNN item, or when the on-intent-accepted workflow fires."
---

# Write spec (Play 9 — Requirements & design)

Input: `work/<YYYY>/<W-id>-<slug>/intent.md` with `status: accepted`.
Output: sibling `spec.md` with `status: proposed`.

## Procedure
1. Read `intent.md` fully, then `CLAUDE.md` and the code the intent touches. Refuse to proceed if the intent is not `accepted`.
2. `python3 -m sdlc stage <W-id> spec` creates the draft (id and risk tier are copied from the intent).
3. Load the standards skills that apply and list them in `skills_applied:` (e.g. API, data classification, threat model). Standards the org has not encoded as skills go under "Open questions".
4. Write:
   - `## Requirements` — R1, R2, …; each one testable, each traceable to the intent's problem or outcome.
   - `## Design` — components, interfaces, data flow, and what changes in existing code. Name real files.
   - `## Acceptance criteria` — AC-1, AC-2, …; each maps to an R and can become a test or eval. Tests will cite them as `<W-id>:AC-n`.
   - `## Security & compliance notes` — data touched, authz changes, new dependencies. Raise `risk_tier` if these reveal higher risk; never lower it.
   - `## Alternatives considered` — at least one, with why it lost.
5. `python3 -m sdlc submit <spec path>` and fix what it reports.
6. Stop. The architect approves (T3 needs a second approver). Report the path and any open questions.
