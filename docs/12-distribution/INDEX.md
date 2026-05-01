---
id: distribution-index
title: Distribution — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Distribution

OCI-native distribution, namespace identity, registry operations, maintainer workflows.

## Model

- `OCI-NATIVE-MODEL.md` — OCI for everything: rationale and architecture.
- `../specs/NAMESPACE-MODEL.md` — `kiki:<namespace>/<name>@<version>` identity.
- `../specs/MEDIA-TYPES.md` — Kiki-reserved OCI media types.

## Catalog

- `ARTIFACT-CATALOG.md` — canonical Kiki artifacts (the ~30 core ones).
- `../specs/META-PACKAGES.md` — desktop, headless, developer, minimal compositions.
- `RELEASE-CADENCE.md` — per-artifact frequency.

## Workflows

- `OCI-WORKFLOWS.md` — build, sign, push (for maintainers).
- `../specs/BUILD-SYSTEM.md` — mkosi + cargo + cosign pipeline.
- `../specs/SNAPSHOT-PINNING.md` — upstream snapshot strategy.
- `MAINTAINER-GUIDE.md` — how to publish under `kiki:<namespace>/*`.

## Registry

- `REGISTRY-OPERATIONS.md` — running an OCI registry for Kiki content.
