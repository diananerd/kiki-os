---
id: image-composition
title: Image Composition
type: SPEC
status: draft
version: 0.0.0
implements: [build-pipeline]
depends_on:
  - upstream-choice
  - paradigm
depended_on_by:
  - boot-chain
last_updated: 2026-04-30
---
# Image Composition

## Purpose

Specify how Kiki OS images are built: the tooling, the configuration, the inputs, the outputs, the reproducibility guarantees. The build pipeline produces signed bootc OCI images that can be deployed atomically on any compatible Kiki device.

## Inputs

- `mkosi.conf` and supporting profile files describing the desired image.
- A snapshot pin to CentOS Stream 10 (timestamp).
- The Kiki Runtime sysext OCI artifact (built separately).
- Build-time secrets for cosign signing (kept in CI).
- The build pipeline's CI environment.

## Outputs

- A bootc OCI image tagged with the build version (e.g., `registry.kiki-os.dev/os/stable:1.0.0-amd64`).
- A signed cosign signature alongside the image.
- An optional Sigstore witness submission.
- A manifest list aggregating multi-arch images under one tag.

## Behavior

### Tooling

`mkosi` (version 25+) is the image build tool. mkosi composes a CentOS Stream 10 base image, layers Kiki content on top, and emits a bootc-compatible OCI image.

### Why mkosi

- systemd-native: maintained alongside systemd, integrates with sd-stub, sd-boot, sd-cryptenroll, sd-measure for PCR pre-computation.
- Reproducible: SOURCE_DATE_EPOCH support, deterministic file ordering.
- Multi-format output: can emit bootc OCI directly, or disk images, or directories.
- Multi-distro: accepts CentOS, Fedora, Debian, Arch, openSUSE as sources (provides a migration path).
- Active maintenance.

### mkosi configuration

The build is parameterized by `mkosi.conf` plus per-profile additions:

```ini
[Distribution]
Distribution=centos
Release=10
Mirror=https://snapshot-mirror.kiki-os.dev/stream10/<TIMESTAMP>/

[Output]
Format=disk
ManifestFormat=bootc
Bootable=yes

[Content]
Packages=
    kernel-core
    systemd
    systemd-boot
    systemd-resolved
    NetworkManager
    pipewire
    wireplumber
    podman
    crun
    bootc
    mesa-dri-drivers
    btrfs-progs
    cryptsetup
    tpm2-tools
    cage
    # ... explicit allowlist; no implicit dependencies pulled in beyond what's needed

[Validation]
SignExpectedPcr=yes

[Distribution]
Distribution=
```

The `Packages=` list is exhaustive. Any package not listed is excluded.

### Anti-bloat directives

mkosi composition includes explicit exclusions:

```
RemovePackages=
    bash-completion
    man-db
    info
    plymouth-*
    NetworkManager-bluetooth
    cups-*
    avahi-*
    GNOME-*
    KDE-*
    xfce-*
    xorg-x11-*

ExcludePaths=
    /usr/share/doc/
    /usr/share/man/
    /usr/share/info/
    /usr/share/locale/[!es]*
    /usr/share/locale/[!en]*
    /usr/share/X11/
```

Resulting image excludes documentation, man pages, info pages, non-{en,es} locales, X11 stack, GNOME/KDE/Xfce assumptions, printer support, Bluetooth GUI tooling, mDNS daemon (we use systemd-resolved).

### Layer stack

The final image is a layered OCI artifact:

```
Layer 0  CentOS Stream 10 base userspace (from snapshot)
Layer 1  Kernel + UKI signing
Layer 2  systemd configuration tweaks (Kiki defaults)
Layer 3  cage compositor + agentui binaries (sealed in)
Layer 4  Kiki Runtime sysext volumes
Layer 5  /etc/os-release branding (Kiki OS identity)
Layer 6  cosign verification keys for namespace registry
```

