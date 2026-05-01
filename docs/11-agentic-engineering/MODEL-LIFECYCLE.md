---
id: model-lifecycle
title: Model Lifecycle
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - inference-engine
  - inference-models
  - update-orchestrator
  - cosign-trust
last_updated: 2026-04-29
---
# Model Lifecycle

## Purpose

Specify how models reach the device, how they are
verified, swapped, and retired. A model on a Kiki device
is high-trust software: it sees user data and produces
behavior. The lifecycle around it must match.

## Scope

This document covers:

- LLMs (Llama 3.3 8B and friends)
- Speech models (Whisper, Kokoro, microWakeWord, Silero
  VAD)
- Embedding models (bge-m3)
- Re-ranker (jina-reranker-v2)
- Safety classifiers (Granite Guardian, Llama Prompt
  Guard 2)

It does not cover:

- Remote provider models (those are loaded on the
  provider's side; the gateway sees only the wire
  protocol)
- User-trained adapters that aren't shipped by us

## Distribution

Models are OCI artifacts in the same lineage as everything
else (`PARADIGM.md`). Each model has a manifest:

```json
{
  "id": "kiki:models/llama-3.3-8b-q4@1.0.0",
  "kind": "llm",
  "format": "gguf",
  "size_bytes": 5350000000,
  "context_max": 131072,
  "capabilities": ["tool_calling", "thinking", "multi_turn"],
  "license": "Llama-3.3-Community",
  "checksum": "sha256:...",
  "signature": "cosign:...",
  "evals": {"baseline": "rev=2026-04-15"}
}
```

The model image is a single-blob OCI artifact pulled by
the update orchestrator on the model channel.

## Verification

Every model loaded must:

1. Be signed by a trusted Kiki key (cosign with Sigstore
   transparency log entry)
2. Have a signed manifest matching the artifact contents
3. Pass a checksum on disk
4. Be loadable by the inference engine without errors

A model that fails any check is not loaded; the previous
version remains active. This applies to model channel
updates and to model swap operations.

## Storage

Models live under `/var/lib/kiki/models/<id>/`:

```
/var/lib/kiki/models/llama-3.3-8b-q4@1.0.0/
├── manifest.json
├── model.gguf
├── tokenizer.json
├── eval-snapshot.json
└── .signature
```

They are mounted read-only into inferenced. Multiple
versions can coexist for A/B comparison and instant
rollback; old versions are GC'd after a grace period.

## Memory budget

Each model declares its memory profile:

- `cpu_load_mb` — RAM cost when loaded on CPU
- `gpu_vram_mb` — VRAM cost when loaded on accelerator
- `kv_cache_mb_per_token` — incremental cost for context
- `concurrent_inferences_max` — how many parallel
  inferences this model can handle on the target hardware

The inference engine refuses to load a model that would
exceed available memory; it picks an alternative or fails
gracefully.

## Update flow

```
1. Backend signs new model release; pushes to OCI registry
   on the "models" channel for the relevant variant.
2. Update orchestrator notices the new version (poll +
   server hint).
3. On user-approved or scheduled window, orchestrator
   downloads the artifact (resumable; bandwidth-aware).
4. Verifies signature, transparency log, checksum.
5. Stages alongside current model.
6. Runs the eval suite against the staged model in a
   sandboxed inference engine.
7. If pass, swap: load staged, drain in-flight requests on
   old, unload old.
8. If fail, retain old; alert the user in settings.
```

The full eval gate is critical for safety models
(Guardian, Prompt Guard); for general LLMs it can be more
permissive (smoke tests + opt-in canary).

## Hot-swap

For most models, swap is a load + atomic-pointer-swap +
drain. The agent loop sees a `model_changed` event;
in-flight inferences continue on the old model and finish.
New requests use the new model.

For models that hold lots of state (KV cache, fine-tuned
adapters), warm-up before swap so latency doesn't jump.

## Rollback

If a newly-loaded model misbehaves at runtime (eval
post-swap regressions, user reports of weird behavior),
the orchestrator can roll back:

```
kiki-models rollback <id>
```

This is fast: the previous version is still on disk
within the grace period.

## Retirement

Models retired in upstream (deprecated, license withdrawn,
known-unsafe behavior) are flagged in the manifest:

```json
"retired": {
  "since": "2026-09-01",
  "reason": "license-changed",
  "replacement": "kiki:models/llama-4.0-7b@1.0.0"
}
```

The orchestrator surfaces this in settings and pushes the
replacement (per the channel rules).

## Selection at runtime

The model registry (see `MODEL-REGISTRY.md`) tracks loaded
models and their health. The inference router picks per
request based on capabilities, latency, privacy. The
lifecycle layer is below the router; it provides "the set
of available models" and the router picks.

## A/B comparisons

For evaluating a new model:

- Load both
- Route a small fraction of traffic to the new (opt-in;
  configurable)
- Compare outcome metrics (no quality dip, no cost spike)
- Promote on success; roll back on regression

A/B is opt-in per user.

## User-supplied models

Users can opt to load a custom model:

- Place the GGUF and a manifest in a known location
- Sign with their own key (cosign with their identity);
  the system recognizes user-keyed models as
  "user-trusted"
- The model runs only with reduced trust: `Sensitive`
  privacy requests do not route to it; `agent.memory.
  write.identity` is denied

Users who want full integration with system-trust models
must wait for the official channel.

## Safety models

Granite Guardian, Llama Prompt Guard, and Whisper noise
gates are safety-critical. Their lifecycle is stricter:

- Cannot be hot-swapped without a maintenance window
  (small)
- Eval suite is a hard gate
- Rollback is automatic on a regression in the safety
  eval over the first hour of use
- A "safe minimum" is always retained (even if a swap
  goes wrong, the system has a working classifier)

## Provenance

Every model carries provenance metadata visible to the
user:

- Provider (Meta, IBM, Mistral, etc.)
- License URL
- Training data summary URL (if disclosed)
- Eval scores at release
- Sigstore log entry

Settings → Models → Details shows this. Users who care
can review before consenting to a model running on their
device.

## Anti-patterns

- **Auto-swapping safety models** without eval gate
- **Loading unsigned models** (only signed; never local
  trust shortcuts in production)
- **Multiple unscoped versions** (memory blow-up; lifecycle
  enforces grace periods and GC)
- **No rollback path** (always retain prior version for
  the grace period)
- **Hidden model swaps** (user must see what changed and
  when)

## Performance contracts

- Verification: <2s for a 5GB model
- Hot swap: drain ≤5s; new model ready ≤1s after swap
- Rollback: <500ms (already on disk)
- Eval gate: <2 min for the smoke set

## Acceptance criteria

- [ ] Models are signed and verified before load
- [ ] Eval gate runs before promotion
- [ ] Rollback works without restart for non-safety
      models
- [ ] User-supplied models run with reduced trust
- [ ] Provenance shown in settings

## Open questions

None.

## References

- `00-foundations/PRINCIPLES.md`
- `00-foundations/PARADIGM.md`
- `03-runtime/INFERENCE-ENGINE.md`
- `03-runtime/INFERENCE-MODELS.md`
- `03-runtime/MODEL-REGISTRY.md`
- `03-runtime/UPDATE-ORCHESTRATOR.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/SIGSTORE-WITNESS.md`
- `11-agentic-engineering/EVALUATION.md`
