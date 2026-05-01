---
id: platform-index
title: Platform — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Platform

OS base, image composition, sandbox, storage, audio, display.

## Base and image

- `UPSTREAM-CHOICE.md` — CentOS Stream 10 bootc as operational upstream.
- `../specs/IMAGE-COMPOSITION.md` — mkosi pipeline for building the bootc image.
- `../specs/BOOT-CHAIN.md` — systemd-boot + UKI + sd-stub.
- `../specs/INIT-SYSTEM.md` — systemd as init/supervisor.
- `../specs/KERNEL-CONFIG.md` — required kernel features.

## Hardware

- `../specs/HARDWARE-MANIFEST.md` — signed hardware description.
- `../specs/HAL-CONTRACT.md` — HAL daemon interfaces.
- `../specs/HARDWARE-KILL-SWITCHES.md` — mic/camera/radio HAL enforcement.
- `../specs/DRM-DISPLAY.md` — Mesa, nvidia-open, NVK.
- `../specs/INFERENCE-ACCEL.md` — Vulkan via wgpu, optional CUDA.

## Network

- `../specs/NETWORK-STACK.md` — NetworkManager and per-app namespaces.
- `../specs/DNS-RESOLUTION.md` — systemd-resolved with DoT.

## Audio

- `../specs/AUDIO-STACK.md` — PipeWire 1.4+ and AEC integration.

## Sandbox and runtime

- `../specs/SANDBOX.md` — Landlock + seccomp + namespaces + cgroups.
- `../specs/CONTAINER-RUNTIME.md` — podman + crun + quadlet.

## Storage

- `../specs/STORAGE-LAYOUT.md` — read-only `/usr`, mutable `/var`, encrypted `/home`.
- `../specs/FILESYSTEM-BTRFS.md` — subvolumes for workspaces; snapshots.
