---
id: memory-sync
title: Memory Sync
type: SPEC
status: draft
version: 0.0.0
implements: [memory-sync]
depends_on:
  - backend-contract
  - device-auth
  - memory-architecture
  - bitemporal-facts
  - cryptography
depended_on_by:
  - self-hosting
last_updated: 2026-04-30
---
# Memory Sync

## Purpose

Specify the optional cross-device memory sync service: end-to-end encrypted, bitemporal-aware, and respecting per-layer policies. Sync is opt-in and per-layer; the user decides which memory crosses devices.

## Privacy guarantees

- **End-to-end encrypted.** The backend never sees plaintext memory.
- **User-held keys.** Encryption keys are derived on-device from a user secret (homed-managed); the backend stores ciphertext only.
- **Per-layer opt-in.** Identity, semantic, episodic, procedural sync independently. Working and sensory never sync.
- **Auditable.** Every sync action is logged on each device.

## Architecture

```
device A                       sync service                device B
                                  │
encrypt fact ──────POST(ct)─────▶ store ─────GET────────▶ decrypt fact
                                                            │
                                                            apply
```

The service is a CRDT-style log of opaque ciphertexts. Devices push and pull the log; conflict resolution happens on each device after decryption.

## What syncs

```
identity        opt-in; small; the most useful to sync
                  (you want SOUL.md consistent on your phone and home)
semantic        opt-in; the entity facts
episodic        opt-in; per-session summaries (raw turns optional)
procedural      opt-in; recipes
audit           opt-in; per-device audit appended to a per-user log
```

Working memory does not sync (transient).
Sensory does not sync (RAM-only).

## Encryption

- Per-corpus symmetric key derived from a user master key
- AES-GCM-256 for record encryption
- Records carry a signed envelope with sender device id (for accountability) and a CRDT vector clock

The user master key is derived from:

- Their homed account passphrase, or
- A recovery secret saved at provisioning

Re-keying is supported; old records re-encrypt as background work.

## CRDT log

Each corpus is a log of records. Records have:

- Sender device id
- Vector clock
- Ciphertext payload
- Sender signature

Devices append; the backend orders by upload time and serves a paginated stream. Each device replays from its last seen vector clock.

## Conflict resolution

Memory layers have natural conflict semantics:

- Identity (Markdown): git-style three-way merge after decrypt; user resolves
- Semantic (bitemporal facts): bitemporal merge — both transactions apply; supersession via vector-clock tiebreak; surface to user on real conflicts
- Episodic (append-only): no conflicts (append-only)
- Procedural (files): file-level merge; conflicting recipes prompt user

The classifier surfaces hard conflicts via the consent flow (see `CONTRADICTION-RESOLUTION.md`).

## Consistency

Eventual. Devices catch up when online. Most-recent-wins is *not* the default — bitemporal data preserves history, and identity uses three-way merge.

## Bandwidth

Sync is small most of the time:

- A new identity edit: <1KB
- A new semantic fact: <1KB
- A session summary: a few KB
- Episodic raw turns (if opted in): can be MB; rate-limited

A device on a metered link can defer non-essential sync.

## Backend storage

The backend stores per-user, per-corpus, encrypted records:

```
/users/<user-id>/corpora/<corpus>/records/<record-id>.bin
```

Quotas per user (default 1GB; configurable). Old records garbage-collected after retention.

## Backup

The encrypted log itself is a usable backup. Restoring a wiped device is a re-pair + sync replay; the device decrypts with the user's master key (which the user re-derives from their account credentials).

## Self-hosted sync

A reference Rust service implements the sync protocol; runs on any cloud or LAN. Database: PostgreSQL or SQLite for small deployments.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Backend unreachable              | queue locally; flush when      |
|                                  | available                       |
| Decryption fails (key rotated    | trigger re-key flow            |
| out of sync)                     |                                |
| Conflict at semantic layer       | resolve via                    |
|                                  | CONTRADICTION-RESOLUTION.md     |
| Quota exhausted                  | refuse new uploads; alert user |
| Replay diverges                  | refuse; surface; user resolves |

## Acceptance criteria

- [ ] Per-layer opt-in works
- [ ] Backend never holds plaintext
- [ ] CRDT replay produces consistent state on both devices
- [ ] Conflict resolution surfaces correctly
- [ ] Re-key flow tested
- [ ] Self-hosted reference works

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/DEVICE-AUTH.md`
- `09-backend/SELF-HOSTING.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/IDENTITY-FILES.md`
- `04-memory/BITEMPORAL-FACTS.md`
- `04-memory/CONTRADICTION-RESOLUTION.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/PRIVACY-MODEL.md`
