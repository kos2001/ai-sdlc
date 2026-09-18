# Review policy

Layered review (design §7 Play 10): deterministic gates → reviewer subagents → humans by risk tier.

## Layers
| Layer | What | Blocks merge when |
|---|---|---|
| Gates | `sdlc validate`, `transitions`, `plan-gate`, `eval-guard`, `make check` | any exits non-zero |
| Agents | spec-conformance, security, test, perf reviewers (`.claude/agents/`) | an unresolved `critical` finding |
| Humans | count from `sdlc risk`: T0/T1 = 0 (sampled audit), T2 = 1 code owner, T3 = 2 incl. domain expert | approvals missing |

## Severity
- **critical** — exploitable, data loss, or breaks an acceptance criterion. Blocks merge.
- **high** — likely defect or policy breach; fix before merge unless a human waives it in the PR.
- **medium** — real but contained; fix or open a follow-up intent.
- **low / nit** — optional. At most 5 nits per review.

## Evidence
Every finding cites `file:line` and the code or fact that proves it. Findings without evidence are dropped.

## Humans
- Review the findings and the summary first; read line by line only at T3.
- Tag comments `[rule]`, `[bug]`, `[false-positive]`, or `[style]` so the feedback loop can learn from them (Play 4).
- Agents can raise a PR's tier with a `risk:T*` label; only humans remove one.
