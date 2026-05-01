---
id: deterministic-vs-agentic
title: Deterministic vs Agentic
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - vision
  - principles
depended_on_by:
  - design-philosophy
last_updated: 2026-04-30
---
# Deterministic vs Agentic

## Problem

LLMs are flexible but slow, expensive, and capable of hallucination. Deterministic code is fast, cheap, and predictable but inflexible. An agentic OS that uses LLMs everywhere becomes unreliable. An agentic OS that uses LLMs nowhere is just a Linux distribution. The line between deterministic and agentic must be drawn explicitly per component.

## Constraints

- Hallucination must never be load-bearing for safety, security, or correctness.
- Determinism must never be load-bearing for tasks that require flexibility, creativity, or open-ended interpretation.
- The line must be testable: any component can be classified.
- Escape hatches in the agentic path must be deterministic (so the user is never trapped if an LLM fails).

## Decision

The line is drawn by these rules:

### Deterministic by default

Anything that satisfies any of these is deterministic:

- It is a security or safety enforcement point.
- It is a contract boundary (protocol, ABI, capability check).
- It manages persistent state with correctness requirements.
- It is on the critical path with strict latency requirements.
- It can be expressed as a fixed algorithm without significant loss of utility.

### Agentic where it adds irreplaceable value

Anything that satisfies any of these is agentic:

- It interprets natural-language user intent.
- It plans across an open-ended action space.
- It composes UI from semantic intent.
- It summarizes, classifies, or generates content.
- It would be brittle as a fixed algorithm because the input space is unbounded.

### Bounded agentic for risky cases

When agentic logic touches a security or safety surface, the agentic component is bounded:

- A separate, smaller model performs the gating decision (not the main agent).
- The gating model receives only the minimum input needed (input minimization).
- The decision has a deterministic fallback (e.g., human prompt) on failure or repeated denial.
- Time and token budgets are enforced by deterministic outer wrappers.

## The line, by component

| Component | Mode | Notes |
|---|---|---|
| Boot, kernel, image deployment, rollback | Deterministic | Cannot be agentic; correctness is mandatory. |
| Sandbox primitives (Landlock, seccomp, namespaces, cgroups) | Deterministic | Kernel enforcement. |
| OTA updates (apply, verify, rollback) | Deterministic | Crypto and atomic operations. |
| OTA timing recommendation | Agentic (advisory) | Agent suggests; deterministic policy applies. |
| Capability gate static rules | Deterministic | Profile match, hardcoded restrictions. |
| Capability gate arbiter classifier | Bounded agentic | Separate model, input-minimized, deterministic fallback. |
| Inference router routing decision | Deterministic | Fixed algorithm based on classified inputs. |
| Inference engine | Agentic by definition | The LLM. |
| Memory store/retrieve/search | Deterministic | Algorithmic. |
| Memory compaction tiers L0–L2 | Deterministic | Mechanical. |
| Memory compaction tiers L3–L4 | Agentic (background) | Summarization. |
| Memory embeddings | Agentic (one-shot per item) | Embedding model. |
| Tool registry lookup, dispatch | Deterministic | Tables. |
| Agent loop control flow | Deterministic | Loop, budget, hooks. |
| Agent reasoning within loop | Agentic | The LLM's job. |
| Canvas reconciliation, layout, animation | Deterministic | Diff and apply. |
| Canvas content composition | Agentic | Agent decides what to show. |
| Voice STT, TTS | Agentic (output well-defined) | Models with structured output. |
| Voice wake word | Bounded agentic | Tiny model, binary output. |
| Slash commands | Deterministic | Parsed and dispatched. |
| Workspace switching, hibernation | Deterministic | Mechanical. |
| Audit log append, hash chain | Deterministic | Crypto. |
| Registry semantic search, recommendations | Agentic | Open-ended. |
| Identity file write | Deterministic (consent flow) | Non-bypassable. |
| Drift detection signals | Deterministic (rules) | Threshold-based. |

## Patterns we apply consistently

### Agentic wrapped in deterministic

Every agentic component has a deterministic wrapper that:

- Validates input against a schema.
- Enforces a timeout.
- Provides a deterministic fallback (even if lossy).
- Logs input and output to the audit journal.

Example: `memoryd.compact()` invokes an LLM with a 10-second timeout. On failure, falls back to deterministic Snip. On repeated failure, alerts and aborts.

### Bounded LLM (separate model, input minimized)

When an LLM takes a decision affecting safety, the deciding LLM is **not** the main agent:

- Arbiter classifier is a small dedicated model (86M–3B parameters).
- It receives only `(user_prompt, tool_call_descriptor)`, never the agent's reasoning prose.
- This prevents prompt injection in the agent's prose from reaching the gate.

### Deterministic escape hatches

Wherever the agent could become unreliable or stuck, the user has a deterministic escape:

- Slash commands (`/back`, `/forward`, `/restart-agent`, `/workspace`, `/kill`, `/share`).
- Task manager UI with explicit buttons.
- Direct system reboot.

If the LLM stack fails entirely, the OS remains usable in a degraded mode.

### Deterministic for enforcement, agentic for suggestion

```
"Apply this update?"               agentic recommends, deterministic policy enforces
"Allow this tool call?"            arbiter suggests, gate enforces deny-first
"Hibernate this workspace?"        agent hint, timer policy acts
```

Never the inverse. Agentic enforcement loses guarantees.

### Every agentic decision logs input and output

The audit journal records:

- Model used and version.
- Exact input.
- Output of the model.
- Decision of the deterministic wrapper.

Replayable. Auditable. Investigable.

### Versioned curated prompts as code

System prompts for arbiter, compaction, search, and other curated agentic components are versioned as artifacts. A change to a prompt is a release like a code change: tested, signed, documented.

### Rate limits and circuit breakers

Each agentic loop has bounded budgets:

- Three consecutive arbiter denials → human prompt fallback.
- Three consecutive auto-compact failures → abort, alert.
- N tokens per minute per app → rate limit.
- N tool failures in M minutes → pause agent, surface error.

Without these, an agentic loop can consume budget indefinitely.

## Anti-patterns explicitly rejected

- An LLM that interprets a sandbox configuration in runtime. Sandbox configuration is static.
- An LLM that decides whether to verify a signature. Crypto is always verified.
- An LLM that adjusts cgroup limits dynamically. Profiles declare limits.
- An LLM as event router for the bus. The bus is deterministic.
- An LLM that selects a workspace destination for a new block. Routing is deterministic; the agent composes explicitly.
- An LLM patching code at runtime. The OS does not eval or execute generated code in its daemons.
- An LLM negotiating updates with a backend. The server proposes, the client verifies signature, applies or rejects.

## Consequences

- About 6–8 curated prompts in the system, each versioned and signed.
- The rest of the system is deterministic Rust + systemd + apt-equivalent + protocol code.
- The system feels conversational when LLMs are working well, and feels solid when they are not.
- Adding a new agentic decision point requires: a deterministic wrapper, a fallback, a budget, an audit hook. Without all four, it is rejected.

## The simple rule

> **If the OS breaks when the LLM hallucinates, the design is wrong.**
> **If the OS feels rigid when the LLM is working well, the design is wrong.**

These two failures are diagnostic. Either symptom indicates the line was drawn wrong somewhere.

## References

- `00-foundations/PRINCIPLES.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `04-memory/COMPACTION.md`
- `11-agentic-engineering/CURATED-PROMPTS.md`
