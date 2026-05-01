---
id: compaction
title: Compaction
type: SPEC
status: draft
version: 0.0.0
implements: [compaction]
depends_on:
  - memory-architecture
  - working-memory
  - context-engineering
depended_on_by: []
last_updated: 2026-04-30
---
# Compaction

## Purpose

Specify how the agent loop keeps the working context within budget without losing what matters: the five-tier strategy, cache-edit pinning, the L3 background notes, and triggers.

## The five tiers

```
T0  System prompt + tool descriptions + sticky latches  (always preserved)
T1  Recent N turns, full fidelity                         (live working set)
T2  Older turns, full fidelity                            (until pressure)
T3  Summarized middle: turn-by-turn summaries              (budget pressure)
T4  Archived past: a single overall summary                (heavy pressure)
```

T0 is immutable mid-session. T1 and T2 are evictable; T3 and T4 are write-once-then-condense.

## Triggers

```
70% of context budget   start summarizing T2 → T3
85%                      fold T3 into T4 (collapse middle)
95%                      emergency: halve T1 budget
```

The agent loop watches token count after each cycle and triggers compaction off-thread when over a threshold.

## Cache-edit pinning

KV-cache reuse depends on prefix stability. Compaction edits the middle, which would invalidate cache from the edit point onward — costly. We track:

- A **stable prefix length** pointer; T0 + identity are always before it
- A **cache pin** per turn telling the engine which prefix is still valid

When compaction rewrites a tier, we set the pin to the start of the rewritten region; the engine recomputes only that and forward, not the whole context.

## L3 background notes

When summarizing into T3, we capture not just the conversation gist but also:

- Decisions made
- Unresolved questions
- Promises ("I'll send X tomorrow")
- Entities introduced

These are stored as a structured block alongside the prose summary so the agent can later retrieve specifics.

## Summarizer

The summarizer is a small fast model (Llama 3.3 8B Q4 by default). The prompt (`prompts/compaction/summarizer.txt`) explicitly preserves entities, decisions, and verbatim quotes the user requested.

The summarizer runs in inferenced via the router; cost is included in the user's budget.

## Algorithm sketch

```
fn compact(ctx: &mut WorkingMemory, target_pct: f32):
    if ctx.usage_pct() < 0.7: return

    let oldest_t2 = ctx.oldest_t2_window(N);
    let summary = summarizer.run(oldest_t2);
    ctx.replace(oldest_t2, T3Block::from(summary));
    ctx.bump_cache_pin(after = oldest_t2.start);

    if ctx.usage_pct() < 0.85: return

    let all_t3 = ctx.t3_blocks();
    let archive = summarizer.run_archive(all_t3);
    ctx.replace(all_t3, T4Block::from(archive));
    ctx.bump_cache_pin(after = all_t3.first.start);

    if ctx.usage_pct() < 0.95: return

    // emergency
    ctx.t1_budget /= 2;
```

## What is never compacted

- T0 (system prompt, tool descriptions, sticky latches)
- The identity section in working memory
- Verbatim quotes the user explicitly said to remember
- Code blocks and tool results the user has marked
- Structured artifacts the agent is currently editing

These survive any compaction.

## What is preferentially compacted

- Long assistant reasoning chains where the conclusion is captured
- Failed attempts ("user asked for X, agent tried Y, was wrong, tried Z, succeeded" → "succeeded with Z")
- Conversational filler

## Capability

Compaction is internal to memoryd and the agent loop; no per-call capability check beyond `agent.memory.write.working`.

## User control

```
kiki-memory working compact         # trigger compaction now
kiki-memory working pin <turn-id>   # never compact this turn
kiki-memory working pins            # list pinned turns
```

## Quality regressions

Compaction is a known source of subtle quality loss. We measure:

- Reference-recall after compaction (does the agent still recall key facts?)
- Length of summary vs original (extreme ratios warn)
- Entity preservation (named entities should appear in summary)

These feed evaluation (`EVALUATION.md`); regressions block summarizer-prompt changes.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Summarizer call fails            | retry once; on continued fail, |
|                                  | drop oldest tier-2 raw turns   |
|                                  | (keep their refs)              |
| Cache invalidation worse than    | revert pin; recompute everything|
| expected                         |                                |
| User-pinned turn forces over-    | refuse to add new turns;       |
| budget                           | surface "context full"         |

## Performance

- Compaction call: <2s typical (depends on summarizer)
- Off the agent's hot path
- Cache invalidation cost: bounded by pin discipline

## Acceptance criteria

- [ ] Triggers fire at the configured thresholds
- [ ] Compaction preserves identity and pinned turns
- [ ] Cache pin is updated correctly
- [ ] L3 background notes capture decisions and promises
- [ ] CLI works for inspection and manual triggering

## References

- `03-runtime/AGENT-LOOP.md`
- `04-memory/WORKING-MEMORY.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
- `11-agentic-engineering/CURATED-PROMPTS.md`
- `11-agentic-engineering/EVALUATION.md`
