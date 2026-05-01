---
id: 0002-oci-native-distribution
title: OCI-Native Distribution for All Artifacts
type: ADR
status: draft
version: 0.0.0
depends_on:
  - 0001-appliance-os-paradigm
last_updated: 2026-04-29
depended_on_by:
  - 0003-cosign-sigstore-trust
  - 0004-namespace-registry
  - 0005-no-package-manager-user-facing
  - 0006-centos-stream-bootc-upstream
  - 0012-podman-quadlet-app-runtime
---
# ADR-0002: OCI-Native Distribution for All Artifacts

## Status

`accepted`

## Context

Kiki OS distributes many kinds of artifacts: the base OS image, system extensions (the runtime sysext), apps, components (Slint markup), tools (WASM), profiles (signed YAML), models (LLM weights), skills (Markdown), and agent bundles. Without a unified distribution model:

- Each artifact type would have its own packaging, signing, registry, and trust mechanism.
- Maintainers would need to learn N different ways to publish.
- Users would have N different update flows.
- Security audits would have N different surfaces.

A unified distribution mechanism is the structurally simpler answer.

## Decision

**All Kiki artifacts are signed OCI artifacts in federated OCI registries.**

Specifically:

- The base OS is a `bootc`-compatible OCI image.
- The Kiki runtime is a sysext OCI artifact.
- Apps are OCI container images run via podman quadlet.
- Components, tools, profiles, models, skills, and bundles are OCI artifacts with Kiki-specific `mediaType` annotations.
- All artifacts are signed with cosign.
- Trust is per-namespace: each maintainer's namespace has a registered cosign public key.
- Optional Sigstore witness submission for transparency.
- Federation via OCI registries is the default; any maintainer may run their own registry.

Canonical identity is `kiki:<namespace>/<name>@<version>`, resolved through a namespace registry to an OCI registry URL.

## Consequences

### Positive

- One distribution format for everything.
- One signing model (cosign + Sigstore).
- One trust mechanism (per-namespace keys).
- One update mechanism (atomic OCI pull + verify + apply).
- Layer deduplication: artifacts with shared base layers save disk.
- Industry-standard OCI tooling works out of the box: skopeo for inspection, oras for non-image artifacts, podman/buildah for image creation, registries like ghcr/quay/Harbor/Zot all compatible.
- Multi-arch supported natively via OCI manifest list.
- Reproducible: OCI image digests are content-addressed.
- Federation-friendly: maintainers are not tied to a central Kiki-controlled registry.

### Negative

- Maintainers familiar with apt/dnf/pacman packaging must learn Containerfile and cosign.
- OCI tooling has been stabilizing since 2023; mature on container images, less mature on arbitrary artifacts (improving rapidly).
- Storage overhead: each app bundles its own libraries (mitigated by layer dedup but never zero).
- Bootstrap problem: the namespace registry itself must be distributed somehow (we ship it as part of the base OS to break circularity).

## Alternatives considered

- **deb format with apt repos.** Rejected because it duplicates concerns the OS image already addresses, requires maintaining a parallel signing infrastructure (apt-secure), and contradicts the appliance paradigm.
- **rpm format with dnf repos.** Same issues as deb.
- **Flatpak.** Rejected because cross-distro portability is irrelevant for a single-purpose appliance OS, and Flatpak's runtime layer adds significant size.
- **Custom Kiki-specific format.** Rejected because reinventing distribution is unnecessary work that delivers no value over OCI.

## References

- `00-foundations/PARADIGM.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/MEDIA-TYPES.md`
- `09-backend/REGISTRY-PROTOCOL.md`
- OCI Distribution Spec v1.1
- OCI Image Spec v1.1
- Sigstore project documentation
