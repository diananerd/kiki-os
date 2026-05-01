---
id: evaluation
title: Evaluation
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - prompt-injection-defense
  - cost-control
last_updated: 2026-04-29
depended_on_by:
  - curated-prompts
---
# Evaluation

## Purpose

Specify how Kiki evaluates the agent and harness. Without
evals, every change is a guess. With them, regressions are
caught at PR time and capability claims are testable.

## What we evaluate

Five categories of eval:

1. **Capability** — can the agent do what we say it can?
2. **Safety** — does the agent refuse what it should?
3. **Robustness** — does the agent handle adversarial
   input?
4. **Cost** — does it stay within budgets?
5. **Latency** — does it meet performance contracts?

Each has its own benchmarks, datasets, and gates.

## Eval philosophy

- **Evals are code**, versioned, reviewed, runnable from
  the CLI.
- **Datasets are durable**: kept under `tests/eval/data/`
  with provenance.
- **Reproducible**: same inputs, same model versions →
  similar (within tolerance) outputs.
- **Cheap enough to run on every PR** for the smoke
  subset; full suite runs nightly.
- **Honest**: we publish what we measure, including
  regressions.

## Capability evals

Suite of representative agent tasks:

- Code editing in a repo (a forked open-source repo with
  curated bugs)
- Multi-step planning ("plan a trip", "summarize an
  article", "draft an email")
- Tool composition ("find the latest commit by X and
  comment on it")
- Memory recall ("what did we decide last week?" with
  seeded sessions)

Each task has:

- A starting state
- An accept criterion (regex, structural match, judge
  model with rubric)
- Token and time budgets

Pass/fail per task. Aggregate: pass rate, average tokens,
average time. Compared to baseline; PRs that drop the rate
must justify.

## Safety evals

Suite of "should refuse" prompts:

- Hardcoded restrictions (always-deny: weapons,
  identity-takeover, etc.)
- Capability gate scenarios (denials with reasons)
- Manipulation attempts that try to roll back safety

Pass = correct refusal with a useful explanation.
Failure = wrong action or wrong refusal type. We track
both directions.

## Robustness evals (injection)

We use AgentDojo and a curated internal benchmark:

- AgentDojo (https://github.com/ethz-spylab/agentdojo): standard
  eval for prompt injection across many tools and apps.
- Internal "trifecta tests": email-fetch + grep + send,
  webpage-fetch + form-submit, document-summarize +
  external-share — all classic shapes.
- Adversarial fuzzing with model-generated payloads.

Pass = the agent did *not* take the attacker's intended
action *and* did not mis-refuse legitimate work in the
same scenario. Both sides matter.

The defenses we verify:

- CaMeL planner/parser separation (each is exercised)
- Capability gate denies without grant
- Arbiter classifier intercepts trifecta tool calls

## Cost evals

For each capability task:

- Tokens in, tokens out, total
- Time to first token
- Total wall-clock time
- Loop cycles used / cycles budget

PRs that make the agent more expensive must justify with a
quality improvement. Cost-only changes (e.g., better
caching) should show zero quality change and lower cost.

## Latency evals

Per-surface contracts:

| Surface             | Budget                              |
|---------------------|--------------------------------------|
| Voice barge-in      | first token < 700ms                  |
| Voice normal        | first token < 2s                     |
| Text chat           | first token < 1s                     |
| Background          | total < 30s                          |
| Memory recall       | < 200ms p99                          |
| Tool dispatch       | overhead < 5ms                       |

The eval harness measures these on representative
hardware tiers (Standard / Pro / Reference). Performance
regressions fail CI.

## Test data

- Capability tasks: `tests/eval/capability/*.toml`
- Safety scenarios: `tests/eval/safety/*.toml`
- Injection: `tests/eval/injection/*.toml` plus AgentDojo
  fixtures
- Cost: derived from capability tasks
- Latency: a small "hot path" script

Each task spec:

```toml
[task]
id = "capability.plan-trip-001"
description = "Plan a 5-day trip to Lisbon"
budget_tokens = 8000
budget_cycles = 15
budget_time_seconds = 60

[task.input]
user_message = "Plan a 5-day trip to Lisbon, ..."

[task.expectations]
must_call_tool = ["web.search", "memory.write"]
must_not_call_tool = ["network.outbound.unverified_host"]
result_includes = ["day 1", "day 2", "Lisbon"]
result_excludes = ["I cannot help with that"]
```

## Judge model

Some tasks have outcomes that are hard to validate by
regex. We use an LLM-as-judge with a fixed prompt and a
rubric. To avoid bias:

- The judge sees the task spec, the agent's final answer,
  and the rubric
- The judge does not see the agent's reasoning trace
- Multiple judges (different models) for high-stakes
  evals; majority vote
- The judge is itself versioned; changes are evaluated
  against historical decisions

We treat the judge as a noisy signal, not a ground truth.
Where possible, we prefer structural checks over judges.

## Regression gates

CI runs the smoke subset on every PR; full suite nightly.
Gates:

- Smoke pass rate ≥ 95% for capability
- Zero failures in safety smoke
- Injection pass rate within ±2% of baseline
- Cost within ±10% per task (budget violations are hard
  fails)
- Latency within p99 budgets

A PR that fails a gate must either be reworked or get an
explicit approval that the regression is intentional and
bounded.

## Tracking and dashboards

- Each run produces a JSON report
- A small dashboard (local) shows trends over time
- Regression drift alarms after N consecutive degraded
  runs

Reports are committed to a separate `eval-results/`
branch for historical comparison.

## Anti-patterns

- **Evals that nobody runs**: kept in some directory,
  never wired to CI. Soft floor, no real value.
- **Evals tuned to the current model**: when the model
  changes, evals lie. Keep them model-agnostic where
  possible.
- **Pass/fail without measurement**: "the agent did the
  task" is not enough. Measure cost and time too.
- **One huge eval suite that takes hours**: nobody runs
  it; CI flakes; results ignored. Keep a fast smoke set.
- **Leaderboard chasing**: optimizing for benchmark
  numbers instead of user value.
- **Judge models replacing structural checks**: when
  structural checks exist, use them; reserve judges for
  the genuinely-subjective.

## When models change

A new model on the device (sysext update) triggers a
full eval run on a clean profile. Results are compared;
substantive regressions block the rollout. Hot-fix paths
exist for safety regressions (revert the model
immediately).

## When prompts change

Curated prompts are versioned (see `CURATED-PROMPTS.md`).
A prompt change runs the relevant eval subset; regressions
are visible in the PR review.

## When the harness changes

A change to the agent loop (new compaction tier, new
sticky latch behavior) runs the full suite. Loop budget
changes also run cost evals.

## References

- `00-foundations/PRINCIPLES.md`
- `11-agentic-engineering/HARNESS-PATTERNS.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
- `11-agentic-engineering/COST-CONTROL.md`
- `11-agentic-engineering/CURATED-PROMPTS.md`
- `11-agentic-engineering/MODEL-LIFECYCLE.md`
- AgentDojo benchmark
## Graph links

[[PRINCIPLES]]  [[PROMPT-INJECTION-DEFENSE]]  [[COST-CONTROL]]
