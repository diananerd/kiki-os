---
id: device-provisioning
title: Device Provisioning
type: SPEC
status: draft
version: 0.0.0
implements: [device-provisioning]
depends_on:
  - backend-contract
  - device-auth
  - identity-files
  - consent-flow
  - verified-boot
depended_on_by: []
last_updated: 2026-04-30
---
# Device Provisioning

## Purpose

Specify the first-boot enrollment flow: a Kiki device goes from "fresh image" to "this device is mine, with my account, with my profile, signed in to my chosen backend." Provisioning is intentionally deliberate; the user is choosing trust anchors.

## Inputs

- A flashed Kiki image
- A user (with an account on a backend, or the intent to create one)
- Optional: a paired existing Kiki device for transfer
- Optional: a passphrase to set up

## Outputs

- A provisioned device with its cert
- A user identity (SOUL/IDENTITY/USER baseline)
- A chosen profile applied
- A device-to-backend binding
- An audit entry recording the provisioning

## Flow

```
1. Boot. Verified boot succeeds. /var is fresh (BTRFS subvol seeded).
2. provisioning UI starts (interactive_ephemeral app).
3. Pick locale, accessibility, time zone.
4. Pick or create user account:
   - Option A: scan a QR / enter a code from an existing paired
     device → recovery flow
   - Option B: sign in to a backend account (or create one) → standard
   - Option C: local-only (no backend; can be added later)
5. Generate device key pair; send CSR to chosen backend (or skip).
6. Receive cert; install.
7. Pick a profile (default, kid-friendly, accessibility-first, ...).
8. Initialize identity files (per profile + user input).
9. Optionally enroll voice (wake-word phrase, voice print).
10. Optionally connect Wi-Fi / configure networking.
11. Display setup summary; user confirms.
12. Audit entry.
13. Ready.
```

## Networking

Provisioning works:

- **Online**: connects to the backend; full enrollment.
- **Offline**: local-only setup; device can be paired with a backend later.

Air-gapped enterprise setups can use a local backend; the provisioning flow points to it.

## Recovery flow

If the user has an existing Kiki device and wants to set up a new one:

- New device displays a QR code (or numeric code)
- Existing device scans / enters
- Existing device authorizes the new one (consent flow on the existing)
- New device receives:
  - User account binding
  - Recovery seed (encrypted)
  - Suggested profile

The new device still gets its own cert; recovery is about user binding, not cert sharing.

## Identity bootstrap

The provisioning flow seeds the identity files with:

- The user's name, pronouns, language (entered)
- Profile defaults (e.g., kid-friendly applies a SOUL extension)
- A starter SOUL fragment (system default)
- An empty USER.md the user expands later

The consent flow runs at the end; the user reviews the seeded files before they're committed.

## Voice enrollment

Optional. If skipped, the device works with default-foreground-user heuristics. Enrollment writes the voice print under the user's directory.

## Wi-Fi

Wi-Fi can be configured by:

- Scanning a QR with WPA passphrase encoding
- Entering manually
- Bluetooth handoff from a phone

Networking is the boring-and-important step; we cover the obvious cases.

## Hardware kill switches

The provisioning UI verifies hardware kill switches work (visible to the user):

- Mic kill: shows "Listening: off" when toggled
- Camera kill: same
- Radio kill: same

This builds the user's confidence in their physical controls.

## Multi-user

A device shipped to a household supports multiple users. After the first user, additional users can be added in Settings (a slimmer flow that reuses the same patterns).

## Auditing

Provisioning emits a single composite audit event:

```
{
  "category": "provisioning",
  "event_kind": "completed",
  "actor": {"kind": "user", "id": "user-1"},
  "payload": {
    "backend": "...",
    "profile": "kiki:profiles/default@2.0.0",
    "voice_enrolled": true,
    "...": "..."
  }
}
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Backend unreachable              | offer local-only setup; can    |
|                                  | enroll later                    |
| Verified boot fails              | refuse to provision; recovery  |
|                                  | mode                            |
| User cancels mid-flow            | preserve what's set; allow     |
|                                  | resume                          |
| Hardware attestation fails       | enroll at lower trust tier or  |
|                                  | refuse, per backend policy     |

## Acceptance criteria

- [ ] All entry paths work (online / offline / recovery)
- [ ] Identity bootstrap produces valid files
- [ ] Voice enrollment optional; works when chosen
- [ ] Hardware kill switch self-test included
- [ ] Audit event captures provisioning summary
- [ ] Multi-user flow available after first user

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/DEVICE-AUTH.md`
- `04-memory/IDENTITY-FILES.md`
- `04-memory/CONSENT-FLOW.md`
- `08-voice/SPEAKER-ID.md`
- `10-security/VERIFIED-BOOT.md`
- `02-platform/HARDWARE-KILL-SWITCHES.md`
