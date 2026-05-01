---
id: dependency-graph
title: Dependency Graph
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-30
---
# Dependency Graph

This document is **intended to be auto-generated** by the doc linter from `depends_on:` and `depended_on_by:` frontmatter fields. The hand-written summary below is a bootstrap snapshot of the corpus on 2026-04-30 that holds until the linter runs in CI; treat the prose as illustrative and the frontmatter on each doc as authoritative.

## Generation

The linter runs in CI on every PR. It:

1. Parses frontmatter from every Markdown file in `docs/`.
2. Builds a directed graph from `depends_on:` edges.
3. Validates that every reference resolves to an existing document.
4. Validates that no `stable` document depends on a `draft` document as load-bearing.
5. Detects cycles (which are errors).
6. Regenerates this document with the current graph.

## Corpus shape

```
chapter                       docs
00-foundations                  7 + INDEX
01-architecture                 7 + INDEX
02-platform                    17 + INDEX
03-runtime                     18 + INDEX
04-memory                      18 + INDEX
05-protocol                     9 + INDEX
06-sdk                         20 + INDEX
07-ui                          18 + INDEX
08-voice                       11 + INDEX
09-backend                      9 + INDEX
10-security                    13 + INDEX
11-agentic-engineering          8 + INDEX
12-distribution                11 + INDEX
13-remotes                      7 + INDEX
14-rfcs                        28 ADRs + 4 process/template + INDEX
meta                            2 (this directory)
```

Total: 225 Markdown files in `docs/`.

## High-level layers (top → bottom)

```
12-distribution    OCI-native distribution; identifiers; registries
       │
       ▼
14-rfcs            decisions
       │
       ▼
00-foundations     paradigm, principles, vision
       │
       ▼
01-architecture    system overview, process model, trust boundaries
       │
       ▼
02-platform        upstream, image, kernel, sandbox, audio, DRM, HAL
       │
       ▼
03-runtime         agentd + 4 daemons + agent loop + gate + ...
       │           ┌───────────┐
       ├──────────▶│ 04-memory │ (six layers, dreaming, drift)
       │           └───────────┘
       │           ┌──────────┐
       ├──────────▶│ 05-proto │ Cap'n Proto, NATS, DBus, iceoryx2
       │           └──────────┘
       │           ┌──────────┐
       ├──────────▶│ 07-ui    │ shell, canvas, components, gestures
       │           └──────────┘
       │           ┌──────────┐
       ├──────────▶│ 08-voice │ pipeline, channels, ASR/TTS, barge-in
       │           └──────────┘
       │           ┌────────────────────────┐
       └──────────▶│ 11-agentic-engineering │ harness, evals, prompts
                   └────────────────────────┘
       ▼
06-sdk             Kernel + Blocks + Render + System contracts; bindings
       │
       ▼
13-remotes         peer pairing, protocol, fleet, platforms
       │
       ▼
09-backend         optional cloud services; self-hostable
       │
       ▼
10-security        cross-cutting (gate, taxonomy, crypto, audit, CaMeL)
```

10-security is referenced from many layers; it's better viewed as a cross-cutting concern than a downstream layer.

## Selected dependency edges (illustrative)

### Foundation → Architecture

```
00-foundations/PARADIGM           ◀──── 01-architecture/APPLIANCE-MODEL
00-foundations/PRINCIPLES          ◀──── 03-runtime/AGENTD-DAEMON
00-foundations/PRINCIPLES          ◀──── 04-memory/MEMORY-ARCHITECTURE
00-foundations/PRINCIPLES          ◀──── 11-agentic-engineering/HARNESS-PATTERNS
```

### Platform → Runtime

```
02-platform/CONTAINER-RUNTIME      ◀──── 06-sdk/APP-CONTAINER-FORMAT
02-platform/SANDBOX                ◀──── 02-platform/CONTAINER-RUNTIME
02-platform/AUDIO-STACK            ◀──── 08-voice/AUDIO-IO
01-architecture/HARDWARE-ABSTRACTION ◀──── 05-protocol/DBUS-INTEGRATION
```

### Runtime → cross-cutting

```
03-runtime/AGENTD-DAEMON           ◀──── 04-memory/MEMORY-FACADE
03-runtime/CAPABILITY-GATE         ◀──── 03-runtime/TOOL-DISPATCH
03-runtime/INFERENCE-ROUTER        ◀──── 08-voice/STT-CLOUD
03-runtime/AGENT-LOOP              ◀──── 11-agentic-engineering/CONTEXT-ENGINEERING
```

