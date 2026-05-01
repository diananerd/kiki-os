---
id: harness-patterns
title: Harness Patterns
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - agent-loop
  - context-engineering
  - prompt-injection-defense
last_updated: 2026-04-29
depended_on_by:
  - context-engineering
  - curated-prompts
  - multi-agent-policy
---
# Harness Patterns

## Purpose

Distill the patterns that production agentic systems
(Claude Code, Cursor, Aider, Cline, Devin, Codex, etc.)
have converged on into a vocabulary Kiki uses across
agentd, the SDK, and skill authoring. The goal is not to
catalogue every harness ever built — it is to name the
patterns we use, so readers and contributors can recognize
them.

This is a guide, not a spec. Specifics of Kiki's runtime
live in `03-runtime/`.

## The seven-component decomposition

A "harness" is the wrapper around a model that turns a
single inference call into useful agentic behavior. After
auditing many open and closed systems we have found seven
recurring components. A harness is some combination of
these:

```
1. Prompt assembly       gather state, format messages
2. Tool surface          which tools, schemas, descriptions
3. Loop control          when to keep looping, when to stop
4. Memory & retrieval    how to bring relevant facts back
5. Compaction            shrinking context as it grows
6. Subagent dispatch     parallel or hierarchical agents
7. Safety arbiter        gating actions before they happen
```

A trivial chat harness does (1) + (2) + (3). A full agent
does all seven. Kiki's agent loop (`AGENT-LOOP.md`) is the
canonical instance.

### 1. Prompt assembly

The model only sees what we put in front of it. Pieces:

- **System prompt**: stable across the session; identity,
  tools available, safety constraints.
- **Tool descriptions**: usually appended to the system
  prompt; concise + accurate matters more than clever.
- **Context window**: the working memory; user messages,
  assistant turns, tool results.
- **Sticky latches**: facts that should remain visible
  across compactions (e.g., the active task, the user's
  current location). See `CONTEXT-ENGINEERING.md`.
- **Just-in-time injections**: timestamps, environment
  signals, fresh retrievals — added to the latest turn.

Anti-patterns:

- A 5000-token system prompt that re-explains everything
  the model already knows from training
- Tool descriptions that contradict the tool's actual
  behavior
- Re-injecting the same facts every turn (cache busting)

### 2. Tool surface

Tools are the model's hands. The harness decides:

- Which tools to expose (more is *not* better)
- The schema and description of each
- The format of tool calls (JSON, XML, function-call)
- The format of tool results (compact > verbose)

Patterns we use:

- **Risk classes**: tools labeled `safe`, `gated`,
  `elevated` so the planner can reason about consequence
  before calling.
- **Idempotent vs effecting**: idempotent tools (read,
  list) versus tools with side effects; the planner can
  retry the former on parse failures.
- **Composition over proliferation**: a few small tools
  the planner can compose, not 80 special-case tools.

### 3. Loop control

When to call the model again. When to stop.

- **Step budget**: max cycles per task (Kiki: 25 with
  `LOOP-BUDGET.md`)
- **Tool budget**: max tools per cycle
- **Diminishing returns detection**: if N consecutive
  cycles produce no measurable progress, stop and
  surface.
- **Wrap-up hint**: at 80% budget, inject "you are nearing
  step budget; produce a final answer or hand off"
- **Idle conditions**: voice silence, user inactivity,
  battery low

The loop is the heart of a harness. Most failure modes are
loop-control bugs (forever-looping, premature stops,
unbalanced step counts).

### 4. Memory & retrieval

Bringing back relevant facts:

- **Episodic recall**: vector search over past turns
- **Semantic graph traversal**: structured queries over
  named-entity facts
- **Procedural recall**: how-to recipes for common tasks
- **Identity facts**: short, always-loaded; the user's
  name, time zone, defaults
- **Document grounding**: pulling specific files referenced

The harness must decide *what to retrieve* and *when*. Too
eager → bloated context, slower inference, distracted
model. Too lazy → hallucination.

### 5. Compaction

Conversation grows; context budget shrinks.

