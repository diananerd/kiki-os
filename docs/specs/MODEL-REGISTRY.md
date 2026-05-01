---
id: model-registry
title: Model Registry
type: SPEC
status: draft
version: 0.0.0
implements: [model-registry]
depends_on:
  - inference-engine
  - oci-native-model
depended_on_by:
  - inference-engine
  - inference-models
  - inference-router
last_updated: 2026-04-30
---
# Model Registry

## Purpose

Specify the registry of available inference models: their identity, capabilities, health, routing characteristics, and how the router consults the registry to make decisions.

## Behavior

### Model entries

Each model has a registry entry:

```rust
struct ModelEntry {
    id: ModelId,                       // e.g., "kiki:core/models/llama-3.3-8b-q4"
    name: String,                      // human name
    privacy_class: PrivacyClass,       // Local | TrustedCloud | ThirdPartyCloud
    capabilities: ModelCapabilities,   // tool_calling, thinking, vision, ...
    context_window: u32,
    typical_first_token_ms: u32,
    typical_throughput_tok_per_s: u32,
    memory_mb: u32,                    // VRAM or RAM required
    cost_per_token_in: Option<f64>,    // None for local
    cost_per_token_out: Option<f64>,
    health: HealthState,               // Healthy | Degraded | Unavailable
    route: Route,                      // local engine, AI gateway, direct provider
    quantization: Option<String>,      // Q4_K_M, Q5_K_M, etc.
    license: License,
}
```

### Model sources

Models come from three sources:

1. **Local OCI artifacts**: pulled from registry, stored in `/var/lib/kiki/models/`. Loaded by `inferenced` on demand.
2. **AI Gateway routes**: remote models accessed through Kiki's backend gateway with cred substitution.
3. **Direct provider routes**: rare; KikiSigned only; for users who explicitly grant `inference.cloud.direct`.

### Registration

Local models register at install time. The OCI artifact metadata declares capabilities; `inferenced` parses and adds to the registry.

Cloud routes register from configuration (`inferenced` config file) at startup.

### Capability schema

```rust
struct ModelCapabilities {
    tool_calling: ToolCallingTier,    // None | Basic | Native
    thinking: ThinkingTier,           // None | Streaming | Extended
    vision: bool,
    audio_input: bool,
    multi_turn: bool,
    context_window_max: u32,
    structured_output: bool,
    streaming: bool,
    languages: Vec<String>,
}
```

### Health state

Models start as `Healthy`. The router records outcomes:

- Single failure within window: log, retry once, no state change.
- Multiple failures within window: mark `Degraded` (still callable but ranked lower).
- Continued failures: mark `Unavailable` for a cool-down period.
- After cool-down: probe to test; restore to `Healthy` if probe succeeds.

Health state is per-model, in-memory. Resets on `inferenced` restart.

### Route types

```rust
enum Route {
    LocalEngine { path: PathBuf, backend: Backend },
    AiGateway { gateway_url: String, model_alias: String },
    DirectProvider { provider: String, endpoint: String, model: String },
}
```

The router chooses a route based on privacy, latency, capabilities, and policy.

### Default registered models

A v0 desktop install registers:

- `kiki:core/models/prompt-guard-2-86m` (always-loaded; arbiter stage 1).
- `kiki:core/models/granite-guardian-3.2-5b` (always-loaded; arbiter stage 2).
- `kiki:core/models/bge-m3-embeddings` (always-loaded; retrieval).
- `kiki:core/models/whisper-large-v3-turbo` (loaded on voice activation).
- `kiki:core/models/kokoro-82m` (loaded on TTS).
- `kiki:core/models/llama-3.3-8b-q4` (default LLM; loaded on first agent inference).
- `gateway:standard` (AI Gateway alias for cloud-standard tier).
- `gateway:strong` (AI Gateway alias for cloud-strong tier).

The user can pull additional models via `agentctl install kiki:<ns>/models/...`.

### Lifecycle

```
install → load on demand → use → unload (LRU eviction or explicit)
```

VRAM budget is enforced. If a new model needs to load and VRAM is full, the LRU non-pinned model is unloaded.

Always-loaded models are pinned and not subject to LRU eviction.

### Versioning

Models version per OCI artifact. New versions of the same model id update the registry. Old versions kept until explicitly garbage-collected.

```
agentctl model versions kiki:core/models/llama-3.3-8b-q4
agentctl model gc                  # remove unreferenced versions
```

## Interfaces

### Programmatic

```rust
struct ModelRegistry {
    fn register(&mut self, entry: ModelEntry) -> Result<()>;
    fn unregister(&mut self, id: &ModelId) -> Result<()>;
    fn lookup(&self, id: &ModelId) -> Option<&ModelEntry>;
    fn healthy_models(&self) -> Vec<&ModelEntry>;
    fn record_outcome(&mut self, id: &ModelId, outcome: ModelOutcome);
}
```

### CLI

```
agentctl model list
agentctl model show <id>
agentctl model load <id>
agentctl model unload <id>
agentctl model health
agentctl model gc
```

## State

### Persistent

- Model files in /var/lib/kiki/models/.
- Model catalog in system.sqlite.

### In-memory

- Registry entries.
- Health state per model.
- Loaded model contexts.

## Failure modes

| Failure | Response |
|---|---|
| Model artifact missing | mark Unavailable; alert |
| OCI verification fails on install | reject install |
| Capability declaration invalid | reject; clear error |
| Multiple models with same id | reject second registration |

## Performance contracts

- Registry lookup: <1µs.
- Load on demand (cold): 2–10s depending on size.
- Unload: <100ms.

## Acceptance criteria

- [ ] All v0 default models registered.
- [ ] Health state updated by router outcome reports.
- [ ] LRU eviction respects pinned models.
- [ ] Multiple versions per id supported.
- [ ] OCI artifact integrity verified at install.

## References

- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/INFERENCE-ENGINE.md`
- `03-runtime/INFERENCE-MODELS.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
