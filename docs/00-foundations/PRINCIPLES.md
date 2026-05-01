---
id: principles
title: Design Principles
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - vision
  - paradigm
depended_on_by:
  - anti-patterns
  - audit-log
  - backend-contract
  - capability-taxonomy
  - context-engineering
  - cost-control
  - cryptography
  - curated-prompts
  - data-flow
  - design-philosophy
  - deterministic-vs-agentic
  - evaluation
  - hardcoded-restrictions
  - hardware-abstraction
  - harness-patterns
  - memory-architecture
  - model-lifecycle
  - multi-agent-policy
  - oci-native-model
  - privacy-model
  - process-model
  - prompt-injection-defense
  - remote-architecture
  - sdk-overview
  - shell-overview
  - system-overview
  - threat-model
  - trust-boundaries
last_updated: 2026-04-30
---
# Design Principles

## Problem

Engineering decisions in a complex system require a stable set of constraints. Without them, decisions drift toward whatever feels expedient at the moment. The result is a system whose behavior cannot be predicted from its purpose.

## Constraints

- Principles must be testable: a decision either complies or doesn't.
- Principles must be ordered: when two conflict, the resolution is determined.
- Principles must be few: more than ~12 cannot be remembered or applied.
- Principles must be technical: business and product principles belong elsewhere.

## Decision

The following principles constrain every technical decision in Kiki OS. They are listed in priority order. When two conflict, the higher-priority principle wins.

### 1. Safety

The system does not knowingly produce harm to users or to people other than users.

**Test:** No code path enables actions on the hardcoded restrictions list (see `10-security/HARDCODED-RESTRICTIONS.md`). Safety checks cannot be disabled by configuration.

### 2. Privacy

Sensitive user data is enforced to stay on-device unless the user has explicitly authorized egress.

**Test:** A request tagged `Sensitive` cannot reach the cloud through any code path. The capability gate denies cross-boundary data flow without explicit grant. The audit log records every attempt.

### 3. Security

Each layer assumes the layer above may be compromised and limits the damage.

**Test:** A compromised app cannot exfiltrate data outside its declared capabilities. A compromised agent cannot bypass the capability gate. A compromised cloud cannot extract local-only data.

### 4. Reliability

The system tolerates partial failures without compromising the whole.

**Test:** An app crash does not crash the agent harness. The agent harness crashing does not corrupt persistent memory. A failed update reverts via atomic rollback. Network loss does not block local operation.

### 5. Performance

Within the bounds of the higher principles, the system minimizes latency, memory, and power consumption.

**Test:** Documented performance contracts in each SPEC. Regressions caught in CI.

### 6. Convenience

Within the bounds of the higher principles, the system minimizes friction for users and developers.

**Test:** Common tasks have short paths. Configuration has sensible defaults. Errors are actionable.

## Rationale

**Why this order?** Convenience routinely tempts engineers to weaken privacy or security. The order is explicit so that those temptations are resolved before they become decisions.

**Why so few?** Memorable. Every contributor can hold the full list. A principle that requires a wiki to remember does not constrain behavior in practice.

**Why technical only?** Other principles (e.g., open source, sustainability) belong to project governance, not to engineering decisions about specific subsystems. Mixing categories blurs the test.

## Operational rules that follow from the principles

These are not separate principles but rules that fall out of the priorities above. Each must be honored in every implementation.

### Local-first

The device works without network. Cloud is enhancement, not foundation. A request fails honestly when it cannot be served locally and policy forbids cloud routing.

Follows from: privacy, reliability.

### Capability-based, deny by default

No implicit access. Every sensitive resource — files, network, hardware, memory, other apps — is mediated by an explicit named capability declared in a manifest and granted by the user.

Follows from: security, privacy.

### Memory is a system service

Memory is OS-level, not per-app. Its structure is defined by the system. The user can inspect, edit, export, and delete.

Follows from: privacy, reliability.

### Hardware-aware from the kernel up

The system knows what hardware it is on. Apps query the manifest; they do not assume. Hardware events are first-class.

Follows from: reliability, performance.

### Capability gate enforces regardless of agent intent

The agent can be persuaded (by prompt injection, by adversarial content, by user request) to want to violate a capability. The gate denies. Identity invariants cannot be overridden by any external content.

Follows from: safety, security, privacy.

### Reversible by default

Actions the agent takes are reversible where physically possible. Irreversible actions require explicit confirmation.

Follows from: safety, reliability.

### Honest behavior

The agent does not pretend. It says "I don't know" when it doesn't. It does not invent capabilities it lacks. It discloses what it has done when asked.

Follows from: safety, privacy.

### Auditable by construction

Every capability decision and every significant action is recorded in an append-only, hash-chained audit log. The user can inspect the log. Tampering is detectable.

Follows from: security, privacy.

### Rust where it matters

Privileged code (the agent harness, sandbox, memory subsystem, cryptography) is Rust. C is permitted at the FFI boundary. Other languages are permitted in apps via the binary ABI and in models via wasmtime.

Follows from: security, reliability.

### Appliance shape

The OS is single-purpose. Decisions that turn Kiki into a generalist Linux distribution are rejected. The user does not see Linux internals.

Follows from: paradigm. Constrains: convenience (we sometimes lose generic Linux affordances).

### OCI-native distribution

All artifacts are signed OCI artifacts in federated registries. There is no parallel package manager track for end users.

Follows from: security, paradigm.

### Inherit, don't fork

The OS is composed from upstream inputs (kernel, glibc, drivers, userspace libraries). We do not maintain forks of upstream packages. If a fix is needed upstream, we contribute it upstream.

Follows from: reliability (less to maintain), security (broader surface for review).

## Consequences

- The capability taxonomy is large and explicit. Every action that could violate privacy or security has a named capability.
- The audit log is mandatory. There is no "lite" mode without it.
- Cloud backends are replaceable. The protocol is open.
- The user can always export their data and disable any feature.
- We choose Linux kernel + systemd + bootc + image-based atomic semantics over more novel options because reliability dominates novelty at the system layer.
- We reject features that contradict the appliance paradigm even when they would be convenient.

## References

- `00-foundations/VISION.md`
- `00-foundations/PARADIGM.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/HARDCODED-RESTRICTIONS.md`
- `10-security/AUDIT-LOG.md`
## Graph links

[[VISION]]  [[PARADIGM]]
