---
id: dependency-graph
title: Dependency Graph
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-30
---
# Dependency Graph

This document is **auto-generated** by the doc linter from `depends_on:` and `depended_on_by:` frontmatter fields. The hand-written summary below is a bootstrap snapshot of the corpus on 2026-04-30 that holds until the linter runs in CI; treat the prose as illustrative and the frontmatter on each doc as authoritative.

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
chapter                       non-spec docs    specs (in docs/specs/)
00-foundations                    8                 0
01-architecture                   8                 0
02-platform                       2                16
03-runtime                        2                17
04-memory                         2                17
05-protocol                       2                 8
06-sdk                            3                18
07-ui                             2                17
08-voice                          2                10
09-backend                        3                 7
10-security                       4                10
11-agentic-engineering            9                 0
12-distribution                   7                 9
13-remotes                        2                 6
14-rfcs                          33                 0
meta                              2                 0
─────────────────────────────────────────────────────
total                            91               131  =  222
```

## Graph statistics (2026-04-30 snapshot)

```
total docs with id field:         222
total depends_on edges:           585
root nodes (nothing points to):    63
broken depends_on references:       0
```

Root nodes are either: top-level foundations that nothing inherits from, or terminal implementation SPECs that no other SPEC references.

## Most load-bearing documents

Sorted by in-degree (number of other documents that declare `depends_on` pointing here):

```
in-degree   id                       type
   28        principles               DESIGN
   24        capability-gate          SPEC
   19        agentd-daemon            SPEC
   19        memory-architecture      DESIGN
   17        oci-native-model         DESIGN
   15        cosign-trust             SPEC
   13        paradigm                 DESIGN
   13        capability-taxonomy      SPEC
   11        inference-router         SPEC
   11        capnp-rpc                SPEC
   11        cryptography             SPEC
   10        audit-log                SPEC
   10        shell-overview           DESIGN
   10        canvas-model             SPEC
   10        voice-pipeline           DESIGN
```

These are the documents whose stability is most critical: a breaking change to any of them propagates to the most dependents.

## Layer structure

The corpus forms a partial order. The intended stratification (lower layers may not `depends_on` higher layers):

```
Layer 0 — Foundations:   vision, paradigm, principles, glossary
Layer 1 — Architecture:  system-overview, process-model, trust-boundaries, threat-model
Layer 2 — Platform:      kernel, image, boot, sandbox, storage, audio, display, network
Layer 3 — Runtime:       agentd, policyd, inferenced, memoryd, toolregistry, event-bus
Layer 4 — Protocol:      capnp, nats, iceoryx, dbus, focusbus
Layer 5 — Memory:        six memory layers, consolidation, dreaming, retrieval
Layer 6 — SDK:           app format, lifecycle, kernel-framework, blocks, render, skills, souls
Layer 7 — UI:            shell, canvas, components, gestures, workspaces
Layer 8 — Voice:         pipeline, wake-word, STT, TTS, VAD, AEC
Layer 9 — Backend:       provisioning, OTA, sync, gateway, registry
Layer 10 — Security:     privacy, capabilities, audit, cryptography, verified-boot
Layer 11 — Distribution: OCI model, namespaces, build, signing
Layer 12 — Remotes:      pairing, discovery, protocol, fleet (v2 scope)
```

The linter enforces that no doc in layer N has a `depends_on` edge to a doc in layer M where M > N. The ADR corpus (`14-rfcs/`) is outside the layer structure — ADRs record decisions, they do not define contracts.
