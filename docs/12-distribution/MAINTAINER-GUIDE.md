---
id: maintainer-guide
title: Maintainer Guide
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - oci-native-model
  - namespace-model
  - oci-workflows
  - build-system
  - cosign-trust
last_updated: 2026-04-30
---
# Maintainer Guide

## Purpose

Walk a new maintainer through what they need to do to publish under their own namespace: get a namespace, set up signing, structure a project, build, sign, push, and deal with the inevitable issues.

## Step 1 — Pick a namespace

Pick a short, lowercase, alphanumeric name. Examples: `acme`, `julia`, `museum-de-fin-de-mundo`.

Check it's not in use:

```
kiki-namespace lookup acme
```

If available, register:

```
kiki-namespace register \
  --namespace=acme \
  --registry=ghcr.io/acme/kiki \
  --sigstore-identity '^https://github.com/acme/.*'
```

Reserved namespaces (`kiki`, `system`, etc.) cannot be registered by third parties.

## Step 2 — Set up signing

Two paths:

### Sigstore keyless (recommended)

Use OIDC-bound identities (GitHub Actions, GitLab, etc.) to sign without managing keys. Your namespace record's `sigstore-identity` regex matches the OIDC subject.

### Keyed

Generate a key pair:

```
cosign generate-key-pair
# produces cosign.key + cosign.pub
```

Store `cosign.key` in your CI secret manager. Add `cosign.pub` to your namespace record.

## Step 3 — Pick an artifact kind

```
app                  Run-able program with possible UI
component            Slint-based UI component
profile              Device configuration bundle
skill                Markdown recipe
agent_bundle         Subagent + SOUL extension
tool                 Wassette WASM or container tool
```

Each has its format spec under `06-sdk/`.

## Step 4 — Scaffold

```
kiki-pkg init <kind> my-thing
cd my-thing
```

The scaffold gives you a manifest, a build script, and a sample test.

## Step 5 — Implement

Code in your language of choice; SDK bindings exist for Rust, Python, TypeScript, Go, C. Rust is the canonical and best-supported.

Make sure to:

- Declare all required capabilities in the manifest
- Provide localized strings for at least one language
- Pass a11y lint
- Write tests

## Step 6 — Build and lint

```
kiki-pkg build .
kiki-pkg lint .
```

Lint catches: missing manifest fields, undeclared capabilities used, accessibility issues, schema problems.

## Step 7 — Test locally

```
kiki-pkg dev .             hot-reload local run with stub services
kiki-pkg run .             run with real local kiki daemon
```

## Step 8 — Sign and push

```
kiki-pkg sign --identity-token=$ID_TOKEN
kiki-pkg push --to=ghcr.io/acme/kiki/my-thing:1.0.0
```

The push includes:

- The artifact
- The cosign signature (Sigstore log entry)
- The SBOM attestation
- Release notes

## Step 9 — Update namespace record (if first release)

```
kiki-namespace publish --namespace=acme
```

Refreshes the cached record. Existing devices see the new artifact within 24h.

## Step 10 — Communicate

Add a release note. Update your README with the install command:

```
kiki install kiki:acme/my-thing@1.0.0
```

Optionally, list your artifact in a community catalog.

## Common issues

### Reproducibility mismatch

CI catches this. Most common causes: timestamps in built files, non-deterministic dependency resolution, embedded paths. Fix the cause; don't disable the check.

### Cap'n Proto schema break

The CI lint blocks PRs that break schema compatibility. If you really mean to break, justify in the PR; the build orchestrator may schedule a major bump.

### Capability declaration mismatches usage

If you call something at runtime that wasn't declared, the gate denies. Fix the manifest, or fix the code to not need that capability.

### Sigstore log entry missing

Make sure your CI has `id-token: write` permission and you're using OIDC-bound signing.

### Namespace record stale

Devices cache for 24h. Force-refresh:

```
kiki-namespace refresh --namespace=acme
```

## Versioning discipline

- Patch (`1.0.0 → 1.0.1`): bug fixes; no API change
- Minor (`1.0.0 → 1.1.0`): backward-compatible features
- Major (`1.0.0 → 2.0.0`): breaking changes; coordinate with users

Avoid shipping major bumps casually. Users have to re-grant capabilities; old installs may fail.

## Deprecating

Mark a version deprecated in your namespace record and in the artifact's release notes. Users get a warning; the next minor release can drop deprecated functionality safely.

## Removing

If a vulnerability or licensing issue requires withdrawal:

```
kiki-pkg revoke kiki:acme/my-thing@1.0.0 --reason=vulnerability
```

Publishes a revocation entry. Devices warn and may auto-update to a fixed version.

## Acceptance criteria

- [ ] A new maintainer can ship their first artifact in <30 minutes
- [ ] Common issues have documented fixes
- [ ] CI reference workflow runs end-to-end

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/OCI-WORKFLOWS.md`
- `12-distribution/BUILD-SYSTEM.md`
- `06-sdk/PUBLISHING.md`
- `10-security/COSIGN-TRUST.md`
## Graph links

[[OCI-NATIVE-MODEL]]  [[NAMESPACE-MODEL]]  [[OCI-WORKFLOWS]]  [[BUILD-SYSTEM]]  [[COSIGN-TRUST]]
