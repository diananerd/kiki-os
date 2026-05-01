---
id: rfcs-index
title: RFCs and ADRs — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# RFCs and ADRs

Two governance artifacts live here:

- **RFCs** — proposals for major changes. Heavier process, discussion period, open until accepted or rejected.
- **ADRs** — Architectural Decision Records. Lighter process, document decisions already made.

See `RFC-PROCESS.md` and `ADR-PROCESS.md` for workflows.

## RFCs

(none yet — RFCs receive sequential RFC-NNNN numbers when accepted)

## ADRs

The full list is below. ADRs are numbered sequentially; numbers are stable once assigned.

### Foundational (paradigm-defining)

- `0001-appliance-os-paradigm.md` — Kiki OS as appliance OS for agentic computing.
- `0002-oci-native-distribution.md` — All artifacts are signed OCI artifacts.
- `0003-cosign-sigstore-trust.md` — cosign per-namespace + opt-in Sigstore witness.
- `0004-namespace-registry.md` — `kiki:<namespace>/<name>@<version>` identity.
- `0005-no-package-manager-user-facing.md` — No apt/dnf/pacman in the user surface.

### Upstream and base

- `0006-centos-stream-bootc-upstream.md`
- `0007-mkosi-image-build.md`
- `0008-systemd-init.md`
- `0009-systemd-boot-uki-pcr.md`
- `0010-btrfs-var-subvolumes.md`
- `0011-luks2-cryptenroll-homed.md`
- `0012-podman-quadlet-app-runtime.md`
- `0013-cage-kiosk-compositor.md`

### Stack core

- `0014-rust-only-shell-stack.md`
- `0015-slint-shell-toolkit.md`
- `0016-servo-html-engine.md`
- `0017-wgpu-canvas-render.md`
- `0018-accesskit-accessibility.md`
- `0019-libinput-gestures.md`
- `0020-capnp-rpc-tool-dispatch.md`
- `0021-nats-service-bus.md`
- `0022-iceoryx-data-plane.md`
- `0023-zbus-dbus-integration.md`

### Inference and voice

- `0024-llamacpp-inference-engine.md`
- `0025-microWakeWord.md`
- `0026-whisper-turbo-stt.md`
- `0027-kokoro-tts.md`
- `0028-pipewire-audio.md`
- `0029-bge-m3-jina-reranker.md`

### Memory

- `0030-lancedb-episodic.md`
- `0031-cozodb-semantic-graph.md`
- `0032-redb-capability-grants.md`
- `0033-duckdb-metrics.md`
- `0034-git-identity-versioning.md`

### Security and crypto

- `0035-rustls-aws-lc-rs.md`
- `0036-ct-merkle-audit-chain.md`
- `0037-landlock-primary-apparmor-backstop.md`
- `0038-camel-trifecta-isolation.md`

### Agentic patterns

- `0039-five-tier-compaction.md`
- `0040-arbiter-classifier-two-stage.md`
- `0041-coordinator-worker-isolation.md`
- `0042-sidechain-jsonl-subagents.md`
- `0043-workspaces-model.md`

### Future and alternatives

- `0098-mistralrs-runner-up-documented.md`
- `0099-future-distribution-pivots.md`
