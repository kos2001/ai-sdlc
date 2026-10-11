<p align="center"><img src="web/icons/app-icon.svg" width="88" alt="ai-sdlc — a loop in six stage colours around the human gate"></p>

<h1 align="center">ai-sdlc</h1>

<p align="center"><b>The software lifecycle after code stops being the bottleneck.</b><br>
Agents do the work, people make the decisions, tools enforce the rules.</p>

<p align="center"><a href="README.md">한국어</a> · English</p>

---

ai-sdlc is a working reference implementation of Anthropic Applied AI's *AI-native SDLC playbook*.
Every stage ends by **committing an artifact to Git**, and the next stage starts by reading it. People judge only at
**gates**, and hooks and CI enforce policy **at the moment an agent acts**.

- Needs Python 3.11+ and git. No third-party packages (Pillow is optional, only for icon PNGs).
- Parts: a CLI (`python3 -m sdlc`) · Claude Code hooks, skills, and subagents · GitHub Actions · a local web app · a product site.
- Python unit tests, artifact and lesson checks (`make check`), plus separate browser regressions.

## Contents

1. [Why](#why)
2. [Core ideas](#core-ideas)
3. [Quick start](#quick-start)
4. [One work item, end to end](#one-work-item-end-to-end)
5. [CLI reference](#cli-reference)
6. [Artifact format](#artifact-format)
7. [Governance: risk tiers, hooks, approvals](#governance-risk-tiers-hooks-approvals)
8. [The self-improvement loop](#the-self-improvement-loop)
9. [Web app](#web-app)
10. [CI/CD workflows](#cicd-workflows)
11. [The 12 plays and their implementation](#the-12-plays-and-their-implementation)
12. [Adopting it in another repository](#adopting-it-in-another-repository)
13. [Repository layout](#repository-layout)
14. [Development](#development)
15. [Known limits](#known-limits)
16. [Documentation](#documentation)

---

## Why

Agents have cut the build from weeks to hours. But if the planning, review, and release around it still move at the
old pace, the whole cycle doesn't get faster. Three things happen at once:

| What happens | Consequence |
|---|---|
| The bottleneck moves to either side of the build (plan, review, deploy) | The time saved is absorbed by review queues and committee calendars |
| Line-by-line human review stops matching reality | Either the queue grows or code ships under-reviewed |
| Exceptions still route through weekly or monthly committees | Governance cost grows with agent output |

Measured on a real repository: in `lls-kit`, built with Claude, 25 merged PRs had a **median of 10 seconds from open
to merge** and **0 reviews**; replaying ai-sdlc's policy puts 18 of them at T3, where a person should decide.
([method and limits](docs/adoption/lls-kit.md))

## Core ideas

```
intent.md ──accept──▶ spec.md ──approve──▶ plan.md ──approve──▶ code + tests ──▶ PR ──merge──▶ release
    ▲                                                                                              │
    └──────── incident record ◀── control band breached ◀── production metrics ◀───────────────────┘
```

| Idea | Meaning |
|---|---|
| **Artifact chain** | Each stage commits one file (`intent.md` → `spec.md` → `plan.md` → diff+tests → PR → incident). The commit chain is the audit trail. |
| **Human gates** | Only people move `proposed` → `accepted`. Agent identities can't record an approval. T3 specs and plans need two people. |
| **Enforcement at action time** | Claude Code hooks block writes to protected paths, forged approvals, tier lowering, and dangerous commands **before they run**. |
| **Risk tiers T0–T3** | Computed deterministically from the changed paths. They set how much human review a change gets; agents can only raise them. |
| **A closed loop** | When a production metric leaves its control band, an incident and a new `intent.md` open. A person accepts it, and it's Plan again. |

## Quick start

```bash
git clone https://github.com/kos2001/ai-sdlc.git && cd ai-sdlc
make check                                           # unit tests + artifact and lesson checks

# see the web app on a sample repository with every state (sample data)
python3 -m sdlc demo /tmp/demo-shop
python3 -m sdlc --root /tmp/demo-shop serve          # → http://127.0.0.1:8791/?lang=en
```

To use it on your own repository, see [Adopting it in another repository](#adopting-it-in-another-repository).

## One work item, end to end

| # | Stage | Who | Command / action | Result |
|---|---|---|---|---|
| 1 | Plan | agent | `sdlc new "EU checkout latency" --tier T2` → write evidence and problem → `sdlc submit W-0142 --stage intent` | `intent.md` proposed |
| 2 | Gate | **product owner** | `sdlc approve W-0142 --stage intent --role product-owner` | intent accepted |
| 3 | Design | agent | `sdlc stage W-0142 spec` → requirements, design, `AC-n` → `submit` | `spec.md` proposed |
| 4 | Gate | **architect** (two at T3) | `sdlc approve W-0142 --stage spec --role architect` | spec accepted |
| 5 | Build (plan) | agent | `sdlc stage W-0142 plan` → checklist, test strategy, rollout, control bands → `submit` | `plan.md` proposed |
| 6 | Gate | **tech lead** | `sdlc approve W-0142 --stage plan --role tech-lead` | code may start |
| 7 | Build · Test | agent | tag tests `W-0142:AC-1`, tick plan steps `- [x]`, `sdlc trace W-0142 --strict`, `make check` | PR |
| 8 | Deploy | CI + as many people as the tier needs | `risk` · `plan-gate` · `eval-guard` · `transitions` · reviewer subagents | merge, release record |
| 9 | Done | tech lead | `sdlc done W-0142 --stage plan` (only once every AC is traced) | plan done |
| 10 | Maintain | tools + a person | `sdlc bands open --metrics m.json` → incident + follow-up intent | back to 1 |

> Agents go as far as `submit` (draft → proposed). Hooks block `approve` from agents, and the web app has no approve
> button. A person runs it in their own terminal.

## CLI reference

Every command is `python3 -m sdlc [--root <repo>] <command>` and exits non-zero on a violation, so hooks and CI can
use it directly.

**Artifacts**

| Command | What it does |
|---|---|
| `new <title> [--owner O] [--tier T0..T3]` | Create a draft `work/<year>/W-NNNN-<slug>/intent.md` |
| `stage <W-id> spec\|plan` | Create the next draft once the previous stage exists (copies id and tier) |
| `submit <path \| W-id --stage S>` | draft → proposed, saved only if it validates as proposed |
| `approve … --role R [--by name]` | Record a person's approval; accepted once enough are in. Agent identities refused |
| `reject … --reason text` | proposed → rejected |
| `done …` | accepted → done; every plan box ticked and every AC traced |
| `validate [--changed]` | Schema, chain, and approval rules for every artifact |
| `trace [W-id] [--json] [--strict]` | Acceptance criteria → tagged tests coverage |

**Gates (CI runs these on PRs)**

| Command | What it does |
|---|---|
| `transitions --base REF` | Blocks illegal status changes, edited or removed approvals, tier lowering, deleted artifacts |
| `risk [--base REF] [--floor T] [--json] [paths…]` | Risk tier and required human reviews from path rules |
| `plan-gate [--base REF] [--refs branch "PR title"…]` | Non-T0 changes need a W-NNNN with an accepted `plan.md` |
| `eval-guard [--base REF]` | Flags deleted tests/evals, removed test definitions or AC tags, added skips |

**Loop and operations**

| Command | What it does |
|---|---|
| `events --base REF [--json]` | Status changes → next play and skill (orchestrator input) |
| `bands check\|open --metrics m.json` | Judge control bands / on breach, open incident + proposed intent (deduplicated) |
| `feedback comments.json… [--out file]` | `[rule]` / `[bug]` / `[false-positive]` review comments → rule and eval candidates |
| `lessons status\|add\|close\|check` | The self-improvement loop: mistake → lesson → a control the repo checks ([below](#the-self-improvement-loop)) |
| `release-record --base REF [--pr N] [--approver name…]` | Tier, work items, human approvers, agent co-authors |
| `hook pre-tool-use\|post-tool-use\|stop\|user-prompt-submit` | Claude Code hook handler (JSON on stdin) |
| `serve [--port 8791]` | Local web app (127.0.0.1 only) |
| `demo <dir>` | Build a sample repository that goes through every state |

## Artifact format

Markdown with YAML frontmatter (a deliberately narrow subset). Templates in [`templates/`](templates/).

```yaml
---
id: W-0142
type: intent            # intent | spec | plan | incident
status: proposed        # draft → proposed → accepted → done  (rejected, superseded)
owner: "Dana Park <dana@example.com>"
sources:                # at least one once proposed
  - kind: ticket
    ref: SUP-8812
risk_tier: T2           # T0..T3, can only go up
origin: human           # human | maintain-loop
approvals: []           # people only, append-only
---
```

| File | Required sections / rules |
|---|---|
| `intent.md` | Can't be submitted with an empty `## Problem` or `## Desired outcome` |
| `spec.md` | Submitted only after the intent is accepted; `AC-1…` under `## Acceptance criteria` |
| `plan.md` | Submitted only after the spec is accepted; `- [ ]` checklist under `## Steps`; done needs every box and every AC traced |
| `incidents/<year>/INC-*.md` | open → diagnosed → closed; closed needs a follow-up intent or a resolution |

## Governance: risk tiers, hooks, approvals

**Risk tiers** — [`policy/risk-tiers.json`](policy/risk-tiers.json). The highest matching rule wins.

| Tier | Examples | Human reviews | Release |
|---|---|---|---|
| T0 | docs, `work/**` | 0 (sampled audit afterwards) | auto |
| T1 | ordinary feature code, tests | 0 (sampled audit afterwards) | auto + canary |
| T2 | migrations, public APIs, dependencies, `CLAUDE.md` and skills | 1 (findings first) | auto + canary |
| T3 | auth, payments, regulated data, IaC permissions, the controls themselves | 2 (line by line) | `production` environment approval |

**Hooks** — [`.claude/settings.json`](.claude/settings.json) → `sdlc/hooks.py`, rules in [`policy/guard.json`](policy/guard.json).

| Event | Behaviour |
|---|---|
| PreToolUse | Blocks dangerous commands (force push, direct push to main, `--no-verify`, `sdlc approve`, `curl \| sh`, `terraform apply`, `gh pr merge` …), writes to protected paths (`policy/**`, `.claude/settings.json`, `.github/workflows/**`, `sdlc/hooks.py` …), and, in artifacts, recorded approvals, gate status changes, and tier lowering |
| PostToolUse | Validates the artifact just edited and hands problems back to the agent |
| Stop | Won't let the session end while changed artifacts are invalid (once) |
| UserPromptSubmit | Injects the work item named in the branch (W-NNNN) and its status |

Hooks fail **closed** on malformed input or a broken policy file.

**Approval rules** — people only (`claude`, `anthropic`, `[bot]`, `github-actions` refused), no duplicate approver,
append-only (checked by `transitions` on PRs), two for T3 specs and plans.

## The self-improvement loop

Agents make mistakes. What matters is that the same mistake **never quietly comes back**.

```
mistake caught ──▶ lessons add (lesson, open) ──▶ write a control ──▶ lessons close (only with a control)
      ▲                                                                              │
      └──── make check / CI: fails if a closed lesson's control disappears ◀─────────┘
```

| Part | What it is |
|---|---|
| Ledger | [`lessons/ledger.json`](lessons/ledger.json) — per lesson: who found it (`gate`, `test`, `review`, `human`, `measurement`, `incident`), what happened, root cause, **whether an existing gate caught it first**, and the control |
| Control | `path::needle` — a file and text that must stay in the repository. Kinds: `test`, `rule` (written into CLAUDE.md automatically), `policy`, `eval`, `doc` |
| Enforcement | `sdlc lessons check` is part of `make check` — CI fails if a closed lesson's control (a test name, a rule line) disappears. Lessons open for over 30 days warn |
| Measurement | `sdlc lessons status` and the web app's **Improvement loop** screen — share caught first by an existing gate (prevention rate), who found them, control kinds, controls still in place |
| Agents | The [`retrospect`](.claude/skills/retrospect/SKILL.md) skill — when a mistake is caught, record and close it in the same change as the fix |

```bash
python3 -m sdlc lessons add "eval-guard missed deleted check() calls" --detected-by measurement \
  --what "lls-kit tests are check(...) calls, so deleting one passed" --cause "test definition patterns were hard-coded"
python3 -m sdlc lessons close L-012 --kind test --ref "tests/test_gates.py::class EvalGuardHouseStyleTest"
python3 -m sdlc lessons close L-013 --kind rule --rule "Re-measure over the full set before reporting a pattern."
python3 -m sdlc lessons status
```

This repository's ledger started with 11 mistakes actually made while building it. At that point nine were closed
by tests or rules and two were open. **An existing gate caught only 2 of those initial 11 first (18%)**; people,
reviews and measurements found the rest after the fact. Read current figures and additional lessons with
`python3 -m sdlc lessons status` or the Improvement loop screen.

## Web app

```bash
python3 -m sdlc --root <repo> serve        # http://127.0.0.1:8791/  (한국어 / English)
```

| Screen | Contents |
|---|---|
| Intro | What changes from the traditional SDLC — at a glance, stage by stage, who does what, live cards from this repository, FAQ |
| Guide | The full story (`web/index.html`) inside the app |
| Overview | Work in progress, gates waiting on people, median gate wait (from git), AC coverage, open incidents, approval commands to copy |
| Board | Board/list views, search/filter/sort, work preview drawer. Filters persist in the URL and are restored when returning from details |
| Work item | Chain, audit trail, AC coverage, keyboard tabs, draft body/evidence editing, Markdown formatting, preview, save and submit |
| Branch check | Choose a comparison ref, inspect risk and CI gates, retry errors |
| Incidents | Control band breaches and follow-up intents, search and status filters |
| Improvement loop | Ledger, prevention rate and controls, search and status/detector filters |

Overview counts and stage links open a filtered board. New work opens its intent editor.
Use **Quick switch** or **Ctrl/⌘ K** to search work and screens, then use arrow keys and Enter to open a result.
**Preview** on the board opens a read-only drawer; Escape returns focus to the same item.
Select text in a draft to format headings, bold, lists, checklists or code. **Ctrl/⌘ S** saves changes.
Write the body and evidence, **Save changes**, then **Submit**. Unsaved inputs survive tab,
language and in-app refresh changes; leaving asks for confirmation. An external file change
blocks saving and preserves your input. Loading the latest file asks before discarding input.
Submitted artifacts are read-only. Human approvals use the existing CLI.

**API** (all JSON)

| Method | Path | Description |
|---|---|---|
| GET | `/api/overview` | Summary figures and the approval queue |
| GET | `/api/work`, `/api/work/W-NNNN` | Work list / detail (with text and audit trail) |
| GET | `/api/branch?base=REF` | Risk tier, gate results, events |
| GET | `/api/incidents` | Incidents |
| GET | `/api/lessons` | The lessons ledger and its measures |
| POST | `/api/work` | Create a draft intent `{title, owner, tier}` |
| POST | `/api/work/W-NNNN/draft` | Save draft `{stage, body, revision, sources?}`. Sources are intent-only. Detail responses contain revisions. Stale revisions/non-drafts return 409; invalid input returns 400 |
| POST | `/api/work/W-NNNN/stage` | Draft the next stage `{stage}` |
| POST | `/api/work/W-NNNN/submit` | Submit `{stage}` — gate violations return 409 |

**Security model**: binds to 127.0.0.1 only; a non-loopback Host header gets 403 (blocks DNS rebinding); writes need
`Content-Type: application/json` plus an `X-SDLC: 1` header; static files never leave the app folder.
**There is deliberately no approve endpoint** — any local process, an agent included, could call an HTTP route.
Draft editing preserves approval, status, tier, owner and other gate metadata. HTTP writes
are serialized and files are atomically replaced. Revisions detect outside changes; there
is no cross-process transaction lock with an external editor.

## CI/CD workflows

| Workflow | When | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | PR, review, push to main | `make check`, transitions, plan-gate, eval-guard (label `eval-change-approved` to override), risk label and required human approvals |
| [`pr-review.yml`](.github/workflows/pr-review.yml) | PR | Subagent review via the `review-pr` skill; posts findings |
| [`advance.yml`](.github/workflows/advance.yml) | `work/**` changes on main | `sdlc events` → runs the next play's skill, opens a PR |
| [`control-band.yml`](.github/workflows/control-band.yml) | `repository_dispatch` | Metrics → incident + intent + diagnosis PR |
| [`feedback.yml`](.github/workflows/feedback.yml) | Mondays | Tagged review comments → CLAUDE.md rules and regression evals PR |
| [`release.yml`](.github/workflows/release.yml) | push to main | Release record; T3 deploys wait for `production` environment approval |

To configure: secret `ANTHROPIC_API_KEY`, variable `DEPLOY_COMMAND`, required reviewers on the `production`
environment, team names in [`.github/CODEOWNERS`](.github/CODEOWNERS), and "Require review from Code Owners" in branch protection.

## The 12 plays and their implementation

| Play | Implementation |
|---|---|
| 1 Capture intent | `sdlc new/submit`, `capture-intent` skill |
| 2 CLAUDE.md | root [`CLAUDE.md`](CLAUDE.md) |
| 3 Skills | 8 in [`.claude/skills/`](.claude/skills) |
| 4 Feedback loop | `sdlc feedback`, `apply-feedback`, `feedback.yml`, the self-improvement loop (`sdlc lessons`, `retrospect`) |
| 5 Hooks | `sdlc/hooks.py`, `policy/guard.json` |
| 6 Plan mode | `plan-from-spec`, `sdlc plan-gate` |
| 7 Subagents | [`.claude/agents/`](.claude/agents) — spec-conformance · security · test · perf (read-only) |
| 8 Evals | `sdlc trace`, `sdlc eval-guard` |
| 9 Requirements & design | `write-spec`, `advance.yml` |
| 10 PR review | `review-pr`, [`REVIEW.md`](REVIEW.md), `ci.yml` |
| 11 CI/CD | `ci.yml`, `release.yml`, `sdlc release-record` |
| 12 Closing the loop | `sdlc bands`, `incident-to-intent`, `control-band.yml` |

## Adopting it in another repository

1. Copy `sdlc/`, `templates/`, and `policy/` (`sdlc/` has no third-party dependencies).
2. Adapt the path rules in `policy/risk-tiers.json`. If tests aren't written as `def test_`, add the house pattern to
   `policy/eval-guard.json`, e.g. `{"test_definitions": ["^\\s*check\\("]}`.
3. Turn on the hooks with `.claude/settings.json`, and add a section on the artifact chain to `CLAUDE.md`.
4. Use W-NNNN for new work; don't backfill history.
5. Add CI.

A real case: [`docs/adoption/lls-kit.md`](docs/adoption/lls-kit.md) — replaying it on a 3GPP simulator repository,
what had to change (a single-owner repo, a 12 KB file cap, a `check(...)` test style), and the adoption order.

## Repository layout

```
sdlc/                 CLI and library (standard library only, ≤12 KB per file)
  artifacts.py        schemas, status machine, rules      frontmatter.py  YAML-subset parser
  workitems.py        new/stage/submit/approve/done       trace.py        AC → test tracing
  risk.py · policy.py risk tiers, path globs              gates.py        plan-gate, eval-guard
  hooks.py            Claude Code hook handlers           events.py       status change → next play
  bands.py            control band → incident + intent    release.py      release record
  feedback.py         review comments → rule/eval ideas   api.py · server.py  web app backend
  lessons.py          the self-improvement loop (lesson → control)
  demo.py             sample repository builder           cli.py · cli_ops.py command definitions
  webapp/             web app frontend (no build step, Korean/English)
templates/            intent · spec · plan · incident templates
policy/               guard.json (hook rules), risk-tiers.json (tiers)
.claude/              settings.json (hooks), 8 skills, 4 agents
.github/workflows/    ci · pr-review · advance · control-band · feedback · release
web/index.html        product site (Korean/English, also the in-app Guide) · web/icons/ icons
bands/                example control bands
lessons/ledger.json   the lessons ledger
scripts/make_icons.py icon generator
docs/                 design/ design doc · adoption/ case study · patches/ pending patch
tests/                Python unittest + frontend.js browser regressions
```

## Development

```bash
make check                                  # unit tests + artifact validation + lesson controls (same as CI)
python3 -m unittest tests.test_server -v    # one module
python3 scripts/make_icons.py [--png]       # regenerate icons (PNGs need Pillow)
```

Browser checks use Node.js and a separately installed Playwright/Chromium. These are not
product dependencies. The runner builds and cleans up an isolated temporary demo repository.

```bash
export SDLC_PLAYWRIGHT=/absolute/path/to/node_modules/playwright
# Optional: use an already installed Chromium
export SDLC_CHROMIUM=/absolute/path/to/chromium
python3 scripts/check_frontend.py
```

Checks cover board navigation, create/edit/save/submit, concurrent/failed/delayed responses,
save conflicts, keyboard tabs and 375px/desktop × Korean/English × light/dark rendering.
Screenshots default to `/private/tmp/ai-sdlc-frontend-qa`; override with `SDLC_SCREENSHOTS`.

- Standard library only; tests use `unittest`. Commands exit non-zero on violations.
- Keep `sdlc/` files at 12 KB or less (repositories that copy this package may gate on input size).
- Agent rules in [`CLAUDE.md`](CLAUDE.md); review standards in [`REVIEW.md`](REVIEW.md).
- Commit on feature branches; reach `main` through PRs.

## Known limits

- **The hook's shell-write check is over-eager.** It can block a command that only *mentions* a protected path. A fix
  that judges only real write targets, with tests, is in
  [`docs/patches/0001-…`](docs/patches/0001-hook-target-aware-shell-writes.patch). The file is protected, so an agent
  can't apply it; a person applies it with `git apply`.
- Shell-write detection is heuristic (relative paths after `cd`, writes inside `python -c` are missed). CODEOWNERS and CI are the backstop.
- `approvals` live in frontmatter, so a person could hand-forge one. Required CODEOWNERS review and PR approval records cover this.
- `ci.yml` counts approvals; whether the approver is a code owner must be enforced by branch protection.
- There is no single-owner mode yet (GitHub doesn't allow approving your own PR).
- `pr-review`, `advance`, `control-band`, and `feedback` haven't run on GitHub yet (`ci` and `release` pass).

## Documentation

| Document | Contents |
|---|---|
| [`docs/design/ai-native-sdlc-design.md`](docs/design/ai-native-sdlc-design.md) | Design doc (Korean): principles, architecture, artifact spec, 12 plays, governance, roadmap, status |
| [`docs/adoption/lls-kit.md`](docs/adoption/lls-kit.md) | Adoption review and measurements on a real repository (Korean) |
| [`CLAUDE.md`](CLAUDE.md) · [`REVIEW.md`](REVIEW.md) | Agent operating rules · review policy |
| `web/index.html` | Product site (`/about` after `serve`, and the in-app Guide) |
