---
id: cosign-trust
title: cosign Trust Model
type: SPEC
status: draft
version: 0.0.0
implements: [cosign-trust]
depends_on:
  - cryptography
  - namespace-model
depended_on_by:
  - backend-contract
  - build-system
  - component-oci-format
  - component-registry
  - device-auth
  - maintainer-guide
  - model-lifecycle
  - namespace-model
  - oci-native-model
  - oci-workflows
  - ota-distribution
  - profile-oci-format
  - publishing
  - registry-operations
  - sigstore-witness
last_updated: 2026-04-30
---
# cosign Trust Model

## Purpose

Specify how cosign is used for signing and verifying OCI artifacts in Kiki: per-namespace public keys, key registration in the namespace registry, rotation, revocation, and the verification flow on the device.

## Behavior

### Per-namespace keys

Each Kiki namespace has a registered cosign public key. The trust unit is the namespace, not individual artifacts:

```
kiki:core/*           signed by Kiki release key
kiki:dev/*            signed by Kiki release key
kiki:meta/*           signed by Kiki release key
kiki:acme/*           signed by acme's key
kiki:foo/*            signed by foo's key
```

A namespace is registered with:

- Its canonical OCI registry URL.
- Its cosign public key fingerprint.
- Optional metadata (KYC level, contact, registration date).

The namespace registry exposes this via the API in `09-backend/REGISTRY-PROTOCOL.md`.

### Key generation and storage

Maintainers generate their cosign keys:

```
cosign generate-key-pair
```

The private key is kept securely (offline, hardware token, or CI signing service like GitHub Actions OIDC). The public key is registered with the namespace registry at namespace creation.

For Kiki internal namespaces (`kiki:core`, `kiki:dev`, `kiki:meta`), the release key is held by the Kiki maintainers and used in the build pipeline.

### Signing flow

When a maintainer publishes an artifact:

```
1. Build the OCI artifact (image, sysext, app container, etc.).
2. cosign sign with the namespace's private key:
     cosign sign --key acme.key registry.acme.dev/notes:1.2.0
3. Push the signed artifact to the registry.
4. (Optional) Submit signature to Sigstore Rekor for transparency.
```

The signed artifact's digest is the canonical reference. Tags (`1.2.0`, `latest`) point to specific digests.

### Verification flow

When the device pulls an artifact:

```
1. Resolve identity → namespace registry → registry URL + cosign key fingerprint.
2. Pull the artifact from the registry.
3. cosign verify:
     cosign verify --key acme.pub registry.acme.dev/notes@sha256:...
4. If signature valid → install.
5. If signature invalid → reject; alert user.
6. (Optional) Verify against Sigstore Rekor for transparency.
```

Verification happens on every pull. Cached artifacts are not re-verified unless the cache is invalidated.

### Local trust storage

The device stores trusted public keys at:

```
/etc/kiki/cosign-keys/<namespace>.pub
```

These are populated from the namespace registry on first install of an artifact from that namespace, with a trust prompt to the user.

### Trust prompts

When agentctl encounters a namespace not yet trusted:

```
agentui shows:
  "Trust acme.dev for the kiki:acme/* namespace?
   Public key fingerprint: <hex>
   Canonical registry: registry.acme.dev
   Sigstore witness: opt-in
  
   [ Trust ]  [ Trust this artifact only ]  [ Reject ]"
```

User decision is recorded:

- **Trust**: key persisted; future installs from this namespace verify silently.
- **Trust this artifact only**: install proceeds; key not persisted; next install prompts again.
- **Reject**: install aborted.

### Key rotation

Maintainers rotate their key:

1. Generate new key pair.
2. Sign the new public key with the old private key (creates a rotation certificate).
3. Publish the rotation cert to the namespace registry.
4. Sign new artifacts with the new key.

When a device first encounters an artifact signed with the new key:

- Verify the rotation cert's signature against the old key (which we trust).
- If valid, accept the new key. Show the user a notification: "acme rotated their key on <date>; new fingerprint <hex>."
- Persist the new key.

