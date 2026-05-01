---
id: glossary
title: Glossary
type: GUIDE
status: draft
version: 0.0.0
depends_on: []
depended_on_by: []
last_updated: 2026-04-29
---
# Glossary

Canonical technical vocabulary for Kiki OS. Every term used in other documents is defined here. If a term is ambiguous in the broader industry, this document gives the meaning Kiki uses.

Terms are organized by domain. Within each domain, alphabetical.

## Core platform

**agentd**
The agent harness daemon. The privileged userspace process that runs the agent, dispatches tools, enforces the capability gate, and coordinates events. Specified in `03-runtime/AGENTD-DAEMON.md`.

**Appliance OS**
An OS designed for a single purpose, opaque to its underlying Linux substrate, image-based, atomic, signed. Kiki is an appliance OS for agentic computing. See `00-foundations/PARADIGM.md`.

**bootc**
The bootable container model: an OCI image is the OS deployment unit. `bootc upgrade` pulls a new image and switches to it atomically.

**Kiki OS**
The complete operating system: kernel, init, image composition, sandbox, agent harness, memory subsystem, hardware abstraction layer, compositor, voice pipeline, identity system.

**Hardware class**
A category of devices grouped by capabilities. v0 supports `desktop`. Future classes are added via RFC.

**Hardware manifest**
A signed TOML file at `/etc/kiki/hardware-manifest.toml` describing the device's capabilities. Read at boot.

**OCI artifact**
A signed, content-addressed artifact distributed via an OCI registry. Kiki distributes everything (base image, sysext, apps, components, tools, profiles, models, skills, bundles) as OCI artifacts.

**Sysext**
A systemd system extension: a signed image that overlays `/usr` and `/opt` to add software to the base. In Kiki, the agent runtime ships as a sysext OCI artifact.

**Upstream**
The Linux distribution from which we compose our base image. Operational, not contractual. v0 uses CentOS Stream 10 bootc.

## Runtime

**Agent**
The reasoning entity. The combination of a model, a context, a memory subsystem, and a set of tools. There is one primary agent per workspace, plus subagents spawned for specific tasks.

**Subagent**
An agent spawned by another agent. Three kinds: Fork (isolated context), Teammate (parallel coordinated agent), Worktree (persistent domain-scoped agent). Defined in `03-runtime/SUBAGENTS.md`.

**Tool**
A capability the agent can invoke. Implemented by an app, a WASM component, or a built-in. Has a name, description, parameter schema, result schema.

**Skill**
A Markdown document teaching the agent how to use one or more tools effectively. Skills do not contain code.

**Soul**
A `SOUL.md` file defining the agent's voice and stance. Editable via the consent flow.

**Identity**
Three Markdown files: `SOUL.md` (agent voice), `IDENTITY.md` (device identity, signed at build), `USER.md` (user identity, per-user). Versioned in git.

**App**
A signed OCI container image with a Profile, optional UI surfaces, and tools. Run via podman quadlet. The unit of distribution.

**App tier**
One of: tool (headless, ephemeral), light (system widgets via DBus), full (own Wayland surface).

**Workspace**
A parallel agentic session: own canvas, ops log, agent task, optional memory namespace and policy class. Multiple per user. Specified in `03-runtime/WORKSPACE-LIFECYCLE.md`.

## Memory

**Sensory buffer**
A ring buffer in RAM holding raw perceptions (audio, video, sensor data) for seconds. Never persists.

**Working memory**
The current context — what is loaded into the model for the current inference.

**Episodic memory**
What happened. Stored in LanceDB with native versioning as transaction time. Conversations, events, observations.

**Semantic memory / Semantic graph**
What is true. Stored as a temporal knowledge graph in CozoDB. Bitemporal, source-attributed, confidence-weighted.

**Procedural memory**
How to do things. Stored as TOML+Markdown files indexed by sqlite-vec. Workflows, patterns.

**Identity memory**
Who Kiki is and who the user is. The most protected layer. Markdown files in git.

**Bitemporal**
Having two time dimensions: valid time (when something is true in the world) and transaction time (when the system learned it).

**Drift**
The gradual corruption of memory through repeated summarization, unresolved contradictions, or identity bleed. The existential risk of long-running agents.

**Compaction**
The process of reducing the size of working memory while preserving information. Five tiers, cheapest first.

**Pruning**
The deletion of low-utility memories from episodic and semantic storage.

**Dreaming**
Background consolidation. Three phases: Light (low-stakes cleanup), REM (theme extraction), Deep (durable promotion).

## Protocol and IPC

**Cap'n Proto RPC**
The capability-based RPC protocol used between the agent harness and apps. Replaces older custom protocols.

**NATS**
The embedded service bus used between system services and apps for pub/sub and request/reply.

**iceoryx2**
The zero-copy shared-memory IPC used for bulk data plane (audio frames, video frames, large textures).

**focusbus**
A DBus service `org.kiki.Focus1` that publishes selection state and component state across apps.

**Mailbox**
A durable async messaging system for capability prompts, approval requests, notifications, subagent results. Backed by SQLite per user.

**Manifest**
The metadata declaring an artifact's identity, runtime, capabilities, tool definitions, network policy, and resource limits. Embedded as OCI annotations or attached as an OCI artifact.

