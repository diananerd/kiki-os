---
id: inference-accel
title: Inference Acceleration
type: SPEC
status: draft
version: 0.0.0
implements: [inference-accel-stack]
depends_on:
  - drm-display
  - hardware-manifest
depended_on_by:
  - inference-engine
  - render-api
last_updated: 2026-04-30
---
# Inference Acceleration

## Purpose

Specify how local LLM inference uses available hardware acceleration: Vulkan as the cross-vendor primitive, optional CUDA fast path on NVIDIA, fallback to CPU.

## Behavior

### Vulkan as portable substrate

Vulkan compute is the cross-vendor portable acceleration primitive. Mesa exposes Vulkan on Intel, AMD, and NVIDIA (via NVK). llama.cpp has a mature Vulkan backend, within 10–20% of CUDA on consumer GPUs in 2026.

`wgpu` (Rust) wraps Vulkan/Metal/DX12 and is used by agentui's canvas. For inference, llama.cpp accesses Vulkan directly via the kernel driver.

### CUDA fast path on NVIDIA

For NVIDIA users wanting the last 10–20% of throughput, CUDA is available via the `cudarc` Rust crate. inferenced detects NVIDIA hardware and offers CUDA as a backend option.

CUDA requires:

- nvidia-open kernel modules loaded.
- CUDA runtime libraries in the OS image (or via container side-load).
- The model loaded with CUDA-compatible quantization.

CUDA is opt-in. Default is Vulkan for portability.

### ROCm for AMD (limited)

ROCm via HIP is technically possible on AMD; usually rougher than Vulkan in 2026. We don't ship ROCm by default. Vulkan path is preferred.

### Metal for Apple Silicon

Apple Silicon (M1/M2/M3) has Metal as native. llama.cpp's Metal backend is excellent. When Kiki runs on Apple Silicon (future hardware class), Metal is the fast path.

In v0, Apple Silicon support is via arm64 desktop class. Metal acceleration available; Vulkan via MoltenVK is not used.

### CPU fallback

If no GPU acceleration is available (or GPU is busy or memory-limited), llama.cpp falls back to CPU inference. AVX2/AVX512 (x86) and NEON (ARM) provide vectorization.

CPU inference is slower (~5–10x slower than GPU on consumer hardware) but always functional.

### Memory budget

LLM inference consumes significant GPU VRAM:

- Llama 3.3 8B Q4_K_M: ~5.5 GB VRAM (or ~5.5 GB system RAM if CPU-only).
- Qwen 2.5 14B Q4_K_M: ~9 GB VRAM.
- Granite Guardian 3.2 5B (always-loaded arbiter): ~3.2 GB.

The hardware manifest's `gpu.vram_mb` informs the inference router about available capacity. If insufficient VRAM for the requested model, the router falls back to CPU or a smaller model.

### Concurrent workloads

The GPU is shared between:

- LLM inference (llama.cpp).
- agentui rendering (wgpu via Vulkan).
- Tier-full app rendering (apps' wgpu).

llama.cpp's Vulkan backend supports preemption: when agentui needs to render a frame, the inference yields briefly. In practice, with a discrete GPU and reasonable workload, both can run with minimal interference.

For very heavy workloads (e.g., a video editor + LLM inference), users may need to choose: pause inference while editing, or run inference on CPU.

### Per-app GPU access

Apps requesting GPU access declare `device.gpu.use` capability. Their container is given a bind mount of `/dev/dri/renderD128` (compute-only, no display).

The capability gate evaluates:

- Whether the hardware has a GPU (manifest check).
- Whether the user has granted `device.gpu.use` to this app.
- Whether the GPU has capacity (informational; not enforced).

### KMS-based virtualization

Vulkan does not provide GPU isolation; multiple apps with GPU access share the same device. We rely on:

- Each app having its own VkInstance/VkDevice.
- Trust that apps don't intentionally interfere with each other.
- Driver-level fault recovery (GPU hang detection, context reset).

This is a known limitation. Hardware-virtualized GPUs (SR-IOV) are future work.

### Performance numbers

On reference hardware (M2 Pro, 16GB unified):

- Llama 3.3 8B Q4_K_M: ~38 tok/s decode, ~180ms first-token.
- Qwen 2.5 14B Q4_K_M: ~22 tok/s decode, ~280ms first-token.

On reference hardware (RTX 4060, Vulkan):

- Llama 3.3 8B Q4_K_M: ~75 tok/s.
- Qwen 2.5 14B Q4_K_M: ~45 tok/s.

CUDA fast path adds ~10–20% on NVIDIA.

## Interfaces

### Programmatic

inferenced uses `llama-cpp-2` for the engine. The engine selects backend at runtime:

```rust
let backend = match (manifest.gpu.vendor, user_pref) {
    ("nvidia", "cuda") => Backend::Cuda,
    ("nvidia", _) => Backend::Vulkan,
    ("amd", _) => Backend::Vulkan,
    ("intel", _) => Backend::Vulkan,
    ("apple", _) => Backend::Metal,
    _ => Backend::Cpu,
};
```

### CLI

```
agentctl inference accel             # show backend in use
agentctl inference set-backend <b>   # change backend (config)
```

## State

### Persistent

- User preferences for backend selection.

### In-memory

- Loaded models with their backend context.

## Failure modes

| Failure | Response |
|---|---|
| GPU driver crash | inferenced detects; falls back to CPU; alerts user |
| Insufficient VRAM | router refuses or downgrades model; alerts |
| GPU hang | reset; resume |
| Backend crash mid-inference | retry once; if persistent, fall back |

## Performance contracts

- Backend selection: <10ms at startup.
- Model load: bounded by I/O (NVMe) and VRAM transfer; typically 2–10s.

## Acceptance criteria

- [ ] Vulkan backend works on Intel, AMD, NVIDIA.
- [ ] CUDA optional on NVIDIA.
- [ ] CPU fallback always available.
- [ ] inference router selects backend based on manifest + capability.
- [ ] GPU device exposed to apps with capability.

## Open questions

- When to evaluate ROCm seriously for AMD.
- SR-IOV or similar GPU virtualization for stricter app isolation.

## References

- `02-platform/DRM-DISPLAY.md`
- `02-platform/HARDWARE-MANIFEST.md`
- `03-runtime/INFERENCE-ENGINE.md`
- `03-runtime/INFERENCE-MODELS.md`
## Graph links

[[DRM-DISPLAY]]  [[HARDWARE-MANIFEST]]
