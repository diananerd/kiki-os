---
id: context-engineering
title: Context Engineering
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - agent-loop
  - harness-patterns
last_updated: 2026-04-29
depended_on_by:
  - compaction
  - harness-patterns
  - working-memory
---
# Context Engineering

## Purpose

Describe the patterns Kiki uses to keep the model's
working context useful across long sessions: cache
discipline, sticky latches, prefix preservation,
compaction tiers, just-in-time injection. These are the
techniques that make the difference between a fast,
coherent agent and a slow, drifting one.

## The core constraints

- The model has a finite context window.
- Large contexts cost more inference time and can degrade
  quality (the "lost in the middle" effect remains real,
  despite progress).
- Inference providers (and our own llama.cpp) cache
  prefix tokens; cache hits are fast, cache misses are
  not.
- Cache is invalidated by *any* change to a prefix; one
  edit early in the conversation invalidates everything
  after.

These constraints drive the patterns below.

## Cache discipline

### Append-only is fast

Adding a new turn at the end of the conversation hits the
cache. The provider (or our local engine) reuses the KV
cache for everything before the new tokens.

### Editing in the middle is expensive

If you edit any token before the tail, the cache from
that point onward is invalidated. Subsequent inferences
re-compute KV for the entire suffix.

### Avoid edits when possible

Build the harness to *append* rather than *rewrite*. A
turn that needs correction is best handled with a new
turn rather than rewriting an old one.

### When you must edit, edit at boundaries

If a compaction step rewrites the middle, do it at well-
defined boundaries (turn-aligned, section-aligned). Never
edit a single token; if you must change a fact, replace
the whole section.

### Cache-edit pinning

Kiki tracks which sections have been edited so that the
next compaction does not redundantly recompute. The
runtime maintains a "stable prefix length" pointer; below
that, no edits are allowed by the harness.

## Sticky latches

A sticky latch is a small piece of context the model must
see on every turn, regardless of compaction:

- The current task ("you are helping the user plan a
  trip to Lisbon")
- The user's identity facts (name, time zone, default
  language)
- Active deadlines or constraints ("do this by Friday")
- The session's safety mode (DND, child mode, etc.)

Latches live in a dedicated section near the top of the
prompt. When compaction happens, latches are preserved.
When they change, only the latch section is rewritten;
the rest of the cache is preserved.

### Anti-patterns

- Storing too much in latches (it stops being "sticky"
  and starts being a wall of text)
- Using latches for ephemeral data (e.g., the latest
  search result)
- Re-stamping latches every turn even when unchanged —
  busts the cache

## Prefix preservation

The system prompt + tool descriptions + sticky latches
form a stable prefix. The agent loop:

- Constructs this prefix once per session
- Updates only when truly needed
- Hashes the prefix and uses the hash as the cache key

If the harness produces a new system prompt for any
reason, expect a cold start. We avoid changing the
system prompt mid-session.

## Just-in-time injection

Some context is best added at the moment of use:

- The current timestamp (changes constantly)
- Fresh search results
- The user's just-spoken question
- Tool output

These are added to the latest turn, not into stable
prefix. They invalidate cache only for the latest turn,
not the whole context.

## 5-tier compaction

Kiki's runtime keeps context within budget through a
five-tier compaction strategy:

```
Tier 0   System prompt + tool descriptions + sticky latches
Tier 1   Recent N turns, full fidelity
Tier 2   Older turns, full fidelity (until budget pressure)
Tier 3   Summarized middle: turn-by-turn summaries replace
         the full text
Tier 4   Archived past: a single summary of everything
         compacted out
```

Triggers:

- 70% capacity → start summarizing oldest tier-2 turns
  into tier-3
- 85% capacity → fold tier-3 into tier-4
- 95% capacity → emergency compaction; halve tier-1

The summarizer is a small, fast model; it preserves
entities, decisions, and unresolved questions. It drops
back-and-forth verbiage.

