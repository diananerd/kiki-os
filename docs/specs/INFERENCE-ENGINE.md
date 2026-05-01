---
id: inference-engine
title: Inference Engine
type: SPEC
status: draft
version: 0.0.0
implements: [local-inference-engine]
depends_on:
  - inference-router
  - model-registry
  - inference-accel
depended_on_by:
  - inference-models
  - model-lifecycle
  - model-registry
  - stt-local
  - tts-local
  - wake-word
last_updated: 2026-04-30
---
# Inference Engine

## Purpose

Specify the local inference engine: llama.cpp via the `llama-cpp-2` Rust binding, model loading, hardware backend selection, streaming output, and integration with the inference router.

## Behavior

### Engine choice

**llama.cpp** via the `llama-cpp-2` Rust crate. Reasons:

- Ecosystem velocity: every major GGUF quant lands here first.
- Vulkan backend production-grade in 2026 (within 10–20% of CUDA on consumer GPUs).
- OpenAI-compatible HTTP server (llama-server) stable.
- `llama-cpp-2` tracks upstream within days; supports in-process embedding via `LlamaContext`.
- License: MIT.

mistral.rs is the documented runner-up; pure Rust, but trails llama.cpp on quant coverage and ecosystem velocity. See `14-rfcs/0098-mistralrs-runner-up-documented.md`.

### Process model

`inferenced` is the daemon hosting the engine. The engine runs in-process. Models load on demand into `inferenced`'s memory.

### Backend selection

Per `02-platform/INFERENCE-ACCEL.md`:

```rust
let backend = match (manifest.gpu.vendor, user_pref) {
    ("nvidia", "cuda") => Backend::Cuda,
    ("nvidia", _)      => Backend::Vulkan,
    ("amd", _)         => Backend::Vulkan,
    ("intel", _)       => Backend::Vulkan,
    ("apple", _)       => Backend::Metal,
    _                  => Backend::Cpu,
};
```

### Model loading

Models distributed as OCI artifacts (`application/vnd.kiki.model.gguf.v1+blob`). On install:

```
1. agentctl pull kiki:core/models/llama-3.3-8b-q4
2. cosign verify
3. Extract to /var/lib/kiki/models/<ns>/<name>/<version>/
4. inferenced detects new model; ready to load on demand
```

Load on demand:

```rust
let model = LlamaModel::load(path, params)?;
let ctx = LlamaContext::new(&model, ctx_params)?;
```

Models stay loaded in memory until evicted (LRU per resource budget).

### Streaming output

Tokens stream as they're generated:

```rust
let mut stream = ctx.generate(prompt, sampling_params)?;
while let Some(token) = stream.next().await {
    yield token;
}
```

The agent loop consumes the stream and forwards to TTS / canvas as appropriate.

### Resource management

`inferenced` enforces per-request budgets (max_tokens, timeout). Concurrent requests share the underlying model context if compatible (KV cache reuse). Otherwise queued.

VRAM budget tracked per loaded model. If new model would exceed VRAM, an eviction policy (LRU) unloads least-recently-used model.

### Sampling

Standard params: temperature, top_p, top_k, repetition_penalty, max_tokens. Per-request override possible.

### Tool calling

Models that support tool calling natively (Llama 3.3, Qwen 2.5, Granite, etc.) emit structured tool calls. `inferenced` parses and forwards to agent loop.

For models without native tool calling, the engine adapts: prompt the model with tool definitions in a structured format; parse JSON tool calls from the output. Less reliable; flagged as "basic" in capability metadata.

### Embedding generation

Same engine generates embeddings for retrieval (see `04-memory/RETRIEVAL.md`). The embedding model (bge-m3) is loaded separately from the LLM model and runs in parallel.

### Loaded models

Always-loaded:
- Llama Prompt Guard 2 (86M) for arbiter stage 1.
- Granite Guardian 3.2 5B for arbiter stage 2 (when capacity permits).
- bge-m3 embedding model for retrieval.

On-demand:
- The default LLM (Llama 3.3 8B Q4_K_M).
- Other models per user request.

### Performance numbers

On reference hardware (M2 Pro 16 GB):

- Llama 3.3 8B Q4_K_M: ~38 tok/s decode, ~180ms TTFT.
- Qwen 2.5 14B Q4_K_M: ~22 tok/s decode, ~280ms TTFT.

On RTX 4060 Vulkan:

- Llama 3.3 8B Q4_K_M: ~75 tok/s.
- Qwen 2.5 14B Q4_K_M: ~45 tok/s.

CUDA fast path: ~10–20% above Vulkan on NVIDIA.

### Integration with inferenced HTTP server

`inferenced` exposes an OpenAI-compatible HTTP API at `inference.local`:

```
POST /v1/chat/completions
POST /v1/completions
POST /v1/embeddings
```

Apps and the agent use placeholder credentials; `inferenced` substitutes real provider credentials at egress for remote routes, or routes to the local engine for local requests.

## Interfaces

### Programmatic (within inferenced)

```rust
pub struct LocalEngine {
    fn load_model(&mut self, path: &Path) -> Result<ModelHandle>;
    fn unload_model(&mut self, handle: ModelHandle);
    fn complete(&self, model: ModelHandle, request: CompletionRequest) -> impl Stream<Item = Token>;
    fn embed(&self, model: ModelHandle, texts: &[String]) -> Result<Vec<Embedding>>;
}
```

### CLI

```
agentctl inference status        # loaded models, VRAM usage
agentctl inference load <name>   # explicit load
agentctl inference unload <name>
agentctl inference test <model> "<prompt>"
```

## State

### Persistent

- Model files in /var/lib/kiki/models/.
- Model catalog in system.sqlite.

### In-memory

- Loaded models with their backend contexts.
- KV caches for active requests.

## Failure modes

| Failure | Response |
|---|---|
| Model file missing | error to caller; suggest install |
| GGUF parse fails | error; mark model unavailable |
| Insufficient VRAM | router falls back; alert |
| Backend driver crash | restart engine; mark backend Unavailable temporarily |
| OOM during inference | abort; release; alert |

## Performance contracts

- Model load: 2–10s depending on size and storage.
- First token (warm): per `INFERENCE-MODELS.md` table.
- Throughput: per `INFERENCE-MODELS.md`.

## Acceptance criteria

- [ ] llama.cpp via llama-cpp-2 hosting models.
- [ ] Vulkan backend works on Intel, AMD, NVIDIA.
- [ ] CUDA opt-in on NVIDIA.
- [ ] Apple Silicon Metal backend.
- [ ] Streaming output to agent loop.
- [ ] Tool calling integrates with model registry capabilities.
- [ ] Embeddings via bge-m3.

## References

- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/MODEL-REGISTRY.md`
- `03-runtime/INFERENCE-MODELS.md`
- `02-platform/INFERENCE-ACCEL.md`
- `14-rfcs/0024-llamacpp-inference-engine.md`
- `14-rfcs/0098-mistralrs-runner-up-documented.md`
## Graph links

[[INFERENCE-ROUTER]]  [[MODEL-REGISTRY]]  [[INFERENCE-ACCEL]]
