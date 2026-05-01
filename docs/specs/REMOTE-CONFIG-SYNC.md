---
id: remote-config-sync
title: Remote Config Sync
type: SPEC
status: draft
version: 0.0.0
implements: [remote-config-sync]
depends_on:
  - remote-architecture
  - remote-protocol
  - device-pairing
depended_on_by:
  - fleet-management
last_updated: 2026-04-30
---
# Remote Config Sync

## Purpose

Specify how settings, preferences, and per-app configuration sync between a user's Kiki devices and remote clients. Distinct from memory sync (which carries identity and facts); this is the *settings* layer — themes, accessibility prefs, app configs, capability grants the user has approved.

## What syncs

```
theme + design tokens overrides
accessibility preferences
notification rules (DND, importance)
locale + time zone
voice preferences (default voice, sensitivities)
per-app settings (subset apps opt in)
capability grants (per-app, per-device)
focus-mode rules
```

## What does NOT sync

- Identity files (those go through memory sync explicitly)
- Audit logs (those have their own sync per device)
- Pairing certs (per-device)
- Workspaces and their state (each device has its own)
- Sensory and working memory (transient)

## Architecture

A small CRDT log per user, similar to memory sync but lower-volume:

```
device A ── encrypted setting change ── sync server ──▶ device B
```

End-to-end encrypted; the server stores ciphertext only. Devices apply changes after decryption.

## Conflict resolution

Per-key:

- Last-writer-wins for scalar settings (theme, locale)
- Three-way merge for structured settings (per-app preferences)
- User prompt for capability grants conflicts ("device A granted X, device B revoked X — which wins?")

## Per-app opt-in

An app's manifest can declare settings sync:

```toml
[settings_sync]
sync = true
include = ["preferred_sources", "default_voice"]
exclude = ["device_specific.*"]
```

By default, app settings are device-local. Apps that benefit from cross-device consistency (a music player remembering preferences) opt in.

## Privacy

- Encrypted at rest on the sync server
- Per-user master key (homed-derived) encrypts the corpus
- The sync service runs alongside memory sync (often the same backend)

## Bandwidth

Settings sync is small (kilobytes per change). Defers gracefully on metered links.

## Capability grants

Capability grants sync with a special handling: a grant accepted on one device propagates to others, but each device's gate verifies the grant against the local context (e.g., the network grant uses the local network's hosts).

A revocation propagates immediately and is non-conflicting (revocation always wins over grant in a tie).

## Per-device overrides

A device can override a synced setting:

```
device-overrides:
  ui.theme = "high-contrast-dark"     (overrides the synced "default-light")
```

Overrides survive sync; show as "overridden locally" in Settings.

## CLI

```
kiki sync settings status
kiki sync settings push
kiki sync settings pull
kiki sync settings conflicts
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Sync server unreachable          | queue locally; flush later     |
| Decryption fails                 | trigger re-key flow            |
| Capability grant conflict        | user prompt; lock until        |
|                                  | resolved                        |
| App settings schema mismatch     | log; per-key fallback          |

## Acceptance criteria

- [ ] Listed setting categories sync
- [ ] Per-app opt-in works
- [ ] Conflict resolution per setting type
- [ ] Per-device overrides preserved
- [ ] Capability grants propagate; revocations win
- [ ] CLI tools work

## References

- `13-remotes/REMOTE-ARCHITECTURE.md`
- `13-remotes/REMOTE-PROTOCOL.md`
- `13-remotes/FLEET-MANAGEMENT.md`
- `09-backend/MEMORY-SYNC.md`
- `04-memory/IDENTITY-FILES.md`
- `10-security/CAPABILITY-TAXONOMY.md`
