---
id: data-flow
title: Data Flow
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - system-overview
  - process-model
  - principles
depended_on_by:
  - trust-boundaries
last_updated: 2026-04-30
---
# Data Flow

## Problem

Documenting individual layers in isolation does not show how information flows through the system. Without an explicit data flow document:

- Privacy leaks are easy to overlook (Sensitive data could route through an unintended path).
- Performance bottlenecks are invisible (which step in the chain dominates latency).
- Auditability gaps go undetected (an action might pass through points where the audit log does not see it).

## Constraints

- Every cross-layer flow must pass through a defined enforcement point.
- Privacy classifications must propagate end-to-end; the strictest classification wins.
- Every action that affects user-visible state must produce an audit log entry.
- Latency-critical paths (voice, inference) must be flagged so optimization efforts target them.

## Decision

Five canonical data flows define how information traverses Kiki OS. Every operation is one of these flows or a composition.

### Flow 1 — User intent to agent action

```
USER (voice / text / gesture)
  ↓
AGENTUI (canvas + command bar; libinput-rs / voice pipeline)
  ↓
focusbus (selection state) + Cap'n Proto request
  ↓
AGENTD (coordinator; classifies event)
  ↓
INFERENCED (router decides local vs remote, applies privacy class)
  ↓
LLM (local llama.cpp or remote provider via cosign-verified gateway)
  ↓
AGENTD (parses tool calls; loops back if needed)
  ↓
POLICYD (capability gate evaluates each tool call;
         arbiter classifier for borderline cases)
  ↓
TOOLREGISTRY (resolves tool URI; dispatches)
  ↓
APP / WASM TOOL / BUILT-IN (executes via Cap'n Proto)
  ↓
AGENTD (collects result; integrates into next inference)
  ↓
AGENTUI (renders block; updates canvas)
  ↓
USER (sees response)
```

Privacy classification flows along the chain. If the user's input is Sensitive, the inference is local-only, the result is Sensitive in episodic memory, retrieval of that result later is Sensitive.

Audit log entries fire at: event arrival, capability check, tool dispatch, tool result, final response.

### Flow 2 — Perception to memory

```
HARDWARE (microphone, camera, sensors)
  ↓
HAL DAEMON (kiki-hald-audio, kiki-hald-camera, etc.)
  ↓
Cap'n Proto / iceoryx2 (audio / video frames)
  ↓
SENSORY BUFFER in memoryd (RAM-only ring buffer)
  ↓ (on wake word, manual activation, or significant event)
WORKING MEMORY (promoted as summarized form)
  ↓ (at end of inference cycle)
EPISODIC MEMORY (LanceDB; tagged with workspace_id, privacy class)
  ↓ (during dreaming REM phase)
SEMANTIC GRAPH candidates (CozoDB; held in workspace)
  ↓ (during dreaming DEEP phase, after validation + user consent for identity)
SEMANTIC / PROCEDURAL / IDENTITY (committed)
```

Privacy classification is set at promotion and propagates through every layer. Sensory data never reaches disk in raw form. Episodic data is encrypted at rest. Identity-class proposals from dreaming require explicit consent before commit.

### Flow 3 — Memory retrieval to inference context

```
AGENT LOOP (needs context for next inference)
  ↓
MEMORYD (retrieve query: text, filters, privacy bound)
  ↓
ACL CHECK (workspace scope, user scope, sensitivity filter)
  ↓
PARALLEL RETRIEVAL:
    LanceDB (vector + columnar episodic)
    CozoDB (semantic graph + entity neighborhood)
    Procedural sqlite-vec index
    Recency window (always)
  ↓
SCORING + RANKING (intrinsic, recency boost, thread boost,
                   entity match, confidence, privacy adjust)
  ↓
TOKEN BUDGET TRIM (caps cumulative content size)
  ↓
WORKING MEMORY (retrieved memories appended to context frame)
  ↓
INFERENCE (model receives context + identity frame + tools)
```

Identity tokens are reserved and never compacted away. Cross-user retrieval requires explicit grant. Sensitive memories included only when the request itself is Sensitive.

### Flow 4 — App action to capability decision

```
APP (wants to perform tool call or use system capability)
  ↓
SDK (sends Cap'n Proto request via libagentos-system)
  ↓
Cap'n Proto over /run/kiki/agentd.sock
  ↓
AGENTD (receives request; identifies caller via SO_PEERCRED)
  ↓
TOOLREGISTRY (resolve tool URI; check parameters_schema)
  ↓
POLICYD CAPABILITY GATE:
    1. Hardcoded restrictions check
    2. Hardware realizability check
    3. User policy check
    4. Pre-decision hooks
    5. Grant table lookup
    6. Constraint application
    7. Rate limiting
    8. Arbiter classifier (if borderline)
    9. Audit log entry
  ↓ (allow)
TOOL DISPATCH (Cap'n Proto to target app, WASM, or built-in)
  ↓
RESULT (returned to agent loop)
```