- **5-tier compaction** (per Kiki's runtime): keep the
  system prompt, sticky latches, recent turns, summarized
  middle, archived past
- **Cache-edit pinning**: edits to compacted blocks are
  tracked so we don't re-cache from scratch
- **Triggers**: at 70% capacity, compact eagerly; never
  wait for hard limit

See `CONTEXT-ENGINEERING.md` for details.

### 6. Subagent dispatch

When a task is too big for one model call:

- **Fork**: clone the conversation, run a sub-task, return
  result. The subagent shares context but its turns don't
  pollute the parent.
- **Teammate**: a long-lived sibling agent with its own
  context.
- **Worktree**: an isolated workspace (file-tree, env)
  for a sub-task that may make changes.
- **Coordinator/Worker isolation**: planner runs in a
  context with no privileged tools; workers receive narrow
  capabilities for their sub-tasks. Defends against the
  lethal trifecta. See `MULTI-AGENT-POLICY.md`.
- **Sidechain JSONL**: subagent transcripts are persisted
  separately for auditing without bloating the parent.

When *not* to spawn: trivial sub-tasks. Subagent overhead
(extra inference, context duplication) often outweighs
benefit. Research from the Anthropic Cookbook and others
finds the breakeven for parallel agents starts somewhere
around 3 independent sub-tasks.

### 7. Safety arbiter

A small, fast classifier that runs before any "trifecta-
touching" action — anything that combines untrusted input,
private data, and external effects. The arbiter decides:

- Allow (most cases; agent proceeds)
- Deny (clearly malicious / clearly out-of-scope)
- Defer to human (uncertain)
- Sanitize (transform input or constrain action)

Kiki uses a two-stage arbiter (see `ARBITER-CLASSIFIER.md`):
first a tiny model on minimized input; if uncertain,
escalate to a larger model. Diminishing returns: if the
small classifier is sure, don't pay for the big one.

## Concrete harness shapes

### "Chat with tools" (Claude Code-style)

(1) + (2) + (3) + (5) + light (4). No subagents. Used by
the basic agent surface.

### "Code agent with planning" (Aider/Cursor-style)

(1) + (2) + (3) + (4) + (5) + planning hops. Sometimes
(6) for parallel file searches.

### "Long-running autonomous agent" (Devin-style)

All seven. Heavy use of (5), (6), (7). Persistent
workspaces. This is closest to what Kiki's full agent
loop runs.

### "Voice agent" (Kiki's voice surface)

Reduced (1), no (5) (each voice exchange is short),
heavy (4) for grounding, light (6) for ASR / TTS / LLM
parallelism. Real-time loop control instead of cycle-based.

## Trade-offs

- More components ≠ better. Each adds latency and surface
  area. Match the harness shape to the task class.
- The model's strengths constrain the harness. A model
  bad at tool calls needs more wrappering; a strong
  tool-caller needs less.
- Compaction strategies that work great at 8k context can
  break at 200k.
- Subagent overhead is real; do not spawn unless the
  sub-task is independent enough to absorb the cost.

## Patterns to avoid

- **The kitchen-sink harness**: 50 tools, 12 retrieval
  layers, 8-tier compaction. The model gets confused, the
  user can't predict behavior.
- **Heroic single-prompt agents**: shoving everything into
  one giant system prompt with no loop. Breaks the
  moment a task needs multiple steps.
- **Hidden state**: the harness mutates state the model
  cannot see. The model then makes calls that contradict
  the state.
- **Implicit tools**: the model is told a tool exists but
  the schema isn't surfaced. Hallucinated arguments
  follow.
- **Unbounded retrieval**: pulling in everything that
  matches a query. Context blow-up.

## How Kiki uses these patterns

- Agent loop: full seven-component harness; documented at
  `03-runtime/AGENT-LOOP.md`.
- Skills (Claude Code-style): a smaller harness, one
  curated tool set per skill, fixed prompt template.
- Subagents: spawned via `SUBAGENTS.md` with explicit
  pattern (Fork / Teammate / Worktree).
- Voice loop: a real-time harness with shorter loop
  control budget and aggressive arbiter on the
  classifier.

## References

- `00-foundations/PRINCIPLES.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/LOOP-BUDGET.md`
- `03-runtime/SUBAGENTS.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
- `11-agentic-engineering/MULTI-AGENT-POLICY.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
- `11-agentic-engineering/COST-CONTROL.md`