Layers 1–5 come from the Kiki build process. Layer 0 is upstream. Layer 6 is the trust bootstrap (the namespace registry's public key).

### Multi-arch

The build runs in parallel for each target architecture (x86_64, arm64; future riscv64). Each emits a separate OCI image. A manifest list aggregates them under one tag:

```
registry.kiki-os.dev/os/stable:1.0.0
  → linux/amd64 → sha256:aaaa...
  → linux/arm64 → sha256:bbbb...
```

bootc on the target device pulls the architecture-matching image automatically.

### Reproducibility

Two principles ensure builds are reproducible:

1. **Snapshot pinning.** mkosi resolves packages from a frozen snapshot.
2. **SOURCE_DATE_EPOCH.** All timestamps inside the image are set to the snapshot date.

Two builds from the same `mkosi.conf` and the same snapshot produce identical OCI image digests. Verified by `diffoscope` in CI.

### Signing

Each OCI image is signed by cosign with the Kiki release key:

```
cosign sign --key kiki-release.key registry.kiki-os.dev/os/stable:1.0.0-amd64
```

Optional Sigstore witness submission for transparency. The release key fingerprint is registered in the namespace registry under `kiki:core`.

### CI pipeline

```
1. CI worker pulls source repos (Kiki sources + mkosi.conf + Kiki Runtime sysext recipe).
2. Resolve snapshot timestamp from configured pin.
3. Run mkosi build for each target arch.
4. Verify reproducibility: rebuild and diff (sample run; full reproducibility check is periodic).
5. cosign sign each artifact.
6. Push to registry.kiki-os.dev/os/<channel>:<version>-<arch>.
7. Generate manifest list.
8. Optional: submit witness to Sigstore.
9. Update `latest` tag for the channel.
10. Notify subscribers (downstream rebuild triggers, OTA notification fan-out).
```

### Channels

Three release channels:

- `stable` — production releases. Cosign-signed, Sigstore-witnessed.
- `beta` — pre-release builds. Same signing.
- `nightly` — daily builds from main. Signed but not witness-submitted.

Each channel has its own tag in the OCI registry. bootc devices follow one channel.

## Interfaces

### CLI (build pipeline)

```
kiki-os-build --profile=desktop --arch=amd64 --channel=stable --version=1.0.0
```

This wraps mkosi with our standard parameters. Used in CI.

### Output specification

A successful build produces:

- `registry.kiki-os.dev/os/<channel>:<version>-<arch>` — the OCI image.
- `registry.kiki-os.dev/os/<channel>:<version>-<arch>.sig` — cosign signature.
- (Optional) Sigstore Rekor entry for the signature.

### Manifest list publication

```
registry.kiki-os.dev/os/<channel>:<version>
  → manifest list aggregating per-arch artifacts.
registry.kiki-os.dev/os/<channel>:latest
  → moves to the most recent release.
```

## State

### Persistent (per build)

- The OCI image and its signature in the registry.
- The mkosi build log (kept for diagnostics).
- The reproducibility report (diff vs prior identical-input rebuild).

### Non-persistent

- The mkosi build cache on the CI worker (regenerated per build).
- Intermediate layer files (cleaned up after push).

## Failure modes

| Failure | Response |
|---|---|
| Snapshot mirror unreachable | retry; if persistent, abort build and alert |
| Package not in snapshot | abort; investigate upstream change |
| mkosi config invalid | abort; clear error in build log |
| Signing key unavailable | abort; alert security team |
| Reproducibility check fails | abort; investigate non-determinism |
| Push to registry fails | retry; if persistent, abort |
| Sigstore witness unreachable | continue without witness; flag for retry |

## Performance contracts

- Cold build (no cache): <90s for amd64 desktop profile.
- Warm build (cached layers): <25s.
- Multi-arch parallel: bounded by slowest arch + 10s for manifest list publish.
- Reproducibility verification: <30s for a sampled build.
- Push to registry: bounded by network bandwidth.

## Acceptance criteria

- [ ] Build emits a bootc-compatible OCI image.
- [ ] Image boots successfully on reference hardware.
- [ ] Two builds from identical inputs produce identical digests.
- [ ] cosign signature verifies against the registered key.
- [ ] Multi-arch manifest list resolves correctly.
- [ ] Anti-bloat directives produce an image <800 MB without LLM models.
- [ ] No non-allowlisted packages are present in the image.
- [ ] `/etc/os-release` shows Kiki OS, not CentOS.

## Open questions

- Whether to use bootc-image-builder or stay with mkosi long-term.
- Where to host the snapshot mirror for resilience and bandwidth.
- Whether to support self-hosted build of custom images for organizations.

## References

- `02-platform/UPSTREAM-CHOICE.md`
- `02-platform/BOOT-CHAIN.md`
- `12-distribution/BUILD-SYSTEM.md`
- `12-distribution/SNAPSHOT-PINNING.md`
- `14-rfcs/0007-mkosi-image-build.md`
## Graph links

[[UPSTREAM-CHOICE]]  [[PARADIGM]]