This allows transparent rotation without manual user intervention.

### Key revocation

Maintainers revoke a key:

1. Publish a revocation entry to Sigstore Rekor (signed with the revoked key).
2. The namespace registry reflects the revocation.
3. Devices polling the registry learn of the revocation.
4. Subsequent artifacts signed by the revoked key are rejected.

For the user, agentui shows: "acme's key was revoked. <list of affected installed artifacts>. Suggest update or remove."

### Sigstore Rekor (transparency log)

Optional. Maintainers can submit signatures to Rekor for non-repudiation:

```
cosign sign --key acme.key --rekor-url https://rekor.sigstore.dev ...
```

Devices verify against Rekor when configured to do so:

```
cosign verify --certificate-identity acme --rekor-url https://rekor.sigstore.dev ...
```

This provides a public transparency log: anyone can verify that acme signed a specific artifact at a specific time.

Witness signing on the audit log (per `10-security/SIGSTORE-WITNESS.md`) is similar: it's the inverse, where Kiki's audit log heads are submitted to a witness for transparency.

### Keyless signing (future)

cosign supports keyless signing via OIDC (Sigstore Fulcio). v0 uses keys; keyless can be added in v1 for maintainers who prefer not to manage keys directly.

### Security properties

- **Forgery**: cosign signature cannot be forged without the private key.
- **Tampering**: any modification to the artifact invalidates the signature.
- **Identity**: signatures are bound to a specific namespace; cross-namespace forgery requires controlling the namespace registry's signing chain.
- **Revocation**: in-flight artifacts can be revoked via Rekor publication.

### What this does NOT protect against

- A compromised maintainer's private key — until rotation/revocation, attacker can sign anything as that namespace.
- A compromised namespace registry — could redirect to a malicious registry; mitigated by signing of the registry's own responses.
- A user who opts out of cosign verification — possible in developer mode, with explicit warning.

## Interfaces

### Programmatic

```rust
pub fn verify_artifact(image: &str, namespace: &Namespace) -> Result<VerificationStatus>;
pub fn add_trusted_key(namespace: &Namespace, key: &PublicKey) -> Result<()>;
pub fn revoke_trusted_key(namespace: &Namespace) -> Result<()>;
pub fn rotation_cert(namespace: &Namespace) -> Result<Option<RotationCert>>;
```

### CLI

```
agentctl trust list                            # show trusted namespaces
agentctl trust show <namespace>                # show key fingerprint, status
agentctl trust add <namespace> --key <pubkey>  # manual trust
agentctl trust revoke <namespace>              # remove trust
agentctl trust verify <oci-url>                # one-shot verification
```

cosign CLI is also available in developer mode for direct manipulation.

## State

### Persistent

- /etc/kiki/cosign-keys/<namespace>.pub.
- Namespace registry cache.
- Revocation list.

### In-memory

- Recent verification cache.

## Failure modes

| Failure | Response |
|---|---|
| Signature invalid | reject install; alert user |
| Signature missing | reject; alert |
| Key revoked | reject; alert; suggest update |
| Rotation cert invalid | reject; alert |
| Namespace not registered | trust prompt to user |
| Sigstore Rekor unreachable | optional; if mandatory, reject |

## Performance contracts

- cosign verify: <100ms typical for a single artifact.
- Trust lookup: <2µs (file read, cached).

## Acceptance criteria

- [ ] Every OCI artifact pulled is cosign-verified.
- [ ] Per-namespace keys stored and consulted.
- [ ] Trust prompts on first encounter with a namespace.
- [ ] Key rotation flow works (rotation cert verifies, new key trusted).
- [ ] Key revocation flow works (revoked key rejected).
- [ ] Sigstore Rekor witness submission is opt-in.

## References

- `10-security/CRYPTOGRAPHY.md`
- `10-security/SIGSTORE-WITNESS.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `09-backend/REGISTRY-PROTOCOL.md`
- `14-rfcs/0003-cosign-sigstore-trust.md`
- `14-rfcs/0004-namespace-registry.md`
