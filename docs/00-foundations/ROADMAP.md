---
id: roadmap
title: Roadmap
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - vision
  - paradigm
depended_on_by: []
last_updated: 2026-04-30
---
# Roadmap

Phasing from skeleton to a Kiki OS the community can run and study. Kiki is open research developed in public; each phase is sized so external contributors and researchers can pick it up, exercise it, and feed results back. Phase boundaries are set so each phase delivers something testable end-to-end.

## v0 — Booting skeleton

Goal: a Kiki OS image boots, the shell appears, the agent responds, one app runs end-to-end.

- mkosi composes a CentOS Stream 10 bootc image with the Kiki Runtime sysext.
- Cage starts, launches `agentui`, status bar and empty canvas appear.
- Five daemons start with stub implementations sufficient to dispatch one tool call.
- One app of type `interactive_service` (`kiki:core/hello`) registers a tool and a component.
- Agent (Claude Code-class) handles a "hello world" prompt, calls the tool, renders a `Confirm` component, the user responds, the agent acknowledges.
- Audit log records the cycle. Cosign verification on the image.

What is **not** in v0: workspaces, voice, web blocks, multi-user, OTA, backend, multi-agent, third-party registries.

## v0.1 — Workspaces and voice

Goal: parallel agentic sessions and voice input/output.

- Workspace lifecycle implemented: create, switch, hibernate, archive.
- Voice pipeline: wake word, VAD, STT (Whisper turbo), TTS (Kokoro), AEC.
- Slash commands.
- Ops log invertible navigation (back/forward) and branching.
- 5-tier compaction L0–L2 deterministic.

## v0.5 — Tier-full apps and Servo

Goal: real apps that render their own canvas, plus rich web blocks.

- One reference app of type `interactive_service` with full tier (e.g., a minimal 3D viewer).
- DMA-BUF data plane via iceoryx2.
- Servo embedded for web blocks.
- Hooks system, full 18-point spec.
- Arbiter classifier two-stage active.
- 5-tier compaction L3 (background notes).
- One external maintainer namespace registered (`kiki:demo/*`).
- OTA via bootc upgrade for the base; sysext refresh for the runtime; podman auto-update for apps.

## v0.9 — Memory layer

Goal: full six-layer memory in production shape.

- LanceDB episodic with bitemporal transaction-time semantics.
- CozoDB semantic graph with bitemporal facts and supersession.
- Procedural memory with proposed-procedure flow.
- Identity files in git with consent flow non-bypassable.
- Dreaming three phases active.
- Drift mitigation with health reports.
- Memory export and import.

## v1 — Production

Goal: a Kiki OS the early adopters use daily.

- WASM components with logic via wasmtime.
- Kata containers as alternative high-isolation tier.
- Branch UI for canvas history.
- Backend services (provisioning, OTA distribution, AI gateway, registry, optional memory sync) deployable as a reference implementation.
- Multi-arch images (amd64, arm64).
- Reproducible builds verifiable end-to-end.
- Coverage matrix complete; every acceptance criterion tested.
- Stable RFC and ADR catalog.

## v2 — Multi-device and ecosystem

Goal: Kiki OS as a fleet, not just a device.

- Remote clients (iOS, Android, macOS, Windows, Linux, Web) paired as peers.
- Memory sync E2E encrypted, bitemporal-aware.
- Fleet management for organizations.
- Multi-display canvas, with workspaces per monitor.
- Third-party app ecosystem with multiple registered namespaces.
- Optional self-hosted backend.

## Beyond v2

- Hardware classes beyond desktop (mobile foldable, accelerated headless, sensor) added via RFCs.
- RISC-V as primary target in addition to amd64/arm64.
- Localization beyond English/Spanish.
- Voice-realtime APIs as opt-in.

## Cadence

- Internal milestones every 2–4 weeks during v0–v0.5.
- v0.9 and v1 are quality gates, not date-driven.
- Post-v1, releases on a quarterly cadence (one bootc image bump per quarter for the base; faster for sysext and apps).

## Open questions

- Whether to ship a reference cloud backend or only the protocol.
- How to handle proprietary GPU drivers (NVIDIA blob) within the appliance shape.
- Naming of the canonical default agent persona.
- Whether v1 ships with English-only or multilingual.
## Graph links

[[VISION]]  [[PARADIGM]]
