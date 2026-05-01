---
id: appliance-model
title: Appliance Model
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - paradigm
  - system-overview
depended_on_by:
  - process-model
  - upstream-choice
last_updated: 2026-04-30
---
# Appliance Model

## Problem

The paradigm declaration (Kiki as appliance OS for agentic computing) is abstract. Engineers need a concrete description of what the appliance shape means in practice: which directories are writable, which interfaces are exposed, what the user can and cannot do, how the system is operated, what is locked down, what is configurable. Without this concrete translation, "appliance" is interpreted differently by different contributors.

## Constraints

- The model must be operationally testable: every property is observable on a running device.
- It must be enforceable: violations are caught structurally, not by code review alone.
- It must be honest about user agency: the user owns the device but operates it through a specific surface.
- It must allow developer affordances without compromising the appliance shape for production users.

## Decision

The appliance model is the concrete operational manifestation of the paradigm. It is defined by ten properties.

### 1. Read-only base

`/usr` and the rest of the OS image are mounted read-only. The user cannot install packages, modify binaries, or edit system configuration files. Changes to the OS require a new image deployed atomically.

Enforcement: the filesystem mount is read-only at boot. dm-verity verifies content integrity. Any write attempt fails with EROFS.

### 2. Mutable but bounded `/var` and `/home`

`/var/lib/kiki/` and `/home/<user>/` are writable. They hold:

- Memory layer data (LanceDB, CozoDB, SQLite databases).
- Workspace state (canvas ops logs, snapshots).
- Per-app data directories (bind-mounted into containers).
- User configuration (per-user preferences).
- Identity files (SOUL, IDENTITY, USER) versioned in git.

Encryption at rest via LUKS2 with TPM-sealed keys. Per-user encrypted home via systemd-homed.

### 3. No user-facing package manager

The user does not run `apt`, `dnf`, `pacman`, or any equivalent. There is no `/etc/apt/sources.list`, no repos to add. App installation is done through the agent or `agentctl`, which are pure OCI clients.

See `14-rfcs/0005-no-package-manager-user-facing.md`.

### 4. No user-facing shell as primary interface

The OS does not expose a traditional Linux shell as the primary surface. There is no SSH service running by default. There is no terminal application installed by default.

A shell exists for system maintenance (debugging, recovery), accessed through:

- A recovery boot mode (only with physical access plus user authentication).
- A developer mode flag (off by default; if enabled, exposes a shell on a specific TTY).

Production users never see this surface.

### 5. Agent-only access for normal operation

The user interacts with Kiki through:

- The agent shell (`agentui`) in the GUI.
- Voice through the wake word + voice pipeline.
- `agentctl` for advanced administrative tasks (also opaque to Linux internals).

Everything the user does flows through the agent and its capability gate. The agent is the interface.

### 6. Declarative state

Every load-bearing piece of state is declared in a signed artifact:

- The OS image declares the base.
- The runtime sysext declares the agent harness.
- Profiles declare app permissions and configuration.
- The hardware manifest declares device capabilities.
- Identity files declare the agent's voice and the user's preferences.

Runtime state (mailbox queue, audit log, memory) is derivable from the declared artifacts plus user interaction. Drift — accidental state divergence — is detected and reconciled.

### 7. Atomic OTA

Updates are atomic. A failed update reverts via bootc rollback. There is no "partial update" state where some packages are new and some are old. The OS at any moment is exactly one signed image.

### 8. Signed end-to-end

Every artifact carries a cosign signature verified against a per-namespace public key:

- The OS image.
- The runtime sysext.
- Each app container.
- Each component, tool, profile, model, skill, bundle.

Trust is per-namespace, scoped, rotatable, revocable. There is no implicit trust path.

### 9. Capability-gated

Every sensitive action goes through `policyd`'s capability gate. The gate consults:

- The static profile of the requesting actor.
- Hardcoded restrictions (which cannot be overridden).
- The arbiter classifier for borderline cases.
- The audit log records the decision.

Apps cannot bypass the gate. The agent cannot bypass the gate. The user can grant capabilities via the consent flow, but cannot grant access to hardcoded restrictions.

### 10. Audit-by-construction

Every capability decision and every significant action is recorded in an append-only, hash-chained audit log. The user can inspect the log. Tampering is detectable.

## What this means concretely

### What the user can do

- Talk to the agent (text, voice).
- Install apps and components via the agent or `agentctl`.
- Grant or revoke capabilities for specific apps.
- View the audit log.
- Export their memory, workspace state, and identity.
- Wipe their device.
- Switch to a different backend (or run without a backend).
- Boot to recovery mode (with physical access).
- Enable developer mode (with explicit consent).
- Replace the OS entirely (forks of Kiki are explicitly permitted).

### What the user cannot do (in production mode)

- Install arbitrary Linux packages.
- Edit system configuration files.
- Run a shell on the system.
- SSH into the device.
- Replace components of the OS image individually.
- Bypass the capability gate.
- Modify identity files outside the consent flow.
- Tamper with the audit log.
- Disable hardcoded restrictions.

### What apps can do

- Run as containers under podman quadlet.
- Receive tool dispatch via Cap'n Proto.
- Access user data through capability-gated APIs.
- Render UI surfaces declared in their Profile.
- Subscribe to events on the service bus or DBus.
- Spawn subagents if their Profile permits.

### What apps cannot do

- Communicate directly with each other.
- Bypass the capability gate.
- Read files outside their declared filesystem capabilities.
- Reach hosts outside their declared network capabilities.
- Access kernel APIs directly.
- Persist state outside their bind-mounted data directory.

## Developer affordances

Production users see the appliance shape strictly. Developers building or contributing to Kiki need additional access. The model accommodates both:

- **Developer mode** is a boot flag. When enabled, an additional unit exposes a shell on TTY3 with a developer user. The flag is off by default; enabling it requires physical access and re-imaging.
- **Recovery mode** provides a minimal busybox shell for diagnostics. Always available with physical access.
- **`agentctl debug`** subcommands expose internal state (workspace dump, journal tail) to the user without dropping to a Linux shell.
- **App development** uses container builders (`buildah`, `podman build`) on a developer's own machine, then publishes signed OCI artifacts. The Kiki device runs these via standard install flow.

Developer mode does not weaken security — capabilities, signatures, and the audit log all continue. It exposes additional surface for inspection.

## Consequences

### Positive

- The user surface is minimal and consistent.
- The system's behavior is predictable and verifiable.
- Maintenance is bounded: we maintain only what we publish.
- Security is structural: violations are blocked by mechanism, not policy.
- Crashes and bugs are contained by atomic deployment and rollback.
- The opaque-to-user property holds even when developers work on the device.

### Negative

- We cannot serve users who want a general-purpose Linux they can endlessly customize.
- Some workflows (a developer accustomed to `apt-get install foo`) do not translate.
- Recovery from a broken state requires the recovery boot path, which is a different paradigm from "log in and fix it".
- Documentation must be careful to distinguish appliance (production) flow from developer flow.

## References

- `00-foundations/PARADIGM.md`
- `00-foundations/PRINCIPLES.md`
- `01-architecture/SYSTEM-OVERVIEW.md`
- `01-architecture/TRUST-BOUNDARIES.md`
- `02-platform/STORAGE-LAYOUT.md`
- `02-platform/IMAGE-COMPOSITION.md`
- `14-rfcs/0001-appliance-os-paradigm.md`
- `14-rfcs/0005-no-package-manager-user-facing.md`
