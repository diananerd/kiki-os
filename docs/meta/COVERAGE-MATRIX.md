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

The summary below is a snapshot of the coverage *shape* on 2026-04-30; concrete test-name mappings appear after CI is wired up against the implementation tree.

## Generation

The linter:

1. Parses all documents in `docs/specs/`.
2. Extracts items from each `## Acceptance criteria` section.
3. Cross-references them with test names, integration test definitions, and CI gates.
4. Reports coverage gaps (acceptance criteria with no implementing tests).
5. Reports orphan tests (tests not mapped to any acceptance criterion).

## Corpus snapshot

```
Total Markdown files in docs/:           222
  SPECs (in docs/specs/):               131   ← all have ## Acceptance criteria
  DESIGNs:                               20
  ADRs:                                  28
  GUIDEs (incl. INDEX, meta):            43
docs with ## Acceptance criteria:        140
  SPECs:                                 131
  Non-SPEC docs with AC:                   9   (GUIDEs in 06-sdk, 08-voice, 09-backend,
                                               11-agentic-engineering, 12-distribution)
broken depends_on references:              0
```

## Per-chapter coverage shape

SPECs live in `docs/specs/` (flat). The chapter column below refers to the original domain of each SPEC.

```
chapter                        specs   non-spec-docs-with-AC
00-foundations                     0               0
01-architecture                    0               0
02-platform                       16               0
03-runtime                        17               0
04-memory                         17               0
05-protocol                        8               0
06-sdk                            18               1
07-ui                             17               0
08-voice                          10               1
09-backend                         7               1
10-security                       10               0
11-agentic-engineering             0               1
12-distribution                    9               4
13-remotes                         6               0
14-rfcs                            0               0
─────────────────────────────────────────────────────
total                            131               8
```

(Regenerated on 2026-04-30; the linter will re-derive these on every CI run once wired up.)

## Test-tree expectation

For each SPEC, acceptance criteria map to test names. The linter expects tests organized as:

```
tests/
  specs/
    <spec-id>/
      <criterion-slug>.test.*
```

Until that tree exists, every SPEC's acceptance criteria are reported as **uncovered**.

## Cross-reference integrity

The linter validates `depends_on` IDs against the full corpus on every run. Current state:

```
broken depends_on references:   0
```
