---
id: cost-control
title: Cost Control
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - inference-router
  - loop-budget
  - capability-gate
last_updated: 2026-04-29
depended_on_by:
  - ai-gateway
  - evaluation
  - multi-agent-policy
  - task-manager
---
# Cost Control

## Purpose

Specify the principles, knobs, and circuit breakers that
keep an agentic system from melting wallets and batteries.
Agents that loop, hallucinate tool calls, or chase
diminishing returns can burn through budget fast. Cost
control is a first-class concern, not a footnote.

## What "cost" means here

Three resources we track:

- **Tokens** (compute spent on local or remote
  inference). Tokens are time on local; tokens are money
  on remote.
- **Energy** (battery on portable devices, AC draw on
  fixed). Tied to tokens but with different curves: local
  inference can dominate energy.
- **Wall-clock latency** (the user's time). Cheap
  by-the-token can still be expensive by-the-second.

A cost-aware harness reasons about all three.

## Knobs Kiki exposes

### Per-request budgets

The inference router takes a `cost_limit`:

- `tokens_in`, `tokens_out` — hard caps
- `latency_budget` — Realtime / Conversational /
  Background / Whenever
- `energy_budget` — `low`, `normal`, `high` (maps to
  battery thresholds and hardware throttling)

The router refuses or downgrades requests that exceed.

### Per-user budgets

A user on a metered backend plan has a rolling budget:

```
plan_period_tokens_in   plan_period_tokens_out
consumed_in             consumed_out
period_start             period_end
```

Once consumed crosses the plan, the router falls back to
local-only for that user. The user can opt in to overage
(a separate budget bucket) or accept local-only.

Local inference does not consume the metered budget;
energy/time still apply.

### Per-app budgets

An app's manifest can declare:

```toml
[budget]
max_tokens_per_call = 8000
max_calls_per_hour = 60
max_subagent_spawns_per_call = 0
```

The runtime enforces these in addition to user-level
budgets. Apps that exceed get a `budget.rate_limited`
error; the app can surface to the user or back off.

### Loop budgets

The agent loop has a step budget (default 25; see
`LOOP-BUDGET.md`). At 80%, the loop emits a `WrapUpHint`
inviting the model to conclude. At 100%, the loop stops
and surfaces.

Loop budgets are the single most important guard against
runaway costs. They convert "agent is in trouble" into
"agent stops".

## Circuit breakers

Beyond budgets, we use breakers that trip on patterns:

### Tool spam

A tool called >10 times per minute by the same actor
without progress trips the breaker. The breaker:

- Disables the tool for that actor for 60s
- Logs to audit
- Surfaces to user as "this app seems stuck"

### Inference loops

The router tracks consecutive identical or near-identical
requests. If 5 in a row, breaker trips: refuse with
`internal.bug` and tell the agent loop to stop.

### Provider failures

If a remote provider returns 5xx repeatedly, the router
marks it Degraded, then Unavailable. Cost-shifts onto
local until cool-down expires.

### Cost anomalies

If the user's burn rate exceeds a configurable threshold
(default: 3× rolling average for the period), the user is
notified. The system does not auto-shut-off — that would
be more disruptive than the cost — but it makes the
anomaly visible.

## Diminishing returns detection

A cycle that doesn't move the planner forward is wasted.
Heuristics:

- Same tool called with similar args repeatedly
- Plan content unchanged across turns
- No new entities, no new facts retrieved
- Self-referential reasoning ("let me think about this
  again") without new evidence

The agent loop scores each cycle for "progress" and stops
when the rolling average drops below threshold.

## Caching

Caching is the cheapest cost control. Layers we use:

- **KV-cache prefix reuse**: by far the biggest savings.
  See `CONTEXT-ENGINEERING.md`.
- **Tool result memoization**: idempotent tools cache
  results by argument hash for short windows.
- **Embedding cache**: re-embedding the same query is
  free.
- **Memory recall cache**: identical recall queries hit
  a per-session cache before going to the database.

Cache invalidation is documented per layer; we never let
caches lie.

## Routing decisions

The inference router's job (see `INFERENCE-ROUTER.md`)
includes cost. Patterns:

- **Local-first**: same-tier local model preferred over
  remote
- **Quality vs cost**: a "Standard" privacy request with
  Conversational latency may use a cheaper remote model
  if the local one is busy
- **Burst smoothing**: short-burst remote calls allowed
  even on tight budgets; sustained remote calls are
  rate-limited

The router records its decisions; cost reports show how
much went to which path.

## User-facing cost UX

- Settings show current period consumption with progress
  bars
- Voice intent: "how much have I used this week?" reads
  the budget aloud
- A pre-emptive warning at 80% of plan
- A hard-stop at 100% with the option to opt into overage

Avoid:

- Surprise charges
- Hidden remote-only paths
- "Free" tiers that quietly degrade quality

## Per-feature cost notes

- **Voice**: each voice exchange is short tokens but
  high real-time cost. Hybrid voice (remote ASR/TTS) is
  faster but uses more remote tokens; user opts in.
- **Memory consolidation**: scheduled overnight on AC
  power; not on metered remote budget unless the user
  opts in.
- **Background reasoning**: only on AC + idle; budget set
  to "Whenever".
- **Subagents**: explicit budget per spawn; bounded; see
  `MULTI-AGENT-POLICY.md`.

## Anti-patterns

- **No budgets at all** — agents loop forever.
- **Budgets hidden from the user** — surprise bill
  episodes.
- **Auto-overage** — silently spending past plan.
- **One global budget** — one runaway feature kills the
  rest.
- **Penny-pinching that breaks the experience** —
  refusing reasonable calls because of an arbitrary cap.

## Configuration

```toml
[cost]
default_loop_budget = 25
wrap_up_hint_at = 0.8
hard_stop_at = 1.0

[cost.diminishing_returns]
window_cycles = 5
progress_floor = 0.2

[cost.circuits]
tool_spam_threshold_per_min = 10
inference_loop_threshold = 5

[cost.budgets]
default_tokens_per_period = 1000000
energy_low_battery_pct = 15
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Budget exhausted mid-stream      | let stream finish; warn user   |
| Circuit breaker false positive   | manual reset via CLI or        |
|                                  | settings                       |
| Loop budget too low for task     | user can raise per-call;       |
|                                  | default raises emit a hint     |
| Hidden cost (e.g., subagent      | audit log catches; user can    |
| spawned by tool)                 | review                         |

## References

- `00-foundations/PRINCIPLES.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/LOOP-BUDGET.md`
- `03-runtime/CAPABILITY-GATE.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
- `11-agentic-engineering/MULTI-AGENT-POLICY.md`
- `11-agentic-engineering/EVALUATION.md`
