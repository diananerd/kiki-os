---
id: 0024-llamacpp-inference-engine
title: llama.cpp via llama-cpp-2 as Inference Engine
type: ADR
status: draft
version: 0.0.0
depends_on: [0014-rust-only-shell-stack]
last_updated: 2026-04-29
---
# ADR-0024: llama.cpp via llama-cpp-2 as Inference Engine

## Status

`accepted`

## Context

Local inference is core to Kiki. We need an engine that runs LLMs (Llama 3.3 8B Q4 default), supports CPU, Vulkan, CUDA, ROCm, and Apple Silicon, has good tool-calling behavior, supports KV cache reuse, and is deployable as a single-binary daemon. Candidates: vLLM (Python), TGI (Rust+Python), candle (pure Rust), MLX (Apple-only), llama.cpp (C++ with bindings).

## Decision

Use **llama.cpp** as the inference engine, accessed from inferenced through the **`llama-cpp-2` Rust bindings**. Backend is selected at runtime per the hardware manifest: CPU (always), Vulkan/CUDA/ROCm (where present), Metal (Apple Silicon variants if shipped). Models are GGUF Q4 by default; the engine supports other quantizations on request.

## Consequences

### Positive

- Single C++ engine across all hardware variants; no Python runtime in the device.
- GGUF format is the de facto standard for quantized LLMs; broad model availability.
- Mature KV cache prefix reuse; aligns with our context engineering patterns.
- llama.cpp upstream is fast-moving; we benefit from new model and feature support.
- llama-cpp-2 bindings are kept current; the Rust API is small and stable.

### Negative

- C++ dependency in our stack; we accept it as one of the few non-Rust pieces.
- Tracking llama.cpp upstream releases is ongoing work; we pin per release.
- Performance peaks vs vLLM on dense server hardware are lower; not relevant for a device.

## Alternatives considered

- **candle (pure Rust)**: ergonomic for embeddings and small models; ecosystem still narrower than llama.cpp; we use candle for select side models (re-rankers, classifiers) and llama.cpp for LLMs.
- **vLLM**: Python runtime + Linux-only-ish + sized for servers; unfit for an appliance.
- **MLX**: Apple-only; we are not Apple-exclusive.
- **TGI**: Rust core but Python orchestration; more than we need.

## References

- `03-runtime/INFERENCE-ENGINE.md`
- `03-runtime/INFERENCE-MODELS.md`
- `03-runtime/MODEL-REGISTRY.md`
- `02-platform/INFERENCE-ACCEL.md`
## Graph links

[[0014-rust-only-shell-stack]]
