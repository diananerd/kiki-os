---
id: media-types
title: Media Types
type: SPEC
status: draft
version: 0.0.0
implements: [media-types]
depends_on:
  - oci-native-model
depended_on_by:
  - artifact-catalog
  - oci-workflows
last_updated: 2026-04-30
---
# Media Types

## Purpose

Catalog the OCI media types Kiki uses. Media types tell the registry and the client what kind of artifact each layer is. Kiki reserves a `vnd.kiki.*` namespace.

## Format

OCI media types follow the `application/vnd.<vendor>.<type>.<schema-version>+<format>` convention.

## Reserved Kiki types

### Container images

Use the standard OCI container image types — Kiki apps and bootc images are normal container images.

```
application/vnd.oci.image.manifest.v1+json
application/vnd.oci.image.layer.v1.tar+gzip
```

### Components

```
config: application/vnd.kiki.component.config.v1+toml
layer:  application/vnd.kiki.component.bundle.v1+tar+gzip
```

### Profiles

```
config: application/vnd.kiki.profile.config.v1+toml
layer:  application/vnd.kiki.profile.bundle.v1+tar+gzip
```

### Skills

```
config: application/vnd.kiki.skill.config.v1+toml
layer:  application/vnd.kiki.skill.bundle.v1+tar+gzip
```

### Tools

```
# WASM tool
config: application/vnd.kiki.tool.config.v1+toml
layer:  application/vnd.kiki.tool.wasm.v1+wasm

# Container tool (uses normal container types)
```

### Agent bundles (.kab)

```
config: application/vnd.kiki.agent.config.v1+toml
layer:  application/vnd.kiki.agent.bundle.v1+tar+gzip
```

### Models

```
config:  application/vnd.kiki.model.config.v1+toml
layer:   application/vnd.kiki.model.gguf.v1+binary
        (or .onnx.v1+binary, .safetensors.v1+binary, etc.)
```

### Prompts pack

```
config: application/vnd.kiki.prompts.config.v1+toml
layer:  application/vnd.kiki.prompts.bundle.v1+tar+gzip
```

### Sysext

```
container image with a Kiki-internal label
io.kiki.sysext = "true"
```

### Attestations

```
in-toto SBOM:
  application/vnd.in-toto+json
  predicateType: https://spdx.dev/Document
```

### Signatures

cosign signatures are stored under their standard media types:

```
application/vnd.dev.cosign.simplesigning.v1+json
```

## Versioning

The `.v1` suffix marks the schema version. Bumps to v2 add new media types; old types remain valid for legacy artifacts. Registries store both during transitions.

## Discovery

A registry's manifest list reveals the artifact type via the config's media type. The Kiki client examines the config first; if unknown, refuses (don't install random OCI artifacts).

## Tools

`oras push --artifact-type` sets the artifact type:

```
oras push registry.example/profiles/kid-friendly:1.0 \
    --config config.toml:application/vnd.kiki.profile.config.v1+toml \
    --artifact-type application/vnd.kiki.profile.config.v1+toml \
    bundle.tar:application/vnd.kiki.profile.bundle.v1+tar+gzip
```

## Anti-patterns

- Using `application/octet-stream` for known artifact types
- Reusing a media type across distinct artifact kinds
- Skipping the config for non-trivial artifacts (clients can't tell the kind)

## Acceptance criteria

- [ ] Each reserved type ships in the OS image's manifest
- [ ] Push/pull verified with the canonical types
- [ ] Versioning of media types supported (v1/v2 coexist)

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/ARTIFACT-CATALOG.md`
- `12-distribution/OCI-WORKFLOWS.md`
- OCI distribution-spec
- in-toto attestation framework
## Graph links

[[OCI-NATIVE-MODEL]]
