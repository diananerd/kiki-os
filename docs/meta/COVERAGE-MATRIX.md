---
id: coverage-matrix
title: Coverage Matrix
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-30
---
# Coverage Matrix

This document is **auto-generated** by the doc linter. It maps acceptance criteria from SPEC documents to the implementing tests in CI.

The summary below is a manual snapshot of the coverage *shape* on 2026-04-30; concrete test-name mappings appear after CI is wired up against the implementation tree.

## Generation

The linter:

1. Parses all SPEC documents.
2. Extracts items from each `## Acceptance criteria` section.
3. Cross-references them with test names, integration test definitions, and CI gates.
4. Reports coverage gaps (acceptance criteria with no implementing tests).
5. Reports orphan tests (tests not mapped to any acceptance criterion).

## Corpus snapshot

```
docs with `## Acceptance criteria`:      140
ADRs (decisions; not test-mapped):        28
Foundation / Vision docs:                  7
Process / templates:                       4
Total Markdown files in docs/:           225
```

## Per-chapter coverage shape

```
chapter                              docs-with-criteria
00-foundations                            0   (vision, principles, roadmap)
01-architecture                           0
02-platform                              16
03-runtime                               17
04-memory                                17
05-protocol                               8
06-sdk                                   19
07-ui                                    17
08-voice                                 11
09-backend                                8
10-security                              10
11-agentic-engineering                    1
12-distribution                           9
13-remotes                                6
14-rfcs                                   0
```

(Counted on 2026-04-30; the linter will re-derive these on every CI run once wired up.)

## Test-tree expectation

For each SPEC, acceptance criteria map to test names. The linter expects tests organized as:

```
tests/
├── platform/        boot, sandbox, audio, DRM, storage, ...
├── runtime/         agent-loop, gate, router, hooks, mailbox, ...
├── memory/          lancedb, cozodb, consent-flow, dreaming, ...
├── protocol/        capnp-rpc, nats, dbus, iceoryx
├── ui/              canvas, blocks, components, gestures, a11y
├── voice/           wake, vad, asr, tts, barge-in
├── backend/         auth, ota, gateway, sync, registry
├── security/        capability-gate, audit, crypto, camel
├── distribution/    oci-workflows, build, snapshot, registry
├── remotes/         pairing, discovery, protocol, fleet
└── eval/
    ├── capability/
    ├── safety/
    ├── injection/    AgentDojo + internal trifecta tests
    ├── cost/
    └── latency/
```

## Cross-cutting suites

Some tests cover multiple SPECs:

- **Provisioning end-to-end**: covers `09-backend/DEVICE-PROVISIONING`, `09-backend/DEVICE-AUTH`, `04-memory/IDENTITY-FILES`, `02-platform/VERIFIED-BOOT`.
- **Memory consistency**: covers all six layers + sync.
- **Tool dispatch**: covers `03-runtime/TOOL-DISPATCH`, `03-runtime/CAPABILITY-GATE`, `03-runtime/ARBITER-CLASSIFIER`, `10-security/CAMEL-PATTERN`.
- **Voice end-to-end**: covers the full `08-voice/` chapter.
- **Pairing + protocol**: covers `13-remotes/DEVICE-PAIRING`, `13-remotes/REMOTE-PROTOCOL`, `13-remotes/REMOTE-DISCOVERY`.

## Eval suite mapping

Per `11-agentic-engineering/EVALUATION.md`:

```
eval suite             tests gate                 source documents
─────────────────────────────────────────────────────────────────
capability             capability tasks            agent-loop, harness-patterns
safety                 hardcoded-restrictions      hardcoded-restrictions
injection              AgentDojo + internal         camel-pattern, arbiter-classifier
cost                   per-task token caps         cost-control
latency                surface contracts           voice-pipeline, agent-loop
```

The eval suite is a coverage source on equal footing with unit/integration tests.

## Coverage gates

Initial CI gates for promoting a release to stable:

```
Platform              90%
Runtime               95%   (core; tighter)
Memory                95%
Security             100%   (every criterion has ≥1 test)
Voice                 90%
UI                    85%
Backend               90%   (excluding self-hosted reference)
SDK                   85%
Remotes               90%
Distribution          85%
```

Starting targets; coverage tightens with each release.

## Reporting orphans

Tests not mapped to any acceptance criterion are flagged in the linter report. They may be intentional (regression tests for fixed bugs); maintainers either annotate them or move them under a referenced SPEC's section.

## Coverage gaps

A SPEC's criterion without an implementing test is reported as a gap. PRs that introduce gaps must either add the test or explicitly defer with an issue link.

## References

- `meta/DEPENDENCY-GRAPH.md`
- `11-agentic-engineering/EVALUATION.md`
- `CONTRIBUTING.md`
- `CONVENTIONS.md`
