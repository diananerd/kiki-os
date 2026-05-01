---
id: privacy-model
title: Privacy Model
type: SPEC
status: draft
version: 0.0.0
implements: [privacy-model]
depends_on:
  - principles
  - paradigm
  - capability-taxonomy
  - memory-architecture
  - inference-router
depended_on_by:
  - speaker-id
last_updated: 2026-04-30
---
# Privacy Model

## Purpose

Specify the platform's privacy model: how data is classified, where it can flow, how user consent gates flows, the technical controls enforcing the model, and the user's tools for inspecting and controlling their data.

## Behavior

### Privacy is structural, not declarative

The system does not rely on apps to "be privacy-respecting." Privacy is enforced by:

- Capability gating (apps cannot bypass).
- Sandbox isolation (apps cannot read other apps' data).
- Routing decisions (Sensitive data does not reach cloud routes).
- Audit logging (everything is recorded).
- User-controlled grants and revocations.
- Hardware kill switches (where present).

Apps can do less harm than they otherwise might because the system's structure constrains them.

### Four classifications

```
Public            generally shareable; no constraint
Standard          default; apps can use per their grants
Sensitive         restricted; cloud routing forbidden by default
HighlySensitive   medical, financial, etc.; Sensitive plus stricter
                  (audit log uses references only; never logged plain)
```

### Classification sources

- App declarations (in tool calls or response payloads).
- Source domain (e.g., "from the email tool" → privacy inherited).
- User explicit marking.
- Content-based detection (hooks may classify).

The strictest classification of any input wins for downstream routing.

### Classification propagation

```
User says "what's my doctor appointment?"
  → identifies medical context
  → request classified Sensitive
  → Inference: routed to local model only
  → Response (calendar tool): result also Sensitive
  → Episode written: privacy=sensitive
  → Memory recall later: classified Sensitive on retrieve
  → UI rendering: shown only to authorized user; redacted on shared display
```

The classification flows through every layer.

### Routing constraints

| Class | LLM routing | STT routing | TTS routing |
|---|---|---|---|
| Public | any | any | any |
| Standard | per user policy | per user policy | per user policy |
| Sensitive | local only | local only | local only |
| HighlySensitive | local only + extra checks | local only | local only |

User policy can be more restrictive (e.g., "all my data is local"); cannot be less restrictive.

### Per-user privacy preferences

Each user can configure:

- Default privacy class (Standard or Sensitive).
- Per-domain overrides (e.g., always-Sensitive for medical).
- Cloud routing on/off (kill switch).
- Memory sync on/off (per-layer).

Stored in user-preferences.

### Data domains and default sensitivity

| Domain | Default classification |
|---|---|
| calendar | Standard |
| contacts | Standard |
| email | Sensitive (varies) |
| financial | HighlySensitive |
| medical | HighlySensitive |
| health | HighlySensitive |
| location | Sensitive |
| location.history | HighlySensitive |
| photos | Sensitive |
| notes | Standard or Sensitive (user) |

Apps may not lower these.

### Apps and data

Apps see data through:

- Tool calls they expose (the agent passes data to them).
- Capability-mediated reads (rare).

Apps do not have free-form access. They cannot scrape.

For an app to read a user's calendar, it must:

1. Declare `data.calendar.read` in its manifest.
2. Get user grant.
3. Call the calendar tool (which the calendar app provides).
4. Handle the response under its sandbox.

Data passes through tools, not file dumps.

### Cross-app boundaries

App A's data is invisible to App B unless:

- App B has explicit cross-app grant (rare).
- The agent moderates — calling A's tool, getting data, then passing relevant parts to B.

The agent is the canonical mediator. Direct cross-app reads are forbidden.

### Memory privacy

Per layer:

- Sensory: RAM-only, ages out, never disk.
- Working: RAM-only, snapshots minimal.
- Episodic: encrypted disk, per-user.
- Semantic: encrypted disk, per-user.
- Procedural: encrypted disk, per-user.
- Identity: encrypted disk, consent-flow gated.

Cross-user reads require explicit grant.

### Logs and telemetry

- Audit log: all actions, structured; sensitive content referenced not embedded.
- Telemetry: aggregate, no PII; opt-in for cloud upload.
- Crash reports: scrubbed before any upload (default off).

### Inference and privacy

The router enforces:

- Sensitive requests stay local.
- Cloud requests go through gateway with cred substitution.
- Cloud responses are not cached beyond ephemeral.
- When in doubt about privacy, the router defaults to stricter handling.

### Voice and privacy

- Wake word and sensory buffer: local.
- STT routing: per privacy class.
- TTS routing: per privacy class.
- Speaker ID: local only.
- Voice prints: local; never exported, even by the user.
- Voice channels: native is local; WebRTC and Bridge are off-device.

### Consent

Some operations require consent beyond capability grant:

- Identity changes (always consent flow).
- New cloud provider (per-provider opt-in).
- Memory sync (initial opt-in plus per-layer).
- Voice cloud (per-feature opt-in).

Consent is informed: the prompt explains data flow.

### User's tools

The user can:

- View grants and revoke them: `agentctl cap grants`.
- View memory and edit: `agentctl memory inspect`.
- Export memory: `agentctl memory export`.
- Force-delete memory: `agentctl memory prune` / `forget`.
- View audit log: `agentctl audit show`.
- Toggle cloud (kill switch): `agentctl policy cloud off`.

These are first-class tools.

### Privacy invariants

The platform guarantees:

1. Audio never leaves the device unless an explicit cloud route is engaged for a non-Sensitive request.
2. Identity files never leave unencrypted.
3. Memory contents never leave unencrypted.
4. Apps cannot bypass the capability gate.
5. Hardware kill switches are honored at HAL level.
6. The audit log records all data flows.
7. The user can wipe their data fully.

These are checked by structure, not by app cooperation.

### Privacy by content type

Specific content types have additional handling:

#### Faces in images

- Apps cannot extract face vectors from images they receive.
- Facial recognition is not a platform service.

#### Voice prints

- Local only, encrypted, never transmitted.
- A voice print cannot be exported even by the user.

#### Children's data

- If the system identifies a minor: cloud routing requires extra guardrails. Some categories (e.g., children's behavior tracking) are forbidden by default.

## Interfaces

### Programmatic

```rust
pub struct PrivacyClassification {
    pub tier: PrivacyTier,
    pub sources: Vec<DataDomain>,
    pub user_marked: Option<PrivacyTier>,
    pub propagation_rules: PropagationRules,
}
```

### CLI

```
agentctl policy show                     # current policy
agentctl policy cloud <on/off>           # cloud kill switch
agentctl policy default <Standard/Sensitive>
agentctl policy domain <domain> <class>
agentctl cap grants                       # current grants
agentctl memory audit                     # what's in memory
agentctl audit show                       # audit log
```

## State

### Persistent

- Per-user privacy preferences.
- Capability grants.
- Audit log.
- Encrypted memory layers.

### In-memory

- Active classification of in-flight requests.

## Failure modes

| Failure | Response |
|---|---|
| Classification ambiguous | err on stricter side |
| Routing to cloud denied | local fallback; if none, error |
| User policy contradicts app need | app degraded function; alert |
| Audit log unavailable | refuse operations needing audit; alert (CRITICAL) |

## Performance contracts

- Classification check on request: <100µs.
- Routing decision: <1ms.

## Acceptance criteria

- [ ] All sensitive requests stay local (verified by router tests).
- [ ] Hardware kill switches enforce at HAL.
- [ ] Memory layers encrypted at rest.
- [ ] Cross-user reads require explicit grant.
- [ ] Cross-app reads not possible without grant.
- [ ] User can fully wipe their data.
- [ ] Audit log records all data flows.
- [ ] Privacy invariants documented and tested.

## References

- `00-foundations/PRINCIPLES.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/AUDIT-LOG.md`
- `10-security/HARDCODED-RESTRICTIONS.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `03-runtime/CAPABILITY-GATE.md`
