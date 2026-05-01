---
id: drm-display
title: DRM and Display
type: SPEC
status: draft
version: 0.0.0
implements: [display-stack]
depends_on:
  - kernel-config
  - hardware-manifest
depended_on_by:
  - compositor
  - inference-accel
  - render-api
  - shell-overview
last_updated: 2026-04-30
---
# DRM and Display

## Purpose

Specify the display and graphics stack: Mesa drivers, the NVK Vulkan driver for NVIDIA, the open `nvidia-open` kernel modules path, and how cage as the compositor consumes DRM/KMS.

## Behavior

### Mesa for Intel, AMD, and (via NVK) NVIDIA

Mesa is the open-source graphics driver suite. We use:

- **i965/iris** for Intel iGPUs.
- **RadeonSI** for AMD GPUs (RDNA, GCN families).
- **NVK** (in-Mesa Vulkan driver) for NVIDIA GPUs in conjunction with the open kernel modules.

Mesa 25+ ships with NVK production-quality (since Mesa 24, GA in 25). Vulkan 1.3+ baseline.

### NVIDIA: open kernel modules + NVK

The recommended NVIDIA path in 2026:

- **`nvidia-open`** kernel modules (GSP-firmware-based, Turing+). The default for NVIDIA on CentOS Stream 10.
- **NVK** as the Vulkan driver in Mesa.

Older NVIDIA hardware (pre-Turing) falls back to `nouveau` with NVK.

The proprietary NVIDIA blob is not used by default. It is available for users who explicitly opt in (developer mode), but it complicates the appliance shape (closed-source modules, signed kernel image considerations).

### Wayland-only

Kiki runs Wayland exclusively via cage. There is no X11 server. Apps that require X11 are out of scope (legacy compatibility is not a v0 goal).

### DRM / KMS

The kernel's DRM (Direct Rendering Manager) and KMS (Kernel Mode Setting) are used by:

- cage compositor for scanout and input.
- agentui's wgpu (via Vulkan, via DRM).
- Tier-full apps that produce GPU-rendered surfaces (DMA-BUF passthrough to agentui).

DRM device nodes:

- `/dev/dri/card0` — primary display device.
- `/dev/dri/renderD128` — render-only (compute, no display).

Cage has access to both. Apps with `device.gpu.use` capability get a bind mount of `renderD128` only (no display access; they render to buffers that agentui composites).

### Multi-GPU

Devices with multiple GPUs (e.g., laptop with iGPU + dGPU):

- The integrated GPU drives the display.
- The discrete GPU is available for compute (LLM inference, app rendering).
- The inference router can target a specific device.

### Display configuration

cage reads the hardware manifest to know which displays are configured. Hot-plug events from DRM/KMS reconfigure dynamically.

```
manifest declares: 1 primary display 2560x1440
boot: cage initializes with that resolution
hot-plug: external display attached
   → cage receives uevent
   → reconfigures, agentui canvas adapts via design tokens
```

### Refresh rate

cage runs at the display's native refresh rate (60Hz, 90Hz, 120Hz, 144Hz). agentui's render targets the same rate. wgpu manages the swap chain.

### HiDPI

Displays with high pixel density (>200 dpi) trigger HiDPI mode in agentui's design tokens (font scale, touch target scale). The hardware manifest's `hdpi` flag drives this.

### HDR / color management

v0 does not support HDR. Standard sRGB color space. v1 may add HDR for displays that support it.

### Inference acceleration via Vulkan

Vulkan compute is the cross-vendor primitive for accelerating LLM inference (`02-platform/INFERENCE-ACCEL.md`). Mesa+NVK on NVIDIA, RadeonSI on AMD, iris on Intel all expose Vulkan compute.

llama.cpp's Vulkan backend benefits from this — within 10–20% of CUDA on consumer GPUs in 2026.

CUDA fast path (via cudarc) is opt-in for NVIDIA users wanting the last bit of performance.

### Hardware-accelerated video decode

For the rare app that wants hardware-accelerated video decode (e.g., a video player), VA-API (Intel/AMD) or NVENC/NVDEC (NVIDIA) are available via standard Linux interfaces. The container exposes the decode device with `device.video.decode` capability.

## Interfaces

### Programmatic

agentui's compositor integration uses `wayland-rs` and `wgpu` to talk to DRM/KMS. Apps that render via wgpu use `wgpu` directly; their containers have render-only access to the GPU.

### CLI

```
agentctl display status            # current display config
agentctl display refresh-rate      # current rate
agentctl display rotate <degrees>  # capability-gated rotation
```

## State

### Persistent

- Display preferences (rotation, brightness) per user.

### In-memory

- DRM modeset state.
- Per-display configuration in cage.

## Failure modes

| Failure | Response |
|---|---|
| GPU driver fails | system continues with software rendering (degraded) |
| Display unplugged | cage reconfigures; surfaces migrate to remaining displays |
| Hot-plug to unknown display | use safe defaults; alert |
| GPU hang | reset; agentui reconnects |

## Performance contracts

- Frame budget: 16.7ms (60Hz), 11.1ms (90Hz), 8.3ms (120Hz), 6.9ms (144Hz).
- Mode switch on hot-plug: <500ms.
- GPU hang detection and reset: <2s.

## Acceptance criteria

- [ ] Mesa 25+ active.
- [ ] NVK Vulkan available on NVIDIA hardware.
- [ ] cage drives DRM/KMS.
- [ ] Apps with GPU capability access renderD128.
- [ ] Hot-plug works.
- [ ] HiDPI tokens applied on appropriate displays.

## Open questions

- When to support HDR.
- Whether to ship NVIDIA proprietary blob path or stay open-only.

## References

- `02-platform/KERNEL-CONFIG.md`
- `02-platform/INFERENCE-ACCEL.md`
- `02-platform/HARDWARE-MANIFEST.md`
- `07-ui/COMPOSITOR.md`
## Graph links

[[KERNEL-CONFIG]]  [[HARDWARE-MANIFEST]]
