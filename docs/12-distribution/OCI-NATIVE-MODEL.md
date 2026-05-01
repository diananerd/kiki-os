---
id: oci-native-model
title: OCI-Native Model
type: DESIGN
status: draft
version: 0.0.0
implements: [oci-native-distribution]
depends_on:
  - principles
  - paradigm
  - cosign-trust
  - sigstore-witness
depended_on_by:
  - app-container-format
  - artifact-catalog
  - build-system
  - component-oci-format
  - component-registry
  - maintainer-guide
  - media-types
  - meta-packages
  - model-registry
  - namespace-model
  - oci-workflows
  - ota-distribution
  - profile-oci-format
  - publishing
  - registry-operations
  - release-cadence
  - update-orchestrator
last_updated: 2026-04-30
---
# OCI-Native Model

## Problem

Kiki ships many kinds of artifacts: base images, system extensions, apps, components, tools, profiles, skills, agent bundles, models, prompts. Historically each ecosystem invents its own packaging — debs, rpms, flatpaks, snaps, App Store bundles. Each has its own signing story, its own update mechanics, its own cache. We don't want to inherit that mess.

## Decision

Kiki distributes **everything** as OCI artifacts. One format, one registry surface, one signing path (cosign + Sigstore), one identity scheme (`kiki:<namespace>/<name>@<version>`). No package managers visible to users; the only user verb is `kiki install <id>`.

## Why OCI

- **Mature.** Container ecosystem has solved registry, transport, manifests, signatures, multi-arch — for over a decade.
- **General.** OCI artifacts are not just containers; via `oras` and Sigstore, any blob with a manifest works.
- **Composable.** Layers, references, attestations all part of the spec.
- **Tooling.** podman, oras, cosign, distribution-spec — all open, all auditable.
- **No vendor lock-in.** Any OCI registry works.

## What ships as OCI

```
Kiki artifact         OCI shape
─────────────────────────────────────────────
base image (bootc)    container image
sysext                container image (extension)
app                   container image (manifest declares mode)
component             OCI artifact (Slint bundle)
tool                  OCI artifact (Wassette WASM or container)
profile               OCI artifact (TOML bundle)
skill                 OCI artifact (Markdown bundle)
agent bundle (.kab)   OCI artifact
model                 OCI artifact (single-blob)
prompts pack          OCI artifact (text bundle)
```

Each has a Kiki-reserved media type (see `MEDIA-TYPES.md`) so a registry tells the right kind apart from arbitrary containers.

## What does NOT ship as OCI

- The user's data (memory, identity, settings) — those are not artifacts; they are state.
- Logs and reports — those are filesystem state.
- Audit log entries — those live in the audit chain, not the registry.

## Identity

`kiki:<namespace>/<name>@<version>` is the universal identifier. It resolves through the namespace registry into a concrete OCI registry URL. See `NAMESPACE-MODEL.md`.

## Signing

Every artifact is signed with cosign; the signature is attached as a separate OCI manifest under the same digest. Sigstore transparency log entries are mandatory; verification at install and at every load.

## Multi-arch

Multi-arch via standard OCI manifest lists (image index). Kiki devices pull the right blob per their architecture.

## Reproducibility

Maintainers are expected (and verified by CI) to produce reproducible builds. The artifact's digest is therefore a hash of the *content*, not "whatever Docker emitted." Anyone can re-build and confirm.

## Updates

The update orchestrator (see `UPDATE-ORCHESTRATOR.md`) pulls per-channel:

- Base / sysext channels for system updates (bootc handles atomic apply)
- App channel for installed apps
- Other channels for components, models, etc.

A user controls cadence per channel.

## SBOM and attestations

Each artifact carries an SBOM (in-toto attestation) and may carry additional attestations (provenance, license analysis, vulnerability scans). The Kiki client surfaces these during install review.

## Anti-patterns we avoid

- A separate format per artifact type
- Trust-on-first-use without Sigstore
- Mutable tags as security boundary
- Centralized "Kiki app store" as a control point
- Embedded package managers (apt, pip, npm) at the user-facing layer

## Consequences

### Positive

- One mental model for everyone (users, maintainers, contributors)
- Strong end-to-end signing
- Decentralized publishing
- Cross-platform tooling
- Cheap CI/CD pipelines reusing existing OCI infrastructure

### Negative

- Some artifacts are odd as OCI (a profile is a few KB of YAML; we still wrap in OCI for consistency).
- Registries vary in OCI-artifact support; we test against the major implementations and document compatibility.
- Tooling familiarity: maintainers may know dpkg/rpm but not oras. We provide docs and CLI helpers.

## References

- `00-foundations/PARADIGM.md`
- `00-foundations/PRINCIPLES.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/MEDIA-TYPES.md`
- `12-distribution/ARTIFACT-CATALOG.md`
- `12-distribution/OCI-WORKFLOWS.md`
- `12-distribution/REGISTRY-OPERATIONS.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/SIGSTORE-WITNESS.md`
- `14-rfcs/0002-oci-native-distribution.md`
