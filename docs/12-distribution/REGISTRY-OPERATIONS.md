---
id: registry-operations
title: Registry Operations
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - oci-native-model
  - namespace-model
  - cosign-trust
last_updated: 2026-04-30
---
# Registry Operations

## Purpose

Document running an OCI registry that serves Kiki artifacts. Most maintainers use existing registries (ghcr.io, docker.io, harbor); this guide is for those who want to host their own — community mirrors, organization-private registries, air-gapped deployments.

## Compatible registries

Any OCI distribution-spec implementation works:

- **distribution/distribution** (the reference; runs the docker hub)
- **harbor** (popular for self-hosting; has UI, replication, vulnerability scanning)
- **zot** (a lean OCI registry; OCI-artifact-friendly; recommended for Kiki)
- **GitHub Container Registry** (ghcr.io)
- **GitLab Container Registry**
- **Quay**, **Artifactory**, **Nexus**, **ACR**, **GCR**, **ECR**

We test against zot, harbor, distribution, and ghcr.

## Running zot for Kiki

A small zot config:

```toml
# /etc/zot/config.toml
[http]
address = "0.0.0.0"
port = 5000

[storage]
rootDirectory = "/var/lib/zot"

[log]
level = "info"

[extensions]
search = { enable = true }
sync = {
  enable = true
  registries = [
    { urls = ["https://ghcr.io"], pollInterval = "1h", ... }
  ]
}
```

Start with:

```
zot serve /etc/zot/config.toml
```

For TLS, put zot behind a reverse proxy (Caddy, Traefik) with Let's Encrypt.

## Required features

For Kiki:

- OCI distribution-spec v1.1+ (artifact-aware, supports `application/vnd.kiki.*`)
- Multi-arch manifest list support
- Referrers API (for signature/attestation discovery)
- Optional: vulnerability scanning, replication

If a registry doesn't support OCI artifacts (some older registries treat anything not a container image as invalid), that registry won't work.

## Storage

Plan for:

- ~5GB per release for the system base + sysexts + apps + components
- ~30-100GB per LLM model
- Multiple releases retained: multiply by retention

A Kiki Foundation public mirror runs into the TB range; community mirrors of selected namespaces fit in tens of GB.

## Replication

For high availability:

- zot's built-in sync extension
- harbor's replication
- distribution's pull-through cache

Mirrors should fetch and cache artifacts on demand, not push proactively (registries are read-mostly).

## Authentication

For private content: standard registry auth (basic auth, token auth, OIDC). Kiki devices configure auth via:

```
kiki registry login <registry-url>
```

Credentials stored in the user's keyring (KWallet / GNOME Keyring / homed-managed).

## Air-gapped operation

For air-gapped environments:

```
1. Pull all required artifacts on a connected machine
2. Re-tag for the air-gapped registry
3. Push (or copy by tarball)
4. Devices configured to use the air-gapped registry
```

The `kiki-pkg mirror` helper automates the bulk transfer.

## Garbage collection

Untagged digests accumulate. zot and harbor have GC commands; run periodically. Don't GC during a release window.

## Backups

Registry data is content-addressable; backup is a directory copy (tar, rsync, snapshot). Restore is also straightforward. Test backups regularly.

## Monitoring

Watch:

- Disk usage
- Pull rates and 4xx/5xx
- Sigstore log availability (for verification)
- Replication lag

Alert on anomalies; investigate spikes.

## Security

- Run on a hardened host
- TLS for all traffic
- Auth for write paths; read can be public for community mirrors
- Vulnerability scanning of stored images
- Rotate credentials regularly

## Compatibility testing

We provide a `kiki-registry-test` suite that exercises:

- Push of each Kiki media type
- Pull and digest verification
- Referrers API for signatures
- Manifest list for multi-arch

If your registry passes, you're a viable target for Kiki publishing.

## Anti-patterns

- Registry-side modifications to manifests (breaks signatures)
- Letting tags float (use immutable digests)
- No TLS
- No GC (disk fills)
- No backups

## Acceptance criteria

- [ ] Reference zot config runs
- [ ] kiki-registry-test passes
- [ ] Replication / sync works
- [ ] Air-gapped flow documented and tested
- [ ] Backups + restore tested

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/OCI-WORKFLOWS.md`
- `12-distribution/MEDIA-TYPES.md`
- OCI distribution-spec
