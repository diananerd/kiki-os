---
id: hardcoded-restrictions
title: Hardcoded Restrictions
type: SPEC
status: draft
version: 0.0.0
implements: [hardcoded-restrictions]
depends_on:
  - principles
  - capability-gate
  - identity-files
  - drift-mitigation
depended_on_by: []
last_updated: 2026-04-29
---
# Hardcoded Restrictions

## Purpose

Specify the small set of behaviors the platform refuses unconditionally: what they are, why they are hardcoded, where they are enforced, and how they relate to the user's authority over their device.

These restrictions cannot be granted away. They are part of the platform's identity.

## Behavior

### Why hardcode anything

The platform principle is that the user is sovereign over their device. Hardcoding is in tension with that.

We hardcode nonetheless because some behaviors:

- Cannot be made safe by user-level grants alone.
- Would harm parties outside the user.
- Would compromise the platform's integrity in ways that affect others (supply chain attacks).
- Embody design choices we are unwilling to compromise.

The list is short and specific. Each entry has a reason.

### The list

```
1. The agent does not facilitate sexual content involving minors.

2. The agent does not assist with credible plans for violence against
   specific persons.

3. The agent does not assist with synthesis or acquisition of chemical,
   biological, radiological, or nuclear weapons capable of mass casualties.

4. The agent does not generate or facilitate deepfakes for non-consenting
   impersonation of identifiable individuals.

5. The capability gate cannot be bypassed by any in-band instruction;
   only the gate's grant table authorizes.

6. Identity files (SOUL.md, USER.md) cannot be modified outside the
   consent flow.

7. The audit log cannot be silently rewritten; deletion requires the
   audit-maintenance API which itself logs.

8. Hardware kill switches (where present) cannot be overridden in
   software.

9. The platform does not include functionality intended for covert
   surveillance of one user by another.
```

### Where each is enforced

#### 1. Sexual content involving minors

- Built into the agent's training and prompted refusals.
- The hardcoded restriction is a backstop; the model itself should refuse.
- The platform additionally:
  - Will not store such generated content.
  - Will not allow apps that produce/process such content.

This is an absolute prohibition. The user cannot opt in.

#### 2. Violence against specific persons

The agent refuses requests for:

- Specific targeting of identified individuals.
- Operational planning for harm.

General questions (history, news, fiction with disclaimers) are not restricted. The line is at credible operational assistance.

#### 3. CBRN weapons

The agent refuses substantive technical assistance for:

- Synthesis of biological agents capable of mass casualties.
- Synthesis of chemical weapons of mass destruction.
- Acquisition or design of radiological dispersal devices.
- Nuclear weapons technical information beyond what's in general public discourse.

General education about history, deterrence, and policy is not restricted.

#### 4. Non-consenting deepfakes

The agent refuses to:

- Generate audio deepfakes of identifiable real persons (using their voice samples without consent).
- Generate visual deepfakes of identifiable real persons.

The user can use voice/image generation for fictional characters, themselves, and consenting subjects.

#### 5. Capability gate bypass

The capability gate is enforced in code. No content (no prompt, no agent reasoning, no app-claimed status) can bypass:

- Calls go through the gate.
- Decisions are based on the grant table.
- The gate's source of truth is its grant table, not in-band text.

This is structural enforcement.

#### 6. Identity files outside consent flow

Identity files have:

- Filesystem permissions denying writes from non-consent-flow paths.
- Built-in `BeforeMemoryWrite(identity)` hook that denies bypass attempts.
- Sandbox profiles preventing direct writes.

A compromised app or model cannot write identity. The consent flow is the only path.

#### 7. Audit log integrity

The audit log:

- Append-only API.
- ct-merkle hash chain across entries.
- Maintenance API (deletion, rotation) is itself logged.
- A forced silent deletion would break the chain → detection.

#### 8. Hardware kill switches

Where present:

- Implemented at the HAL or below (firmware).
- Software cannot override (the hardware physically disconnects mic / camera / radio).
- The platform respects the switch state; no UI claims it's off when the hardware switch is on (or vice versa).

#### 9. No covert surveillance functionality

The platform does not include features for:

- One user spying on another's voice activity.
- One user reading another's memory.
- One user controlling another's device without knowledge.

The platform's multi-user model is open: users see the device's state and what's happening. Privacy across users is maintained, but surveillance of one user by another using platform features is not supported.

### Distinction: refusals vs restrictions

The platform distinguishes:

- **Refusals**: things the agent declines to help with based on its values, but the user can sometimes override (or the line shifts based on context). Model-level.
- **Restrictions**: hardcoded; cannot be overridden by any user, app, or grant.

This document covers restrictions only.

### Updates to this list

The list can change only through:

- An RFC with broad review.
- Public discussion.
- An OS update.

Adding a restriction is serious. Removing one is similarly serious. The list grows slowly and intentionally.

### Where the agent's reasoning and platform meet

The agent's identity (SOUL + IDENTITY) refers to these restrictions. The agent says "I won't do that" because it knows. But knowing is not the only enforcement: even if a clever instruction made the model think it was fine, the runtime would still refuse:

- Capability gate denies regardless of agent claims.
- Identity write denied regardless of agent claims.
- Audit log append-only regardless of agent claims.

Code prevails. The agent's understanding and the runtime's behavior are aligned but the runtime is authoritative.

### User authority

The user owns their device. Within the limits above:

- They can grant any capability.
- They can install any app.
- They can edit their identity (via consent flow).
- They can disable any feature.
- They can wipe their device.
- They can replace the OS.

The hardcoded restrictions are about not helping with specific extreme harms, not about limiting user authority over their own life.

### Disagreement and override

We acknowledge: some users will disagree with specific hardcoded restrictions. The platform is open-source; the restrictions are visible. A user determined to remove them can fork the OS.

We do not stop forks. We do not call them illegitimate. We state the restrictions clearly so users know what they're choosing when they pick stock vs fork.

The default platform has these restrictions. That is the contract for what "Kiki OS" provides.

## Interfaces

### Documentation

- This document for the canonical list.
- The agent's identity references these.
- The capability taxonomy mirrors them.
- The drift mitigation hooks enforce a subset.

### CLI

```
agentctl policy restrictions          # show the canonical list
```

(There is no CLI to disable them. By design.)

## State

The list is static, encoded in the platform's source. No runtime state.

## Failure modes

| Failure | Response |
|---|---|
| An action would violate a restriction | refuse; audit log; explain to user |
| The restriction itself is ambiguous in a corner case | a bug fix (rare); CVE if it enables harm |
| A user demands an override | refuse; suggest fork if they strongly disagree |

## Performance contracts

The enforcement points are checked on every relevant action. Per-check overhead is negligible.

## Acceptance criteria

- [ ] All listed restrictions enforced.
- [ ] Each has documented enforcement point.
- [ ] No CLI / API to disable individual restrictions.
- [ ] The platform's source declares them (not just docs).
- [ ] Audit log records refusals.
- [ ] User-facing communication is honest about what's restricted and why.

## References

- `00-foundations/PRINCIPLES.md`
- `04-memory/IDENTITY-FILES.md`
- `04-memory/CONSENT-FLOW.md`
- `04-memory/DRIFT-MITIGATION.md`
- `03-runtime/CAPABILITY-GATE.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/AUDIT-LOG.md`
