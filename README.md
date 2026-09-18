# ai-sdlc

A working implementation of an AI-native software development lifecycle: every stage ends by committing an
artifact, the next stage starts by reading it, humans approve at the gates, and hooks and CI enforce the policy
while the agent works.

```
intent.md ──accept──▶ spec.md ──approve──▶ plan.md ──approve──▶ code + tests ──▶ PR ──merge──▶ release
    ▲                                                                                              │
    └──────────── incident record ◀── control band breached ◀── production metrics ◀──────────────┘
```

- Design: [`docs/design/ai-native-sdlc-design.md`](docs/design/ai-native-sdlc-design.md)
- Agent rules: [`CLAUDE.md`](CLAUDE.md)

## Quick start

```bash
python3 -m sdlc new "Checkout latency for EU users" --tier T2   # Plan: draft intent
# fill sources / Problem / Desired outcome (or let the capture-intent skill do it)
python3 -m sdlc submit W-0001 --stage intent                     # draft -> proposed
python3 -m sdlc approve W-0001 --stage intent --role product-owner   # human gate
python3 -m sdlc stage W-0001 spec                                # Design: draft spec
make check                                                       # tests + artifact validation
```

Requires Python 3.11+ and git. No third-party packages.

## Web app

A local dashboard over any repository that uses the artifact chain.

```bash
python3 -m sdlc demo /tmp/demo-shop                 # optional: a sample repo with every state (sample data)
python3 -m sdlc --root /tmp/demo-shop serve         # http://127.0.0.1:8791/
```

| Screen | What it shows |
|---|---|
| 소개 · 가이드 | a plain-language comparison with the traditional SDLC, and the full product story (`web/index.html`) embedded in the app |
| 개요 | work in progress, gates waiting on a person, median gate wait (from git), AC coverage, open incidents |
| 작업 보드 | work items by stage: intent → spec → plan → build → done |
| 작업 상세 | the chain with approvals, an audit trail rebuilt from git history (agent vs human commits), AC coverage, artifact text |
| 브랜치 점검 | risk tier of the current branch and the same gates CI runs |
| 인시던트 | control-band breaches and their follow-up intents |

The app can create a draft, create the next stage, and submit (draft → proposed). It has **no approve action**:
any local process, an agent included, could call an HTTP route, so gate decisions stay a person running
`python3 -m sdlc approve` in a terminal. The server binds to 127.0.0.1, refuses other Host headers, and accepts
writes only as JSON with an `X-SDLC: 1` header. `/about` serves the product site (`web/index.html`).
