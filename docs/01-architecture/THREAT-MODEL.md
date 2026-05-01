---
id: threat-model
title: Threat Model
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - principles
  - trust-boundaries
  - system-overview
depended_on_by:
  - anti-patterns
  - camel-pattern
last_updated: 2026-04-30
---
# Threat Model

## Problem

A system this exposed needs an explicit accounting of what it defends against and what it does not. Without one, security decisions become reactive: patching the last attack rather than anticipating the next class of attacks.

## Constraints

- Must enumerate concrete adversary categories, not vague threats.
- Must state explicitly what is out of scope.
- Must connect each defense to the boundaries that enforce it.
- Must be reviewable: every claim is testable.

## Decision

Eight categories of adversary, ordered by approximate prevalence. For each: what they want, how they reach Kiki, what we defend with, what we accept losing.

## A1 — Opportunistic attacker

**Profile.** Mass attacker not targeting any specific user. Spammers, malware distributors, fraudsters operating at scale.

**Goals.** Compute theft (mining), botnet recruitment, credential theft, ransomware, data harvesting for resale.

**Reach paths.**

- A malicious app published to a registry pretending to be useful.
- A typo-squatted namespace.
- A compromised dependency in an otherwise legitimate app.
- A drive-by exploit through the embedded web engine (Servo).
- A weak credential on a backend account.

**Defenses.**

- Container sandbox + capability gate (limits what an app can do).
- cosign per-namespace signing (forged signatures detected).
- Namespace registry curation (catches typo-squats and obvious malicious namespaces).
- Mandatory consent for sensitive capabilities (the user notices).
- Rate limits on backend APIs (slows at-scale abuse).
- Encrypted storage at rest (data on a stolen device is not free).

**Accepted losses.** A user who explicitly grants every capability to a deceptive app gives that app the ability to do what its capabilities permit. Visibility (audit log) is the recovery mechanism.

## A2 — Targeted attacker

**Profile.** Motivated adversary going after a specific user or organization. Industrial espionage, intimate-partner abuse, journalist intimidation, executive targeting.

**Goals.** Surveillance, theft of specific information, persistent tracking, plausible deniability.

**Reach paths.**

