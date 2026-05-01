---
id: design-philosophy
title: Design Philosophy
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - paradigm
  - principles
  - deterministic-vs-agentic
depended_on_by: []
last_updated: 2026-04-29
---
# Design Philosophy

This document captures the heuristics, anti-patterns, and dos and don'ts that emerge from the paradigm, principles, and deterministic-vs-agentic line. It is the practical guide for engineers making technical decisions.

## Heuristics for accepting a proposal

A technical proposal is acceptable when:

1. It satisfies the paradigm test (single-purpose, opaque, image-based, signed, declarative).
2. It does not violate higher-priority principles to satisfy lower-priority ones.
3. It places agentic logic only where flexibility is irreplaceable, with bounded budgets and deterministic fallbacks.
4. It inherits from upstream rather than maintaining a fork.
5. It uses OCI artifacts for distribution.
6. It fits an existing chapter in the documentation. If a new chapter is needed, the proposal is structural and requires an RFC.

## Anti-patterns explicitly rejected

### Distribution

- A user-facing apt/dnf/pacman track parallel to OCI.
- App distribution outside signed OCI registries.
- Implicit trust on any untrusted artifact.
- Distribution of unsigned models or components.

### Sandboxing

- Custom sandbox preset templates that duplicate what the container runtime already provides.
- Bypassing the container runtime to run apps directly.
- Running apps as root in any context.
- Unsigned containers being launched.

### Sandboxing escape

- Treating a permission denial as feedback for the agent to retry through a different channel.
- Composing tool calls that together exceed any single capability.
- Cross-agent config writes without explicit user approval.

### Memory

- Identity files written without passing through the consent flow.
- Memory writes that bypass the capability gate.
- Cross-user memory reads without explicit grant.
- Sensory data persisted to disk.
- Compaction that erases the user's emotional content or stated disagreement.

### Inference

- Sensitive content routed to remote models.
- Inference requests that do not pass through the inference router.
- Apps holding raw provider credentials.
- Cost budget exceeded silently.

### Capability gate

- Capabilities granted by the agent's reasoning rather than the user's explicit consent.
- Capabilities defined by apps outside the canonical taxonomy.
- Hardcoded restrictions weakened by configuration.
- Audit log entries omitted or redacted.

### Tool ecosystem

- Tool catalog enumerated to the model in full (causes context bloat and hallucination).
- Tool descriptors that lack a JSON schema.
- Tools without typed `read_only`/`destructive`/`reversible` flags.
- Tool dispatchers that retry on capability denial automatically.

### Multi-agent

- Spawning subagents by default.
- Coordinator agents that execute tools directly.
- Subagent journals merged into the parent's working memory.
- Subagent capabilities exceeding their parent's.

### UI

- Window-management metaphors (alt-tab, taskbar, window switcher).
- Free-form drag-and-drop between apps.
- Clipboard as a first-class user concept.
- App launchers based on icon grids.
- Apps controlling layout decisions globally.

### Auditability

- Operations performed without an audit log entry.
- An audit log that is not hash-chained.
- Sensitive content embedded in the audit log (must be referenced, not copied).
- Audit log mutation without an audit log entry recording the mutation.

### Compositor

- A general-purpose Wayland compositor that the user can replace.
- Apps that control the compositor.
- Multiple windows per app as a first-class concept.

### Identity

- Identity files written outside the consent flow.
- Identity content trusted to override hardcoded restrictions.
- Identity files lacking version history.
- Identity-class proposals applied automatically without user approval.

## Dos

### Architecture

- Inherit from upstream. Contribute fixes upstream rather than forking.
- Use one tool when one tool fits. Use two when one tool fights against itself.
- Make the deterministic part the gate, the agentic part the suggestion.
- Provide a deterministic escape hatch for every agentic loop.

### Distribution

- Sign every artifact with cosign.
- Submit Merkle tree heads to a transparency log when the user opts in.
- Keep namespaces small and trusted. Per-namespace cosign keys are the trust unit.
- Resolve identity through the namespace registry. Don't hardcode URLs.

### Memory

- Default to per-user namespacing. Cross-user is the explicit case.
- Default to recall over precision in retrieval (top-k=20–30, then in-context filter).
- Compact in tiers, cheapest first.
- Preserve the user's emotional content and stated disagreement during compaction.

### Capability gate

- Deny first. Allow only via explicit grant.
- Use an arbiter classifier for ML-based gating, with input minimization.
- Log every decision in the audit journal.
- Provide circuit breakers for repeated denials.

### Performance

- Document performance contracts in every SPEC.
- Track cache hit rate as a first-class metric.
- Bound LLM tasks with both token budgets and loop budgets.
- Use the data plane (iceoryx2) for bulk transfers, not RPC.

### UI

- Keep the canvas reactive. Components mount/unmount with stable IDs.
- Animate transitions; avoid sudden visual changes.
- Provide alternatives for users who cannot perform a gesture.
- Preserve identity tokens in working memory at all costs.

### Voice

- Wake word, VAD, AEC: local always.
- STT/TTS: route by privacy level. Sensitive stays local.
- Voice prints: never exported, even by the user.
- Hardware kill switches: enforced at HAL, not above.

### Code

- Privileged code in Rust. C only at FFI boundaries when unavoidable.
- Errors as first-class values, not exceptions.
- Schema-validated boundaries.
- Tests cover failure modes, not just happy paths.

## Don'ts

### Architecture

- Don't add a feature that turns Kiki into a generalist Linux.
- Don't expose Linux internals (apt, services, units, files) to the user-facing surface.
- Don't add a parallel distribution track.
- Don't fork upstream packages.

### Trust

- Don't trust unsigned content.
- Don't accept content's claims about its own permissions.
- Don't let the agent's reasoning influence security decisions.
- Don't treat MCP as a trust boundary.

### Memory

- Don't conflate the six memory layers into one store.
- Don't write identity files outside the consent flow.
- Don't keep sensory data on disk.
- Don't do single-pass truncation under context pressure.

### Tools and apps

- Don't enumerate the full tool catalog to the model.
- Don't allow apps to enumerate other apps.
- Don't let apps communicate directly. Mediate through the agent.
- Don't allow apps to bypass the capability gate.

### Multi-agent

- Don't spawn subagents by default.
- Don't merge subagent state into the parent.
- Don't ignore the 15× token cost of multi-agent vs single-agent.

### UI

- Don't expose window-management concepts.
- Don't allow apps to capture global input.
- Don't let apps screenshot other surfaces.
- Don't expose drag-drop or clipboard as first-class.

## When to add an exception

Sometimes a strict don't has a rare legitimate exception. The process:

1. Document the exception case in the relevant SPEC's "Open questions".
2. Open an RFC if the exception is structural.
3. Get reviewer approval.
4. Implement with telemetry that lets us watch for drift.

The fact that an exception was made does not loosen the rule for the next case.

## Cultural rules

- State decisions clearly. Hedge only when uncertainty is real.
- Prefer "we decided X because Y" to "we considered many options".
- Prefer "this fails because Z" to "this might be a problem".
- Document negative consequences in `## Consequences`. Honesty about cost.
- When invalidating a previous decision, do so explicitly. Replace the ADR; do not paper over.

## References

- `00-foundations/PARADIGM.md`
- `00-foundations/PRINCIPLES.md`
- `00-foundations/DETERMINISTIC-VS-AGENTIC.md`
- `10-security/ANTI-PATTERNS.md`
- `11-agentic-engineering/HARNESS-PATTERNS.md`
## Graph links

[[PARADIGM]]  [[PRINCIPLES]]  [[DETERMINISTIC-VS-AGENTIC]]