### Memory subgraph

```
04-memory/MEMORY-ARCHITECTURE
    ├── SENSORY-BUFFER
    ├── WORKING-MEMORY     ──▶ COMPACTION
    ├── EPISODIC-MEMORY    ──▶ LANCEDB-INTEGRATION
    ├── SEMANTIC-GRAPH     ──▶ COZODB-INTEGRATION ──▶ BITEMPORAL-FACTS
    ├── PROCEDURAL-MEMORY  ──▶ DREAMING
    └── IDENTITY-FILES     ──▶ CONSENT-FLOW
                                     │
                                     ▼
                          CONTRADICTION-RESOLUTION
                                     │
                                     ▼
                            DRIFT-MITIGATION
                                     │
                                     ▼
                                RETRIEVAL  (consumes all six)
                                  PRUNING  (governs all six)
```

### Protocol subgraph

```
05-protocol/CAPNP-RPC
    ├── CAPNP-SCHEMAS
    └── TRANSPORT-UNIX-SOCKET
05-protocol/NATS-BUS  (paired with the event bus)
05-protocol/DBUS-INTEGRATION  ──▶ FOCUSBUS
05-protocol/ICEORYX-DATAPLANE  (audio/tensor data plane)
05-protocol/IPC-PATTERNS  (synthesizes the four)
05-protocol/ERROR-MODEL  (consumed by all)
```

### SDK → distribution

```
06-sdk/SDK-OVERVIEW
   ├── KERNEL-FRAMEWORK ──▶ BLOCKS-API, RENDER-API, SYSTEM-CLIENTS
   ├── APP-CONTAINER-FORMAT ──▶ APP-RUNTIME-MODES, APP-LIFECYCLE
   ├── COMPONENT-OCI-FORMAT
   ├── PROFILE-OCI-FORMAT
   ├── SOUL-FORMAT, SKILL-FORMAT, AGENT-BUNDLE
   └── PUBLISHING ──▶ 12-distribution/*
```

### Backend → remotes

```
09-backend/BACKEND-CONTRACT
    ├── DEVICE-AUTH ──▶ DEVICE-PROVISIONING
    ├── OTA-DISTRIBUTION
    ├── AI-GATEWAY
    ├── MEMORY-SYNC
    ├── REGISTRY-PROTOCOL ──▶ NAMESPACE-FEDERATION
    └── SELF-HOSTING (consumes all)

13-remotes/REMOTE-ARCHITECTURE
    ├── DEVICE-PAIRING
    ├── REMOTE-DISCOVERY
    ├── REMOTE-PROTOCOL
    ├── REMOTE-CONFIG-SYNC
    ├── REMOTE-CLIENT-PLATFORMS
    └── FLEET-MANAGEMENT
```

### Security cross-cutting

10-security is depended on by most chapters:

- `CAPABILITY-TAXONOMY` ← 03-runtime, 04-memory, 06-sdk, 13-remotes
- `AUDIT-LOG` + `AUDIT-MERKLE-CHAIN` ← 03-runtime, 04-memory, 09-backend, 13-remotes
- `CRYPTOGRAPHY` + `COSIGN-TRUST` + `SIGSTORE-WITNESS` ← 09-backend, 12-distribution, 13-remotes
- `CAMEL-PATTERN` ← 03-runtime/ARBITER-CLASSIFIER, 11-agentic-engineering/PROMPT-INJECTION-DEFENSE
- `STORAGE-ENCRYPTION` ← 04-memory, 02-platform/STORAGE-LAYOUT

## Cycles

No known cycles in the current corpus. The linter detects new cycles automatically; introducing one is a build-blocking error.

## Status crossovers

The corpus is currently treated as research-in-progress: every document is `status: draft` at `version: 0.0.0` until the implementation forces real contracts. The "no `stable` document depends on a `draft` document" rule from `CONVENTIONS.md` therefore does not fire today; it is retained because we expect specific docs to graduate to `stable` once the corresponding subsystem is implemented and exercised.

## Linter expectations (when implemented)

```
docs-lint
   ├── parse-frontmatter
   ├── resolve-id-references
   ├── detect-cycles
   ├── check-status-crossovers
   ├── check-orphans (no incoming or outgoing edges)
   ├── check-dangling (depends_on references a missing id)
   └── emit-graph (regenerates this file)
```

The linter is part of the CI pipeline; failures block PRs.

## References

- `meta/COVERAGE-MATRIX.md`
- `CONTRIBUTING.md`
- `CONVENTIONS.md`