- Social engineering: convincing the user to install something or grant a capability.
- Physical access to the user's device.
- Network MITM on hostile networks.
- Compromise of a service the user already trusts.
- Supply chain compromise (a maintainer's signing key).

**Defenses.**

- Hardware-coupled privacy LEDs (camera/mic activity always visible when hardware supports them).
- Hardware kill switches (cannot be bypassed in software when hardware supports them).
- Verified boot via systemd-boot + UKI (detects firmware tampering).
- TPM PCR-sealed disk encryption (physical access does not free the data).
- Capability auditing (the user can see what's been accessed).
- mTLS for backend connections.
- Reproducible OS images (supply chain visibility).
- cosign signature verification on every artifact pull.
- Sigstore witness submission opt-in for non-repudiation.

**Accepted losses.** A nation-state-class actor with sustained physical access defeats most defenses. We make the bar high; we do not claim it cannot be cleared.

## A3 — Hostile insider

**Profile.** Someone with legitimate access who misuses it. Family member with the password, employee, child trying to bypass parental controls.

**Goals.** Bypass intended limits, access data they shouldn't, modify state to hide actions.

**Defenses.**

- Capability auditing visible to the user.
- Audit log tamper-evident (ct-merkle hash chain; opt-in sigsum witness).
- Multi-user separation: each user's data is scoped (per-user encrypted home via systemd-homed).
- Physical kill switches the user can verify.
- Identity protection: changes to USER.md require explicit consent through the consent flow.

**Accepted losses.** A user who genuinely shares everything with their household has limited recourse against a household member who turns against them. We default to per-user privacy; the user can choose to share more.

## A4 — State actor

**Profile.** Sophisticated, well-resourced, often legally authorized in their own jurisdiction.

**Goals.** Mass surveillance, targeted surveillance, compelled cooperation, device disabling during civil unrest.

**Defenses.**

- The OS is open source. A back door we added would be visible.
- Architectural privacy. The backend cannot give an attacker data the backend doesn't have. Memory sync is end-to-end encrypted with user keys; the backend stores ciphertext.
- Encrypted device storage (LUKS2 + TPM PCR sealing).
- mTLS device authentication.
- The right to refuse architectural changes that compromise users.
- Decentralized: devices work without the backend, alternative backends are possible, namespace registries can be replaced.

**Accepted losses.** We cannot defeat a state actor with unlimited resources targeting a specific user. We can ensure that the architecture does not create blanket surveillance capabilities.

## A5 — Ecosystem-poisoner

**Profile.** Attacker targeting the ecosystem rather than individual devices. Malicious package author who builds reputation then poisons their package. Skill author teaching the agent harmful patterns. Component author with subtle vulnerabilities.

**Goals.** A platform-level foothold that scales, reputation arbitrage, indirect access to many users.

**Defenses.**

- Strong publisher identity for namespace registrations (per-namespace cosign keys).
- Reputation systems and rate limits on namespace registrations.
- Anomaly detection on backend telemetry (when telemetry is opted in).
- Rapid takedown via cosign revocation in Sigstore Rekor.
- Capability scoping limits per-app blast radius.
- Optional Sigstore witness submission for non-repudiation: poisoners cannot deny what they signed.

**Accepted losses.** A first-of-its-kind attack campaign may succeed at small scale before detection. We minimize the window through monitoring and the blast radius through capabilities.

## A6 — Protocol exploiter

**Profile.** Attacker against Kiki at the protocol level rather than application level. Crafted Cap'n Proto frames exploiting a deserialization bug. Crafted SOUL.md content exploiting the agent's parser. Malformed OCI manifest.

**Goals.** Sandbox escape via memory corruption, privilege escalation via parser bugs, tool injection, identity bleed.

**Defenses.**

- Rust as the implementation language for protocol code.
- Schema validation at every protocol boundary (Cap'n Proto's typed schema, JSON Schema for declarations).
- Capability checks regardless of how a request was crafted.
- Sandboxed deserialization in untrusted contexts (containers, wasmtime).
- Adversarial testing (fuzzing of parsers and protocols).

**Accepted losses.** Zero-day vulnerabilities in our parsers will exist. We minimize through Rust's memory safety, fuzzing, and defense in depth.

## A7 — Agent manipulator

**Profile.** Attacker manipulating the agent itself. Prompt injection in user-facing content. Adversarial inputs in voice. Tool results crafted to hijack subsequent reasoning. Memory poisoning.

**Goals.** The agent takes actions the user would not authorize. The agent leaks information it shouldn't. The agent's identity drifts toward attacker-favorable behavior.

**Defenses.**

- Capability gate enforces regardless of agent intent. Persuading the agent to want to violate a capability does not allow the violation.
- Hardcoded identity invariants the agent cannot remove.
- Source provenance in memory; content from external sources is weighted accordingly.
- Drift detection (compaction count, contradiction queue, sycophancy patterns, identity invariant checks).
- Subagent isolation: a manipulated subagent cannot poison the primary agent (sidechain JSONL pattern, Coordinator/Worker capability scoping).
- Mailbox approval pattern for risky actions.
- Arbiter classifier with input minimization (sees only user prompt + tool call descriptor, not agent prose).
- CaMeL pattern for tools touching the lethal trifecta (split privileged planner / quarantined parser).

**Accepted losses.** The agent can be made to give subtly misleading answers to a user via influenced inputs. We mitigate with provenance and audit; we cannot fully prevent the failure mode.

## A8 — Accidental adversary

**Profile.** Not malicious, but causing damage. Buggy app, user error, misconfigured deployment, memory leak, bad firmware update.

**Defenses.**

- Crash isolation (one app crashes; others continue).
- Resource budgets (cgroups).
- Atomic OTA with rollback (bootc).
- Conservative defaults.
- User-recoverable failure modes (no bricking; recovery boot path).

**Accepted losses.** Bugs will exist. We minimize by using Rust, testing thoroughly, and making recovery paths user-accessible.

## Out of scope

The following are deliberately not addressed by the architecture.

- A user explicitly granting every capability to a malicious app.
- A user installing alternative firmware that disables defenses.
- A determined nation-state with physical access and time.
- Sophisticated prompt injection that the user does not detect.
- Hardware supply chain compromise that defeats verified boot (e.g., compromised firmware keys at the silicon vendor).
- Physical attacks on running silicon (probing RAM during operation).
- Errors in our own code (we have these; we patch them).

## Defense layers and their boundaries

Mapping defenses to the boundaries they cross:

| Defense | Boundary | Reference |
|---|---|---|
| Verified boot (UKI + dm-verity) | 1, 2 | `10-security/VERIFIED-BOOT.md` |
| Hardware manifest signature | 1 | `02-platform/HARDWARE-MANIFEST.md` |
| Kernel sandbox (Landlock+seccomp) | 2 | `02-platform/SANDBOX.md` |
| Container runtime (podman+crun) | 2 | `02-platform/CONTAINER-RUNTIME.md` |
| Capability gate | 3 | `03-runtime/CAPABILITY-GATE.md` |
| Per-app netns | 5 | `02-platform/NETWORK-STACK.md` |
| mTLS device auth | 6 | `09-backend/DEVICE-AUTH.md` |
| Inference router privacy | 6 | `03-runtime/INFERENCE-ROUTER.md` |
| cosign signature verification | 6 | `10-security/COSIGN-TRUST.md` |
| Audit log (ct-merkle) | all | `10-security/AUDIT-LOG.md` |
| Identity consent flow | 7 | `04-memory/CONSENT-FLOW.md` |
| Drift mitigation | 8 | `04-memory/DRIFT-MITIGATION.md` |
| Hardcoded restrictions | 8 | `10-security/HARDCODED-RESTRICTIONS.md` |
| CaMeL pattern (trifecta tools) | 8 | `10-security/CAMEL-PATTERN.md` |
| Encrypted storage | physical | `10-security/STORAGE-ENCRYPTION.md` |

## Operational threat model maintenance

- Reviewed quarterly. New adversary categories added when observed in the wild or in research.
- Each new SPEC must declare which adversaries it defends against and which it does not.
- Penetration testing of major releases is performed by an independent party.
- Vulnerability disclosure follows `10-security/VULNERABILITY-DISCLOSURE.md`.
- Sigstore witness logs (when opted in) provide non-repudiable history of artifact publication.

## Consequences

- Every defensive capability in the architecture maps to a specific adversary in this document. Defenses without a named adversary are scrutinized.
- Adversaries we do not defend against are stated explicitly. This guides where users should add their own operational precautions.
- The audit log is mandatory. It is the recovery mechanism when any defense fails.
- The capability gate is the most security-critical component. Its correctness is the dominant determinant of attack containment.

## References

- `01-architecture/TRUST-BOUNDARIES.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/PRIVACY-MODEL.md`
- `10-security/AUDIT-LOG.md`
- `10-security/ANTI-PATTERNS.md`
- `10-security/VULNERABILITY-DISCLOSURE.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
## Graph links

[[PRINCIPLES]]  [[TRUST-BOUNDARIES]]  [[SYSTEM-OVERVIEW]]