## What to summarize, what to keep verbatim

Keep verbatim:

- Tool call/result pairs that the user might want to see
- Code the user is working on
- Verbatim quotes the user requested
- Any artifact the user explicitly asked to "remember"

Summarize:

- Conversational verbosity
- Reasoning chains the model produced (the conclusions
  matter; the path usually does not)
- Failed attempts (their lessons matter; the keystrokes
  do not)

## Retrieval as the alternative to long context

Rather than carrying everything in context, retrieve what
is needed when needed:

- Episodic recall (vector search over past sessions) for
  "what did we decide last week?"
- Semantic graph traversal for entity relationships
- Procedural recall for how-to recipes
- Document grounding for files the user references

The retrieval system is part of the memory daemon; the
harness asks for relevant chunks just-in-time. See
`04-memory/`.

The trade is between:

- **Long context**: high recall, expensive, drift risk
- **Retrieval**: targeted, cheap, miss risk

Kiki blends both. The current task and the latest turns
are in context; everything older is retrieved on demand.

## Token budgets

Per-call budgets are set in the inference router. The
harness keeps within them by:

- Compacting before sending
- Truncating tool results that exceed a per-tool cap
- Refusing to send a request that would exceed the
  model's context budget — surface to user instead

## Tool result handling

Tool results often dominate context size. Patterns:

- **Tail truncation**: keep the last N lines of a long
  command output, drop the middle, mark with `...`
- **Structured summary**: convert a 200-line file listing
  into "73 files, 4 dirs; here are the most relevant by
  size and name"
- **Reference + retrieval**: store the full result in
  memory, give the planner a handle ("results stored as
  X; query if needed")
- **Abbreviation by convention**: paths shortened, large
  binary content elided as `<binary, sha256:...>`

Tool wrappers in the SDK encourage these patterns by
default.

## Avoiding context drift

Drift is when the model loses track of the current task
because old context still steers it. Defenses:

- Sticky latches re-stating the task
- Compaction that explicitly summarizes "current task:
  ..."
- Explicit task boundaries: when the user changes topic,
  start a new session or fork

The agent loop emits a `task_change` signal when the user
clearly switches topic; the harness compacts and refreshes
the latch.

## Just-in-time tool exposure

Not all tools need to be in context all the time.
Patterns:

- **Always-on tools**: 5-15 core tools the planner often
  uses. Worth the prompt cost.
- **Skill-scoped tools**: a skill activated for a task
  brings additional tools into context for the duration.
- **On-demand tools**: rarely-used tools listed in a
  meta-tool; the planner queries them when relevant.

Exposing 80 tools all the time degrades planning quality.
Skills are the natural unit for "more tools when needed".

## Anti-patterns

- **The growing system prompt**: every release adds a few
  lines until the system prompt is 4k tokens.
- **Loud tool results**: tools that dump pages of output
  the planner can't act on.
- **Compaction that loses critical facts**: aggressive
  summarizers that drop the constraints the user
  specified.
- **Unbounded retrieval**: vector searches that return 50
  chunks and shove them all in.
- **Cache thrashing**: edits to the system prompt mid-
  session, rewriting prior turns, etc.

## Measuring

The runtime tracks per-session:

- Tokens in / tokens out
- Cache hit rate (prefix hits / total)
- Compaction events
- Time to first token
- Quality regression flags (model failed to follow
  format, looped, etc.)

These feed into evaluation (`EVALUATION.md`). A regression
in cache hit rate is often the canary for a context
engineering bug.

## References

- `00-foundations/PRINCIPLES.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/LOOP-BUDGET.md`
- `03-runtime/INFERENCE-ENGINE.md`
- `04-memory/EPISODIC-MEMORY.md`
- `04-memory/SEMANTIC-GRAPH.md`
- `11-agentic-engineering/HARNESS-PATTERNS.md`
- `11-agentic-engineering/EVALUATION.md`
