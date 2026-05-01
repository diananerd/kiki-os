---
id: 0040-arbiter-classifier-two-stage
title: Two-Stage Arbiter Classifier
type: ADR
status: draft
version: 0.0.0
depends_on: [0038-camel-trifecta-isolation]
last_updated: 2026-04-29
depended_on_by:
  - 0041-coordinator-worker-isolation
---
# ADR-0040: Two-Stage Arbiter Classifier

## Status

`accepted`

## Context

Even with CaMeL planner/parser separation and capability gating, some tool calls warrant a second look — especially calls that touch the lethal trifecta (private data + untrusted input + external effects). A classifier model can intercept and decide, but a single large classifier on every tool call is expensive and adds latency. Single-stage small classifiers are fast but miss subtle cases.

## Decision

Implement a **two-stage arbiter classifier** following Anthropic's `yoloClassifier` pattern (input minimization + diminishing returns). **Stage 1**: small fast model (Llama Prompt Guard 2 86M or Granite Guardian 5B) sees a minimized view of the call (tool name, typed args, redacted context). Output: Allow / Deny / Uncertain / Sanitize. **Stage 2**: only on Uncertain — escalates to a larger model with broader context for a more deliberate decision. Both stages emit a structured rationale for the audit log.

## Consequences

### Positive

- Average call hits only stage 1; cost stays low.
- Hard cases get the bigger model's attention without paying for it on every call.
- Audit trail captures both stages for forensics.
- Decoupled from the planner: arbiter sees the *call*, not the planner's reasoning, so injection that hijacks the planner still has to pass the arbiter on the way out.

### Negative

- Two prompts to maintain (curated under `prompts/arbiter/`).
- Stage 1 false negatives can let calls through; we pair with the audit log and post-hoc detection.
- Stage 2 escalation rate must be monitored; runaway escalations would erode the cost win.

## Alternatives considered

- **Single small classifier always**: cheaper but blind to subtle cases.
- **Single large classifier always**: better calibrated but expensive on every call.
- **Rule-based classifier**: brittle; can't keep up with novel attack shapes.
- **No arbiter, gate-only**: gate enforces grants but doesn't reason about combinations of trust and intent.

## References

- `03-runtime/ARBITER-CLASSIFIER.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
- `11-agentic-engineering/CURATED-PROMPTS.md`
- `10-security/CAMEL-PATTERN.md`
