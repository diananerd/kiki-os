---
id: build-system
title: Build System
type: SPEC
status: draft
version: 0.0.0
implements: [build-system]
depends_on:
  - oci-native-model
  - oci-workflows
  - 0007-mkosi-image-build
  - cosign-trust
depended_on_by:
  - maintainer-guide
  - snapshot-pinning
last_updated: 2026-04-30
---
# Build System

## Purpose

Specify the build system that produces Kiki artifacts: mkosi for system images, cargo for Rust SDK and daemons, custom recipes for components/profiles/skills, cosign for signing. The build is deterministic, reproducible, and integrates Sigstore at every step.

## Components

```
mkosi          system images (base, sysext, app containers)
cargo           Rust SDK, daemons, tools
buildah/podman  general container images
oras            OCI artifact push for non-container types
cosign          signing
syft / spdx    SBOM generation
kiki-pkg       wrapper CLI
```

## kiki-pkg

The maintainer-facing wrapper. Detects the artifact kind from the source layout and dispatches to the right backend:

```
kiki-pkg init <kind>           scaffold a new project
kiki-pkg build [.]             build the artifact
kiki-pkg lint [.]              validate
kiki-pkg sign --key=...        sign
kiki-pkg push --to=...         push to registry
kiki-pkg release --tag=v1.0.0  full pipeline
kiki-pkg verify <id>            verify a published artifact
```

## mkosi for system images

Base and sysext images are built with mkosi from declarative configs:

```
mkosi/
├── mkosi.conf                  base config
├── mkosi.preset.bootc.conf     bootc-specific
├── mkosi.preset.sysext.conf    sysext-specific
└── packages.list                packages from upstream
```

mkosi consumes upstream snapshots and produces reproducible images. Output is an OCI image suitable for `bootc switch`.

## cargo for daemons

Rust workspaces under `daemons/` and `tools/`:

```
[workspace]
members = ["agentd", "policyd", "inferenced", "memoryd", "toolregistry"]

[profile.release]
lto = true
codegen-units = 1
strip = true
```

Reproducible: `SOURCE_DATE_EPOCH` set; build paths normalized.

## buildah/podman for app containers

App developers (and the Foundation for system apps) use buildah:

```
buildah bud --layers --tag <registry>/<id>:<ver> .
```

For reproducibility, the Containerfile uses pinned digests for base images and avoids non-deterministic operations (`apt-get update` without pinned mirrors is non-deterministic; we pin a snapshot).

## oras for non-container artifacts

For components, profiles, skills, agent bundles, prompts:

```
oras push <registry>/<id>:<ver> --config <config> <layer>
```

`kiki-pkg` wraps this with Kiki-specific media types.

## SBOM

`syft` runs against every artifact:

```
syft <registry>/<id>:<ver> -o spdx-json > sbom.spdx.json
cosign attest --predicate sbom.spdx.json --type spdxjson <registry>/<id>:<ver>
```

`kiki-pkg release` does this automatically.

## Reproducibility verification

The `kiki-pkg verify-rebuild` command:

```
kiki-pkg verify-rebuild --source=git@github.com/me/my-app.git \
  --commit=abc123 \
  --image=registry.example/my-app:1.0.0
```

Re-runs the build and compares digests. CI runs this on every release.

## Cache and offline builds

The build cache is content-addressed; reproducible builds cache reliably. For air-gapped environments, the offline build pulls a pre-prepared registry mirror.

## Cross-compile

Cargo cross-compile targets aarch64 and x86_64 first-class. For containers, buildah supports cross-arch via QEMU (slower) or cross-builders.

## CI

GitHub Actions, GitLab CI, and Drone are all supported via reference workflows. The workflows:

- Run lint
- Build
- Run tests + eval
- Verify reproducibility (re-build twice; compare)
- Sign keyless via OIDC
- Push
- Attest SBOM + provenance
- Update namespace registry

## Local development

```
kiki-pkg dev .                 hot-reload for development
kiki-pkg test .                run tests
kiki-pkg run .                 execute locally with stub services
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Reproducibility mismatch         | block release; investigate     |
| SBOM missing                     | release blocked                |
| Cross-arch build fails           | block; surface to maintainer   |
| Signature step fails             | release blocked; alert          |
| Lint warnings                    | release proceeds with warnings |
|                                  | (configurable; CI can fail)     |

## Acceptance criteria

- [ ] All artifact kinds build via `kiki-pkg`
- [ ] Reproducibility verified
- [ ] SBOM attached to every release
- [ ] Cosign keyed + keyless flows tested
- [ ] Cross-arch supported
- [ ] Local dev mode works

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/OCI-WORKFLOWS.md`
- `12-distribution/MAINTAINER-GUIDE.md`
- `02-platform/IMAGE-COMPOSITION.md`
- `02-platform/UPSTREAM-CHOICE.md`
- `10-security/COSIGN-TRUST.md`
- `14-rfcs/0007-mkosi-image-build.md`
## Graph links

[[OCI-NATIVE-MODEL]]  [[OCI-WORKFLOWS]]  [[0007-mkosi-image-build]]  [[COSIGN-TRUST]]
