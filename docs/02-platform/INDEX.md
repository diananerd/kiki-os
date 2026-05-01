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
- `IMAGE-COMPOSITION.md` — mkosi pipeline for building the bootc image.
- `BOOT-CHAIN.md` — systemd-boot + UKI + sd-stub.
- `INIT-SYSTEM.md` — systemd as init/supervisor.
- `KERNEL-CONFIG.md` — required kernel features.

## Hardware

- `HARDWARE-MANIFEST.md` — signed hardware description.
- `HAL-CONTRACT.md` — HAL daemon interfaces.
- `HARDWARE-KILL-SWITCHES.md` — mic/camera/radio HAL enforcement.
- `DRM-DISPLAY.md` — Mesa, nvidia-open, NVK.
- `INFERENCE-ACCEL.md` — Vulkan via wgpu, optional CUDA.

## Network

- `NETWORK-STACK.md` — NetworkManager and per-app namespaces.
- `DNS-RESOLUTION.md` — systemd-resolved with DoT.

## Audio

- `AUDIO-STACK.md` — PipeWire 1.4+ and AEC integration.

## Sandbox and runtime

- `SANDBOX.md` — Landlock + seccomp + namespaces + cgroups.
- `CONTAINER-RUNTIME.md` — podman + crun + quadlet.

## Storage

- `STORAGE-LAYOUT.md` — read-only `/usr`, mutable `/var`, encrypted `/home`.
- `FILESYSTEM-BTRFS.md` — subvolumes for workspaces; snapshots.
