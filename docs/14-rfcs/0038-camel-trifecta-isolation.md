---
id: 0038-camel-trifecta-isolation
title: CaMeL Pattern for Trifecta-Touching Tools
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
last_updated: 2026-04-29
depended_on_by:
  - 0040-arbiter-classifier-two-stage
  - 0041-coordinator-worker-isolation
---
# ADR-0038: CaMeL Pattern for Trifecta-Touching Tools

## Status

`accepted`

## Context

Tools that simultaneously access private data, ingest untrusted content, and communicate externally (the "lethal trifecta") are vulnerable to prompt injection: instructions in untrusted content can manipulate the agent into exfiltrating private data via the external comm channel. Standard capability gating + arbiter classifier is not sufficient because the agent's reasoning itself becomes the injection vector.

## Decision

Adopt the **CaMeL pattern** (Capabilities for Mission-critical Execution with LLMs, DeepMind/ETH 2025) for tools declared `risk_class: trifecta`. The pattern splits the LLM into a privileged planner (sees user request, can plan tool calls) and a quarantined parser (parses untrusted content into typed fields, cannot call tools). A deterministic execution engine in `policyd` orchestrates between them.

## Consequences

### Positive

- Provable data-flow integrity for high-stakes tools (77% utility on AgentDojo with provable security).
- Prompt injection in untrusted content cannot escape the parser sandbox.
- Composes cleanly with the existing capability gate and arbiter classifier.
- Profile-driven: maintainers declare risk class.

### Negative

- 2x LLM cost for trifecta operations (planner + parser).
- +200–500ms latency per operation.
- Profile authors must accurately declare trifecta risk class.
- The DSL for the typed plan is a new surface to specify and version.

## Alternatives considered

- **Trust the single agent + arbiter classifier alone**: production data shows non-trivial prompt injection success rates.
- **Disallow trifecta tools entirely**: useful tools (web search, email summarization) would need to exist anyway.
- **Rule-based parser instead of quarantined LLM**: input space too varied; rules would be brittle.

## References

- `10-security/CAMEL-PATTERN.md`
- `01-architecture/THREAT-MODEL.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
- arXiv 2503.18813 (CaMeL paper)
## Graph links

[[0001-appliance-os-paradigm]]
