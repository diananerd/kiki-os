---
id: component-oci-format
title: Component OCI Format
type: SPEC
status: draft
version: 0.0.0
implements: [component-oci-format]
depends_on:
  - component-registry
  - oci-native-model
  - cosign-trust
depended_on_by:
  - publishing
last_updated: 2026-04-30
---
# Component OCI Format

## Purpose

Specify the on-disk layout of a third-party UI component bundle (per `COMPONENT-REGISTRY.md`) packaged as an OCI artifact: file layout, manifest, signing, validation rules.

## OCI artifact shape

A component is an OCI artifact (not a runnable container; an OCI artifact with a Kiki-specific media type):

```
artifact descriptor
  config: application/vnd.kiki.component.config.v1+toml
  layers:
    - application/vnd.kiki.component.bundle.v1+tar
```

The single layer is a tarball of the component bundle.

## Bundle layout

```
component/
├── manifest.toml                    component manifest
├── module.slint                     Slint markup
├── assets/
│   ├── icon.png
│   └── ...
├── tokens-overrides.toml            optional token overrides
└── README.md                         human-readable
```

## Manifest

```toml
id = "kiki:components/voice-waveform"
version = "1.0.0"
authors = ["Acme UI"]
license = "MIT"
description = "A waveform visualization for voice sessions."
component_type = "block"               # block | inline | inspector

[a11y]
role = "image"
description_required = true

[size]
default = "medium"
min_width = 200
min_height = 80

[capabilities_required]
audio_metadata_read = false

[exports]
slint_module = "VoiceWaveform"

[props]
session_id = { type = "string", required = true }
color_accent = { type = "token", default = "color.accent.primary" }

[events]
clicked = { type = "void" }
```

## Validation

The toolregistry validates at install:

- Manifest schema valid
- Slint module compiles in a sandboxed builder
- A11y role present
- Token references resolve
- No restricted APIs used
- Render in a sandboxed test harness with synthetic props
- Reproducible build hash matches

## Restricted APIs

A component cannot use:

- `import "std"` for filesystem, network, threading
- Direct GPU access (renders only via Slint primitives)
- Time / RNG without going through host-provided callbacks
- Cross-component reach

The Slint compiler in the validator uses a constrained module resolution that only allows the public component API.

## Signing

cosign-signed; Sigstore log entry required. Same flow as apps.

## Versioning

Semver. agentui can hold multiple versions concurrently; apps reference by `id@version`.

## Build

A reference build pipeline:

```
1. Compile Slint module in sandbox
2. Bundle tar
3. oras push to registry
4. cosign sign --key=<...> ref
5. cosign attach sigstore --certificate=...
```

See `PUBLISHING.md`.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Validation fails                 | reject install                 |
| Signature invalid                | reject install                 |
| Token reference unresolved       | reject install                 |
| Reproducibility fail             | reject (CI only)               |

## Acceptance criteria

- [ ] OCI artifact pulls and unpacks
- [ ] Manifest validates against schema
- [ ] Slint module compiles in sandbox
- [ ] Signature + Sigstore verified
- [ ] Sandbox-test renders without errors

## References

- `07-ui/COMPONENT-REGISTRY.md`
- `07-ui/COMPONENT-LIBRARY.md`
- `07-ui/DESIGN-TOKENS.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/MEDIA-TYPES.md`
- `10-security/COSIGN-TRUST.md`