**Capability**
A named right to perform a sensitive action. The unit of access control. Catalogued in `10-security/CAPABILITY-TAXONOMY.md`.

**Capability gate**
The runtime component in `agentd` (delegated to `policyd`) that checks every sensitive operation against granted capabilities.

**Grant level**
How a capability is granted: Auto, InstallConsent, RuntimeConsent, ElevatedConsent, KikiSigned, OsOnly, Denied.

**Sandbox**
Kernel-level isolation: Landlock for filesystem, seccomp for syscalls, namespaces for network and mounts, cgroups for resources. Provided by the container runtime for apps.

**Audit log**
Append-only, hash-chained record of every capability grant and significant action. ct-merkle Merkle tree, opt-in sigsum witness submission.

## Inference

**Inference router**
The component in `inferenced` that decides whether a request goes to a local or remote model and adapts the request to the chosen model's capabilities.

**Hybrid inference**
The pattern in which some requests run locally and some run remotely, decided per-request by the router.

**Local model**
A model running on the device's silicon via the local inference engine (llama.cpp via llama-cpp-2).

**Remote model**
A model running outside the device, accessed via API through the backend's AI Gateway.

**Privacy level**
A classification of an inference request: Sensitive (must run locally), Standard (may go remote), Public (preferred remote for quality).

**Arbiter classifier**
The two-stage gating system that evaluates each tool call: Stage 1 fast pre-filter (Llama Prompt Guard 2), Stage 2 deliberative (Granite Guardian 3.2). See `03-runtime/ARBITER-CLASSIFIER.md`.

## Voice

**VAD**
Voice Activity Detection. Determines whether audio contains speech.

**STT**
Speech-to-text. Transcription.

**TTS**
Text-to-speech.

**Wake word**
A short phrase that activates the agent without explicit invocation. Detected locally.

**Barge-in**
The user interrupting the agent while it is speaking.

**Voice channel**
A source of audio input/output: Native (device's mic/speaker), WebRTC (remote browser/app), Bridge (messaging app voice notes).

## Events and orchestration

**Hook**
A registered handler that fires at a specific point in the agent's lifecycle. Three modes: Observe (read-only), Intercept (can deny), Transform (can modify).

**Approval request**
A mailbox message from a tool or subagent requesting permission for a risky action.

**Push event**
A signal from a service or external source that may trigger new inference. Carries an InferenceHint.

**Inference hint**
Routing guidance attached to events: TriggerNow, Accumulate, ContextOnly, IfIdle.

**Coordinator**
The agent-loop component that processes mailbox messages, decides on approvals, and triggers inference.

**LoopBudget**
The mechanism preventing the agent from looping forever. Default 25 cycles per task.

## UI

**Compositor**
Cage, a kiosk Wayland compositor. Runs `agentui` as its single fullscreen client.

**agentui**
The single GUI app of Kiki OS. Hosts the canvas, status bar, command bar, task manager, voice pipeline integration. Built in Rust + Slint + Servo + wgpu.

**Canvas**
The reactive scene graph rendered by `agentui`. Components mount, unmount, update reactively. Ops log enables back/forward and branching.

**Block**
A top-level renderable unit on the canvas: text, image, code_diff, table, chart, app_surface, web, system widget.

**Component**
A reusable UI primitive composed within blocks. Standard catalog (`kiki:core/components/*`) plus third-party.

**Layout intent**
A pattern (flow, split, focus, grid, stack) that the canvas applies to compose blocks.

**Slint**
The UI toolkit for the shell and apps. Rust-native, declarative, compiled at build time.

**Servo**
The web rendering engine for HTML blocks. Embedded in-process via the `servo` crate.

## Distribution

**Namespace**
A maintainer-owned identifier (e.g., `acme`, `kiki:core`, `kiki:dev`). Each namespace has a registered cosign public key and canonical OCI registry URL.

**Identity (canonical)**
`kiki:<namespace>/<name>@<version>`. Resolves to an OCI URL via the namespace registry.

**OCI registry**
A standard OCI distribution endpoint hosting Kiki artifacts. Federated; each maintainer can run their own.

**cosign**
The tool used to sign and verify OCI artifacts. Per-namespace keys. Optional Sigstore witness submission.

**Sigstore**
The transparency log infrastructure used for opt-in witness submission.

**agentctl**
The CLI client for installing, updating, signing, and managing Kiki artifacts. Pure OCI client + cosign.

## Conventions

When the documentation refers to:

- **"the agent"** without qualification — the primary agent for the active workspace.
- **"the device"** without qualification — the Kiki device the user is currently working with.
- **"the user"** — the human currently associated with the device.
- **"the system"** — Kiki OS as a whole.
- **"a tool"** — a tool registered with `toolregistry`.
- **"a model"** — an AI model used for inference.
- **"local"** vs **"remote"** — local means on the device. Remote means anywhere else.

## Terms not used

These terms appear in the broader industry but Kiki documentation avoids them:

- **"Smart"** — vague marketing term. Kiki devices run an agent.
- **"Assistant"** — implies servant. Kiki's agent is the substrate.
- **"Cloud-native"** — Kiki is edge-native.
- **"Conversational AI"** — Kiki is agentic, not just conversational.
- **"App store"** — Kiki has a federated registry, not a centralized store.
- **"Distro"** — Kiki is an appliance OS, not a Linux distribution.
