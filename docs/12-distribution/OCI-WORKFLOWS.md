---
id: oci-workflows
title: OCI Workflows
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - oci-native-model
  - media-types
  - cosign-trust
  - sigstore-witness
depended_on_by:
  - build-system
  - maintainer-guide
last_updated: 2026-04-30
---
# OCI Workflows

## Purpose

Cookbook-style workflows for the things maintainers do with OCI: build, sign, push, attest, verify. Other docs are the spec; this is the recipe.

## Build a container app

```
# Build with podman or buildah; reproducible
buildah bud --layers --disable-compression=false \
  --tag registry.example/apps/my-app:1.2.0 .
```

For reproducibility:

- Use a pinned base image
- Set `SOURCE_DATE_EPOCH` from the git commit
- Use mkosi for system images that need bit-for-bit reproducibility

## Build an OCI artifact (component, profile, skill, etc.)

```
# Build the bundle tar
tar -cf bundle.tar component/

# Push as OCI artifact via oras
oras push registry.example/components/my-component:1.0.0 \
  --config config.toml:application/vnd.kiki.component.config.v1+toml \
  --artifact-type application/vnd.kiki.component.config.v1+toml \
  bundle.tar:application/vnd.kiki.component.bundle.v1+tar+gzip
```

## Sign

```
# Keyed
cosign sign --key cosign.key registry.example/apps/my-app:1.2.0

# Keyless via OIDC (CI)
cosign sign --identity-token=$ID_TOKEN \
  registry.example/apps/my-app:1.2.0
```

Both produce a Sigstore Rekor log entry. Verify it's there:

```
cosign verify --certificate-identity-regexp '^https://github.com/me/' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  registry.example/apps/my-app:1.2.0
```

## Attach SBOM

```
syft registry.example/apps/my-app:1.2.0 -o spdx-json > sbom.spdx.json
cosign attest --predicate sbom.spdx.json \
  --type spdxjson \
  --key cosign.key \
  registry.example/apps/my-app:1.2.0
```

## Attach release notes

```
cat > release-notes.md <<EOF
# my-app 1.2.0

- New feature
- Bug fix
EOF

oras attach registry.example/apps/my-app:1.2.0 \
  --artifact-type application/vnd.kiki.releasenotes.v1+text \
  release-notes.md
```

## Verify before install

The Kiki client does this automatically; here's the manual equivalent:

```
# 1. Verify signature
cosign verify --certificate-identity-regexp '...' \
  registry.example/apps/my-app:1.2.0

# 2. Verify Rekor log entry
cosign verify-attestation --type spdxjson \
  registry.example/apps/my-app:1.2.0

# 3. Pull and inspect
oras pull registry.example/apps/my-app:1.2.0
```

## Multi-arch

Build per-arch images and create a manifest list:

```
buildah manifest create my-app:1.2.0
buildah manifest add my-app:1.2.0 \
  registry.example/apps/my-app:1.2.0-amd64
buildah manifest add my-app:1.2.0 \
  registry.example/apps/my-app:1.2.0-arm64
buildah manifest push --all my-app:1.2.0 \
  docker://registry.example/apps/my-app:1.2.0
```

## Update the namespace registry

Once an artifact is pushed, the namespace registry should advertise the right registry URL and signing identity for the namespace. Maintainers update via the registry's CLI or API:

```
kiki-namespace publish --namespace=acme \
  --registry=ghcr.io/acme/kiki \
  --sigstore-identity '^https://github.com/acme/.*'
```

## CI integration

A reference GitHub Actions workflow:

```yaml
name: release
on:
  push:
    tags: ['v*.*.*']
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      id-token: write           # for keyless cosign
      packages: write
    steps:
      - uses: actions/checkout@v4
      - run: kiki-pkg build .
      - run: kiki-pkg lint .
      - run: kiki-pkg push --to=ghcr.io/${{ github.repository_owner }}/...
      - run: cosign sign --identity-token=$ID_TOKEN ...
      - run: kiki-pkg attest sbom ...
      - run: kiki-pkg attest provenance ...
```

## Anti-patterns

- Mutating tags after push
- Skipping Rekor (cosign without `--rekor-url=…` defaults to public Rekor; keep that)
- Pushing without an SBOM
- Letting CI keys live in environment variables (use OIDC keyless)

## Acceptance criteria

- [ ] Container app builds and signs
- [ ] OCI artifact pushes via oras
- [ ] cosign keyed and keyless both work
- [ ] SBOM attached + verifiable
- [ ] Multi-arch manifest list builds
- [ ] CI reference workflow runs to completion

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/MEDIA-TYPES.md`
- `12-distribution/BUILD-SYSTEM.md`
- `12-distribution/MAINTAINER-GUIDE.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/SIGSTORE-WITNESS.md`
- `06-sdk/PUBLISHING.md`
## Graph links

[[OCI-NATIVE-MODEL]]  [[MEDIA-TYPES]]  [[COSIGN-TRUST]]  [[SIGSTORE-WITNESS]]
