---
id: fleet-management
title: Fleet Management
type: SPEC
status: draft
version: 0.0.0
implements: [fleet-management]
depends_on:
  - remote-architecture
  - remote-protocol
  - device-pairing
  - remote-config-sync
  - capability-taxonomy
last_updated: 2026-04-30
---
# Fleet Management

## Purpose

Specify multi-device orchestration: how a user (or organization admin) sees and operates a set of Kiki devices coherently. Fleet management is for households with several devices, organizations with employee or kiosk fleets, and developers running test devices.

## Scope

A fleet is a *named* collection of paired devices belonging to one user account (or one org). Each device retains its sovereignty; the fleet adds a coordinated view.

## Operations

```
list / discover devices in fleet
view per-device health and status
push a profile to selected devices
push an app install to selected devices
revoke pairings across the fleet
collect (read-only) audit summary across devices
delegate an action ("ask my office Kiki to ...")
```

Every operation goes through the targeted device's pairing scope and capability gate. Nothing in fleet management bypasses the device's authority.

## Topology

For a personal household:

```
user
  └── fleet "Casa"
        ├── device "Living Room"
        ├── device "Office"
        └── device "Phone Companion"
```

For an organization:

```
org
  └── unit "Madrid Office"
        ├── fleet "Front Desk Kiosks"
        │     └── 6 devices
        └── fleet "Engineering Workstations"
              └── 12 devices
```

## Backend role

The backend hosts the fleet directory and the dispatcher:

- Directory of devices (id, name, last seen, profile, version)
- Push relay for fleet operations
- Audit aggregation (read-only summary)

Heavy operations (install an app on 50 devices) are issued by the admin's client; the backend relays to each device; each device decides locally and reports back.

## Org admin model

For org fleets:

- Admin accounts have permissions over devices in the org
- A device's pairing with an admin grants org-scoped capabilities
- Per-device, per-user grants still apply
- Device's user can still revoke admin access (subject to lease terms in formal deployments)

## Profiles for fleets

A profile (per `PROFILE-OCI-FORMAT.md`) is the natural unit for fleet configuration:

```
admin: kiki fleet apply kiki:profiles/kiosk-museum@1.0 \
         --to=fleet:front-desk-kiosks
```

Each device receives the profile, runs its own consent/apply path, reports status.

## Health view

```
GET /v1/fleets/<fleet-id>/health
{
  "devices": [
    { "id": "...", "online": true, "version": "...",
      "profile": "...", "advisories": [], "last_audit": "..." }
  ],
  "summary": { "online": 11, "offline": 1,
               "advisories_pending": 0 }
}
```

Surfaced in the admin's remote client.

## Push notifications

Admins can push messages to devices ("please install the update"); the device renders via the mailbox. Devices respect DND and presence; the user can ignore.

## Audit aggregation

The backend can collect audit summaries across the fleet (counts, denied operations, failures) for compliance reporting. *Detailed* audit content stays on each device unless the device's policy permits sharing.

## Access control

Fleet operations require an admin pairing scope:

```toml
[scope.capabilities]
fleet.read = true
fleet.push_profile = true
fleet.push_install = true
fleet.summarize_audit = true
```

A regular user pairing has `fleet.read` for their own devices but not push.

## Self-hosted fleet

A self-hosted backend handles fleet directory + dispatcher. The reference implementation includes this; org-scale deployments customize.

## Cross-device delegation

A user can ask their primary device to delegate to another:

> "Ask my office Kiki to summarize today's email."

The primary calls the office device via the remote protocol. The user's pairing scope on the office device must grant the operation. Audit logs both sides.

## Privacy

- Per-user fleets visible only to the user
- Org fleets visible to admins; per-device user data not exposed
- Push relays carry encrypted payloads

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Device offline during push       | queue; deliver when online     |
| Profile apply fails on a device  | per-device report; admin       |
|                                  | reviews                         |
| Admin revoked mid-operation      | operation aborts on remaining  |
|                                  | devices                         |
| Audit collection denied by       | summary excludes that device   |
| device policy                    |                                |

## Acceptance criteria

- [ ] Fleet directory queries return correct online state
- [ ] Profile push reaches all targeted devices
- [ ] Per-device gating preserved
- [ ] Org admin separation works
- [ ] Audit summary aggregation respects per-device policy
- [ ] Self-hosted fleet backend reference works

## References

- `13-remotes/REMOTE-ARCHITECTURE.md`
- `13-remotes/REMOTE-PROTOCOL.md`
- `13-remotes/DEVICE-PAIRING.md`
- `13-remotes/REMOTE-CONFIG-SYNC.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/SELF-HOSTING.md`
- `10-security/AUDIT-LOG.md`
## Graph links

[[REMOTE-ARCHITECTURE]]  [[REMOTE-PROTOCOL]]  [[DEVICE-PAIRING]]  [[REMOTE-CONFIG-SYNC]]  [[CAPABILITY-TAXONOMY]]
