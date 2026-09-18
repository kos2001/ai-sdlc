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
