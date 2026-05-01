---
id: publishing
title: Publishing
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - app-container-format
  - component-oci-format
  - profile-oci-format
  - skill-format
  - agent-bundle
  - oci-native-model
  - cosign-trust
last_updated: 2026-04-30
---
# Publishing

## Purpose

Specify the workflow for publishing Kiki artifacts: build, sign, push to registry, advertise via the namespace registry. This is the maintainer's perspective; the user's perspective is `kiki install <id>`.

## Build

Build pipelines vary per artifact:

- **App**: container image via mkosi or buildah; must be reproducible
- **Component**: bundle tar; Slint compile in sandbox
- **Profile**: bundle tar; YAML/TOML validation
- **Skill**: standalone Markdown (no build step)
- **Agent bundle**: bundle tar
- **Tool**: WASM (Wassette) or Rust binary in container

The reference `kiki-pkg` CLI wraps these:

```
kiki-pkg build .              # build the artifact in this directory
kiki-pkg lint .                # validate manifest + content
kiki-pkg sign --key=cosign.key
kiki-pkg push --to=registry.example/my-app:1.0
```

## Reproducibility

Builds must be reproducible: same source → same digest. CI verifies. Reasons:

- Verifiable supply chain (anyone can re-build and confirm)
- Caches work (digest-stable)
- Signature-verifiable cross-environment

Recipe: pinned base images, pinned dependencies, deterministic builds (no embedded timestamps, no random ordering).

## Signing

Every artifact is signed with **cosign**:

```
cosign sign --key=cosign.key registry.example/my-app:1.0
```

Sigstore transparency log entry is mandatory:

```
cosign sign --keyless registry.example/my-app:1.0
# uses Fulcio for short-lived cert + Rekor log entry
```

We support both keyed and keyless signing. Keyed is fine for organizational publishing; keyless (OIDC-bound) is fine for individuals and CI.

The publisher's identity is part of the verification:

```
cosign verify
  --certificate-identity-regexp '^https://github.com/acme/'
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
  registry.example/my-app:1.0
```

## Pushing to a registry

We use **oras** for non-container OCI artifacts (components, profiles, etc.) and standard Docker/podman push for containers:

```
oras push registry.example/my-component:1.0 \
  --artifact-type application/vnd.kiki.component.v1+tar \
  bundle.tar
```

Any OCI-compliant registry works. We provide reference setups for ghcr, docker.io, harbor, distribution-spec.

## Namespace advertisement

The artifact's id is `kiki:<namespace>/<name>@<version>`. The mapping from namespace to registry is in the namespace registry:

```
maintainer publishes a record:
  namespace: "acme"
  registry: "ghcr.io/acme/kiki"
  pubkeys: ["...", "..."]
```

The Kiki client looks up the namespace, finds the registry, pulls the artifact, verifies the signature against the pubkeys (or the OIDC identity).

## Versioning

Semver. Pre-release tags via `1.0.0-rc1`. Tags are immutable once pushed; we publish a new digest, never overwrite.

## Channels

Maintainers may publish multiple channels:

```
my-app:1.0           default channel
my-app:1.0-beta      beta channel
my-app:nightly       rolling
```

Channels are conventions on the registry; users opt in to non-default channels in Settings.

## SBOM

Each artifact ships an SBOM (Software Bill of Materials) attached as a separate OCI artifact (in-toto attestation). Useful for auditors and compliance.

## Reproducibility verification

A separate verifier service (or local CLI) can re-run the build and compare digests:

```
kiki-pkg verify-rebuild --source=git@.../my-app.git --commit=abc123 \
  --image=registry.example/my-app:1.0
```

Mismatches indicate either a non-reproducible build or supply-chain tampering.

## Removing artifacts

If a vulnerability or licensing issue requires removal:

- Tag the version as deprecated in the namespace registry
- Optionally publish a Sigstore revocation
- The Kiki client warns users running affected versions

We don't unilaterally remove artifacts (registries decide their own policies); we mark and warn.

## Anti-patterns

- Pushing without signing
- Mutating tags (tag pointing to new digest)
- Publishing under someone else's namespace
- SBOM-less releases
- Non-reproducible builds

## Acceptance criteria

- [ ] All artifact types build via `kiki-pkg`
- [ ] Reproducibility verifiable
- [ ] cosign sign + Sigstore transparency log
- [ ] SBOM attached
- [ ] Namespace lookup resolves correctly
- [ ] Signature verification at install

## References

- `06-sdk/APP-CONTAINER-FORMAT.md`
- `06-sdk/COMPONENT-OCI-FORMAT.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
- `06-sdk/SKILL-FORMAT.md`
- `06-sdk/AGENT-BUNDLE.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/MAINTAINER-GUIDE.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/SIGSTORE-WITNESS.md`
