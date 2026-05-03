# Kiki OS — Documentation

Kiki OS is an **appliance OS for agentic computing**. The base, runtime, apps, components, tools, profiles, and models are all distributed as signed OCI artifacts. Users interact with the agent shell, never with traditional Linux package management.

## Why this exists

Kiki OS is an **open research effort**, developed in the open, that asks one question: *how far can a fully agentic operating system change the way humans interact with personal computers and mobile devices?* The deliverables are two: an OS people can actually run, and observations about agentic human-computer interaction that the broader community can scrutinize, replicate, and extend. Both deliverables require the OS to be real and usable — not a thought experiment — which is why the corpus commits to operational contracts (SPECs), traceable decisions (ADRs/RFCs), and a roadmap toward releases the community can adopt and feed back on. The depth of the design corpus is in service of that bar, not despite it.

## How to read this corpus

The documentation is organized into 16 chapters. Read in order if new to the project; jump to a specific chapter once familiar.

1. **`00-foundations/`** — vision, paradigm, principles, vocabulary. Start here.
2. **`01-architecture/`** — macro decisions: layers, processes, trust, threats.
3. **`02-platform/`** — OS base, image, sandbox, storage, audio, display.
4. **`03-runtime/`** — the agent harness: agentd, policyd, inferenced, memoryd, toolregistry.
5. **`04-memory/`** — six memory layers, bitemporal facts, dreaming, drift mitigation.
6. **`05-protocol/`** — IPC: Cap'n Proto, NATS, iceoryx, DBus, focusbus.
7. **`06-sdk/`** — how to build apps, components, tools, profiles, bundles.
8. **`07-ui/`** — shell, canvas, components, gestures, workspaces.
9. **`08-voice/`** — voice pipeline: wake word, STT, TTS, AEC, speaker ID.
10. **`09-backend/`** — optional cloud services (provisioning, OTA, sync, gateway, registry).
11. **`10-security/`** — privacy model, capabilities, audit log, hardcoded restrictions.
12. **`11-agentic-engineering/`** — research-validated patterns for agentic systems.
13. **`12-distribution/`** — OCI-native model, namespace identity, registry operations.
14. **`13-remotes/`** — multi-device fleet (v2 scope).
15. **`14-rfcs/`** — RFC process + Architectural Decision Records.
16. **`meta/`** — auto-generated graph + coverage matrix.

## Document types

- **DESIGN** — the decision and rationale. Why something is the way it is.
- **SPEC** — the operational contract. Inputs, outputs, behavior, failure modes, acceptance criteria.
- **GUIDE** — orientation material (this README, contributing, conventions).
- **RFC** — proposals for major changes.
- **ADR** — records of architectural decisions made.

See `CONVENTIONS.md` for frontmatter, naming, and authoring conventions.

## Status

Documents have a status: `draft`, `stable`, `deprecated`, or `superseded-by:<id>`. Only `stable` documents may be referenced as load-bearing by other `stable` documents.

As of 2026-05-01 the corpus is treated as **research-in-progress**: every document is `status: draft` at `version: 0.0.0` and stays there until the corresponding subsystem is implemented and exercised. The corpus contains 225 Markdown files: 131 SPECs, 20 DESIGNs, 28 ADRs, 1 RFC, 43 GUIDEs, and 2 generated meta documents. See `meta/DEPENDENCY-GRAPH.md` and `meta/COVERAGE-MATRIX.md` for the auto-generated cross-cutting views.

## Contributing

See `CONTRIBUTING.md`.