If the gate denies, the result is a denial returned to the agent (not an exception). The agent decides next action — the gate's decision is terminal for this attempt; the agent cannot route around it.

### Flow 5 — Distribution to local artifact

```
MAINTAINER (publishes artifact)
  ↓
buildah / podman build (create OCI image)
  ↓
cosign sign (with namespace's private key)
  ↓ (optional)
sigsum / Rekor (witness submission for transparency)
  ↓
OCI REGISTRY (push to maintainer's registry)
  ↓ ... ... time passes ... ...

USER (initiates install via agentctl or agent)
  ↓
agentctl (resolves kiki:<ns>/<name>@version)
  ↓
NAMESPACE REGISTRY (returns: registry URL + cosign key fingerprint)
  ↓
OCI REGISTRY (pull artifact)
  ↓
COSIGN VERIFY (against namespace key fingerprint)
  ↓
LOCAL EXTRACTION:
    OS image    → bootc switch
    sysext      → systemd-sysext refresh
    app         → /var/lib/kiki/apps/ + quadlet generation
    component   → /var/lib/kiki/components/
    tool (WASM) → /var/lib/kiki/tools/wasm/
    profile     → /var/lib/kiki/profiles/
    model       → /var/lib/kiki/models/
  ↓
REGISTRATION (toolregistry, ComponentRegistry, etc.)
  ↓
AUDIT LOG ENTRY (artifact installed)
```

Trust check happens once per artifact pull. If the namespace's cosign key has rotated, the agent prompts the user before accepting the new key.

## Privacy classification propagation

Privacy is enforced architecturally via four tiers (see `10-security/PRIVACY-MODEL.md`):

- `Public` — generally shareable; no constraint.
- `Standard` — default; subject to user policy.
- `Sensitive` — must run locally; cannot leave device without explicit grant.
- `HighlySensitive` — Sensitive plus stricter (audit log uses references only, no content embedded).

Classification rules:

- The strictest classification of any input wins for the whole flow.
- Apps cannot lower a classification (only raise).
- The inference router refuses to route Sensitive to remote models.
- Memory retrieval respects the classification (Sensitive memories filtered out of Standard contexts).
- Audit log entries inherit the classification of their event.

## Latency-critical paths

Three paths are flagged as latency-critical and are the focus of performance optimization:

### Voice round-trip

```
microphone → VAD → STT → agent loop → tool dispatch (if needed) → response → TTS → speaker
```

Target: under 1.2s end-to-end on hybrid mode (some local, some cloud).

### Touch / canvas interaction

```
input event → libinput-rs → agentui scene graph → reconciliation → frame
```

Target: under 50ms input-to-display.

### Workspace switch

```
user gesture → libinput-rs → agentui workspace manager → cage swap → animation
```

Target: under 500ms warm; under 2s when thawing a hibernated workspace.

## Bulk data plane

Some flows transfer large data (audio frames, video frames, GPU textures from tier-full apps) and are routed through iceoryx2 zero-copy shared memory rather than Cap'n Proto RPC. The control plane (request, capability check) goes through Cap'n Proto; the data plane (frames) goes through iceoryx2.

This split is documented in `05-protocol/ICEORYX-DATAPLANE.md`.

## Audit hooks

Every flow has audit hooks at key points. The audit log captures:

- Event arrival (Flow 1).
- Memory write (Flow 2).
- Memory retrieval with retrieved item count (Flow 3).
- Capability decision with reason (Flow 4).
- Artifact installation with cosign verification result (Flow 5).

Sensitive content is referenced (memory ID, file path) rather than embedded in the audit log, so the log can be inspected and exported without leaking.

## Consequences

- Adding a new feature must declare which flow(s) it touches and where.
- Performance regressions can be located: each flow has known latency targets.
- Privacy review is bounded: a feature is reviewed against the privacy classification flow.
- Audit gaps are detectable: a flow without an audit hook at a critical point is incomplete.

## References

- `01-architecture/SYSTEM-OVERVIEW.md`
- `01-architecture/PROCESS-MODEL.md`
- `01-architecture/TRUST-BOUNDARIES.md`
- `10-security/PRIVACY-MODEL.md`
- `10-security/AUDIT-LOG.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `03-runtime/AGENT-LOOP.md`
- `05-protocol/ICEORYX-DATAPLANE.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
