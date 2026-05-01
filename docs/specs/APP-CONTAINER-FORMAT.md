---
id: app-container-format
title: App Container Format
type: SPEC
status: draft
version: 0.0.0
implements: [app-container-format]
depends_on:
  - sdk-overview
  - container-runtime
  - oci-native-model
depended_on_by:
  - app-lifecycle
  - app-runtime-modes
  - publishing
last_updated: 2026-04-30
---
# App Container Format

## Purpose

Specify how a Kiki app is packaged: an OCI container image (rootfs + manifest + signature) with conventions for the Kiki manifest, declared capabilities, surface registration, and entrypoints.

## Why a container

- OCI is universal; podman/quadlet handle isolation
- Sandbox + seccomp + cgroups via the runtime, not per-app code
- Reproducible builds via mkosi or buildah
- Signed and verified end-to-end with cosign + Sigstore

## Layout inside the image

```
/                                     standard rootfs
├── usr/bin/<entrypoint>               main binary or script
├── etc/kiki/manifest.toml             Kiki app manifest
├── etc/kiki/capnp/<schemas>.capnp     tool schemas if any
├── etc/kiki/recipes/                  shipped procedural recipes
├── etc/kiki/views/                    UI surface declarations
└── ...                                language-specific runtime
```

The `manifest.toml` is the *only* metadata Kiki reads to install the app; everything else is implementation.

## manifest.toml

```toml
id = "kiki:apps/example-music"
version = "1.2.0"
authors = ["Acme"]
license = "Apache-2.0"
description = "A simple music player."
homepage = "https://acme.example/music"
runtime_mode = "interactive_service"   # see APP-RUNTIME-MODES.md

[entrypoint]
exec = ["/usr/bin/example-music"]

[capabilities_required]
audio_play = true
network_outbound_hosts = [
    "https://api.example.com",
]
storage_user_dir = true
focus_publish_domain = "media"

[capabilities_optional]
mic_record = true                    # user can grant later

[ui_views]
now-playing = { provides = ["media.controls"], size_class = "flex" }
queue       = { provides = ["media.controls"], size_class = "flex" }

[tools]
# tools the app contributes for the agent to dispatch
play   = { schema = "schemas/play.capnp:Play",   risk = "safe" }
search = { schema = "schemas/search.capnp:Search", risk = "safe" }

[recipes]
# procedural recipes shipped with this app
# they appear under /etc/kiki/recipes and are loaded at install
"morning-music" = "recipes/morning-music.md"

[focus]
domain = "media"
publishes = ["state", "trackTitle", "artist", "position", "duration"]

[lifecycle]
on_install = "/usr/bin/example-music --install-hook"
on_uninstall = "/usr/bin/example-music --uninstall-hook"
```

The manifest is parsed at install; install fails on schema errors or missing referenced files.

## Image labels

OCI image labels mirror parts of the manifest for fast inspection without unpacking:

```
org.opencontainers.image.title=example-music
org.opencontainers.image.version=1.2.0
io.kiki.id=kiki:apps/example-music
io.kiki.runtime_mode=interactive_service
io.kiki.required_capabilities=audio.play,network.outbound,...
```

## Sandbox

The runtime applies a sandbox profile derived from the manifest:

- **Landlock**: write only `/var/lib/kiki/apps/<id>/` and `/run/user/<uid>/<id>/`
- **seccomp**: a default-deny profile; allowed syscalls per the runtime mode
- **AppArmor**: label `kiki-app-<id>`; restricts socket reachability
- **cgroup**: in the app's slice; CPU/memory caps per profile
- **namespaces**: PID, IPC, UTS, mount; share network with host only when capability declared
- **No setuid binaries**

The capability gate then enforces per-call grants.

## Image content rules

- Static linking preferred when feasible
- No setuid; no NOPASSWD sudo files
- No bundled package manager binaries
- `/etc/kiki/manifest.toml` must be present and parsable
- Must be reproducible: building the same source twice yields identical image digests

## Signing

The image and manifest are signed with cosign:

```
cosign sign --key=<key> <registry>/<image>:<tag>
cosign verify --certificate-identity=... <registry>/<image>:<tag>
```

Sigstore transparency log entry is required. Verification happens at install and at start.

## Versioning

Semver. Major bumps invalidate caches and force re-grant of capabilities the user previously approved if the new version requires more.

## Multi-arch

Multi-arch images via OCI manifest list (aarch64, x86_64). One image artifact references the right blob per device.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Manifest missing                 | install rejected               |
| Manifest invalid                 | install rejected with diagnostic|
| Signature invalid                | install refused                 |
| Capability declaration mismatches| install refused                 |
| Tool schema doesn't compile      | install refused                 |
| Reproducibility check fails      | maintainer task; CI gate       |

## Acceptance criteria

- [ ] Apps install only with valid signed manifests
- [ ] Sandbox profile derived from manifest
- [ ] Image labels match manifest fields
- [ ] Multi-arch supported
- [ ] Reproducible builds verified

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/APP-RUNTIME-MODES.md`
- `06-sdk/APP-LIFECYCLE.md`
- `06-sdk/PUBLISHING.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `02-platform/SANDBOX.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `10-security/COSIGN-TRUST.md`
## Graph links

[[SDK-OVERVIEW]]  [[CONTAINER-RUNTIME]]  [[OCI-NATIVE-MODEL]]
