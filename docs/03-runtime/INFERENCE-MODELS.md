---
id: inference-models
title: Inference Model Catalog
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - inference-router
  - inference-engine
  - model-registry
last_updated: 2026-04-29
depended_on_by:
  - arbiter-classifier
  - model-lifecycle
  - stt-local
  - tts-local
  - voice-pipeline
---
# Inference Model Catalog

This document lists the models Kiki OS uses, their roles, characteristics, and the rationale for each choice.

## Default models

### Llama 3.3 8B Instruct (Q4_K_M) — main LLM

- Identity: `kiki:core/models/llama-3.3-8b-q4`
- Role: default model for agent reasoning and tool calling.
- Memory: ~5.5 GB VRAM/RAM.
- Performance: ~38 tok/s on M2 Pro; ~75 tok/s on RTX 4060 Vulkan.
- TTFT: ~180ms.
- License: Llama 3 Community License.
- Capabilities: native tool calling, multi-turn, 128K context, streaming.

Selected as default for the 16 GB hardware tier. Solid quality, fast on consumer hardware, good tool calling, broad multilingual support.

### Qwen 2.5 14B Instruct (Q4_K_M) — 32 GB tier

- Identity: `kiki:core/models/qwen-2.5-14b-q4`
- Role: alternative default for 32 GB hardware tier.
- Memory: ~9 GB.
- Performance: ~22 tok/s on M2 Pro; ~45 tok/s on RTX 4060 Vulkan.
- License: Apache 2.0.
- Capabilities: native tool calling, 128K context, multilingual.

### Granite Guardian 3.2 5B — arbiter stage 2

- Identity: `kiki:core/models/granite-guardian-3.2-5b`
- Role: deliberative gating in the arbiter classifier.
- Memory: ~3.2 GB.
- License: Apache 2.0.
- Inference: ~250ms typical for one classification.

Always-loaded. Receives only `(user_prompt, tool_call_descriptor)` per input minimization.

### Llama Prompt Guard 2 86M — arbiter stage 1

- Identity: `kiki:core/models/prompt-guard-2-86m`
- Role: fast pre-filter in arbiter classifier.
- Memory: ~50 MB INT8.
- License: Llama Community.
- Inference: <10ms.

Always-loaded. Two-stage filter cuts FPR from 8.5% to 0.4%.

### Whisper Large-v3-turbo — STT

- Identity: `kiki:core/models/whisper-large-v3-turbo`
- Role: speech-to-text via whisper.cpp.
- Memory: ~1.2 GB.
- License: MIT.
- TTFT: ~140ms first partial; ~600ms final for 10s utterance.
- Multilingual.

### Kokoro-82M — TTS

- Identity: `kiki:core/models/kokoro-82m`
- Role: text-to-speech.
- Memory: ~350 MB.
- License: Apache 2.0.
- TTFA: ~150ms first audio.
- Multiple voices.

### bge-m3 — embeddings

- Identity: `kiki:core/models/bge-m3`
- Role: hybrid search embeddings (retrieval).
- Memory: ~280 MB INT8.
- License: MIT.
- Throughput: ~8ms per passage on M2.

### jina-reranker-v2-base-multilingual — reranker

- Identity: `kiki:core/models/jina-reranker-v2`
- Role: cross-encoder reranker after first-stage retrieval.
- Memory: ~280 MB.
- License: Apache 2.0.
- ~80ms for 20 candidates.

### Silero VAD v5 — voice activity

- Identity: `kiki:core/models/silero-vad-v5`
- Role: voice activity detection.
- Memory: ~2 MB ONNX.
- License: MIT.
- <1ms per 30ms frame.

### microWakeWord — wake word

- Identity: `kiki:core/models/microwakeword`
- Role: always-on wake word.
- Memory: <5 MB TFLite.
- License: Apache 2.0.
- <50ms detection, <1% CPU.

## Cloud routes

### gateway:standard

- Role: cloud LLM tier for Standard requests.
- Routed via Kiki AI Gateway with cred substitution.
- Provider: configured per gateway.

### gateway:strong

- Role: high-quality cloud tier for tasks above local capacity.
- Routed via Kiki AI Gateway.

The provider behind these aliases is a deployment detail. Default provider configurations published with the AI Gateway documentation.

## Memory budget summary

### 16 GB hardware tier (idle, all loaded)

```
prompt-guard-2-86m         50 MB
silero-vad-v5               2 MB
microwakeword               5 MB
bge-m3                    280 MB
jina-reranker-v2          280 MB
kokoro-82m                350 MB
whisper-large-v3-turbo  1,200 MB
granite-guardian-3.2-5b 3,200 MB
llama-3.3-8b-q4         5,500 MB
─────────────────────────────────
Total                  ~10.9 GB
```

Leaves headroom for OS shell, browser engine, app containers.

### 32 GB hardware tier

Swap default LLM to Qwen 2.5 14B (~9 GB) for higher quality. Total ~14.4 GB. Comfortable headroom for heavy workloads.

## Choosing additional models

Users can install additional models from the registry:

```
agentctl install kiki:<ns>/models/<name>
```

Constraints:
- Must be a registered namespace.
- cosign verification required.
- Model must declare capabilities accurately.
- VRAM/RAM check at install time.

## Model updates

When a new version of a model is published, the namespace's registry receives the update. `agentctl pull-models` fetches updates. The user is notified for default models.

Old versions kept until `agentctl model gc`.

## Quantization notes

Q4_K_M is the default quantization for LLMs. Tradeoffs:

- Q4_K_M: best quality/size balance for most use.
- Q5_K_M: marginal quality boost; ~25% larger.
- Q8_0: near-original quality; 2x larger.
- F16: full quality; 4x larger; rarely worth it for chat.

Users can install higher quants if VRAM allows.

## References

- `03-runtime/INFERENCE-ENGINE.md`
- `03-runtime/MODEL-REGISTRY.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `04-memory/RETRIEVAL.md`
- `08-voice/VOICE-PIPELINE.md`
## Graph links

[[INFERENCE-ROUTER]]  [[INFERENCE-ENGINE]]  [[MODEL-REGISTRY]]
