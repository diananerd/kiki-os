---
id: device-pairing
title: Device Pairing
type: SPEC
status: draft
version: 0.0.0
implements: [device-pairing]
depends_on:
  - remote-architecture
  - cryptography
  - device-auth
  - capability-taxonomy
  - audit-log
depended_on_by:
  - fleet-management
  - remote-client-platforms
  - remote-config-sync
  - remote-discovery
  - remote-protocol
last_updated: 2026-04-30
---
# Device Pairing

## Purpose

Specify the protocol for pairing a remote client with a Kiki device: key exchange, scope negotiation, persistent storage of pairing material, unpairing.

## Modes

- **QR pairing**: visual scan, in-person
- **Code pairing**: short numeric code
- **Recovery pairing**: using a passphrase saved at provisioning, or a challenge from a still-paired client
- **Backend-mediated**: pre-existing user account links new client (after MFA)

QR is smoothest; code is the fallback for cameraless clients; recovery is for re-pairing after loss; backend-mediated is for adding clients without in-person.

## QR pairing flow

```
1. User opens "add remote" on device or client.
   Device shows QR encoding: device-id, ephemeral pub key, nonce,
   short-lived rendezvous URL.
2. Client scans; decodes; generates its own ephemeral key pair.
3. Client connects to rendezvous URL with: its pub key, signed
   handshake (device's nonce + proposed scope + client metadata).
4. Device verifies; if valid, generates a long-term cert for the
   client and signs it.
5. Device returns: signed client cert, device's long-term cert + CA
   chain, granted scope (may narrow what client asked).
6. Client persists: client key, device-issued cert, device's pub key.
7. Device persists: pairing record (client id, scope, timestamps,
   public key).
8. Audit log entries on both sides.
9. Pairing complete; QR is single-use and expires.
```

QR rendezvous URL is short-lived (~60s).

## Code pairing flow

For clients without cameras:

- Device displays a 9-digit code (3-3-3 grouped) and a rendezvous URL
- User types both into the client
- Client connects; presents code + ephemeral key
- Device verifies code; remainder same as QR flow

Code is short-lived (60s), limited-attempt (3 tries before regenerating).

## Recovery pairing

If a user loses a paired client:

- New client requests a recovery pairing on the device
- Device prompts the user (on-device UI or voice) to confirm via:
  - A passphrase set at provisioning, or
  - A confirmation gesture, or
  - A challenge from a still-paired client
- On confirmation, normal pairing proceeds

Recovery is intentionally cumbersome — proves device proximity or possession of an existing pairing.

## Backend-mediated pairing

For fleet expansion without in-person:

- User signed in to a backend account that links their devices
- User signs in on the new client with the same account (with MFA)
- Backend issues a signed introduction
- Existing devices receive the introduction, present an on-device prompt ("approve adding <client> to your fleet?"); on approval, complete pairing

Convenient but requires backend involvement. The device's confirmation prevents a backend-only compromise from inserting clients silently.

## Pairing keys and certs

```
At the device:
  /var/lib/kiki/remote-pairings/<pairing-id>/
    ├── client-cert.pem            client's cert (we issued it)
    ├── client-pubkey.pem
    ├── scope.toml                 capabilities of this pairing
    ├── metadata.toml              client name, kind, created
    └── revoked                    presence = revoked

At the client:
  per-platform secure storage (Keychain, Credential Manager,
                               file-based encrypted)
    ├── device-cert.pem
    ├── device-pubkey.pem
    ├── client-cert.pem
    ├── client-key
    └── pairing-record.toml
```

The client's private key never leaves the client's secure storage. The device's never leaves the device.

## Pairing scope

Each pairing has a declared scope:

```toml
[scope]
client_name = "Phone — primary"
client_kind = "ios"
created_at = "2026-04-30T..."
created_via = "qr"
expires = ""

[scope.capabilities]
agent.command = true
agent.voice = true
agent.surface_observe = true
agent.proactive_receive = true

config.read = true
config.write = true

apps.list = true
apps.install = true
apps.uninstall = true

memory.read.episodic = false
memory.write.identity = false        # never granted via pairing

audit.read = true
fleet.discover = true
diagnostics.read = true
```

The pairing scope is a *ceiling*; per-call gates still apply.

## Per-pairing limits

- Concurrent active sessions (default 4)
- Maximum surface observation rate
- Maximum requests per minute
- Permitted hours (optional; e.g., "9-5 only")

## Multiple users on one device

A pairing belongs to one user (its scope is "act as user X"). A remote can switch active user only if the pairing's scope explicitly permits.

## Listing and managing

On the device:

```
kiki-remote pairings              # list all
kiki-remote pairings show <id>    # detail
kiki-remote pairings revoke <id>  # remove
kiki-remote pairings rename <id>
kiki-remote pairings narrow <id>  # adjust scope down
```

On the client: Settings → Devices.

## Unpairing

From either side:

- Device unpairs: mark revoked; terminate active sessions; reject future; audit
- Client unpairs: delete local credentials; notify device (best-effort); device cleans up

A lost client: user unpairs from another paired client (or directly on the device).

## Cert renewal

Pairing certs valid for 1 year by default. Renewal:

- Client requests before expiry
- Device renews if pairing still active and unrevoked
- New cert; same key pair (private key remains in secure storage)

A pairing whose cert expired beyond grace period requires re-pairing.

## Out-of-band confirmation

For high-stakes actions (modifying identity, granting elevated capabilities), the device may require on-device confirmation even from an authenticated remote:

```toml
[scope.confirmations]
identity_change = "on_device"
new_capability_grant = "on_device"
app_uninstall = "remote_or_device"
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| QR scanned by wrong device       | mismatched nonce; rejected     |
| QR expired                       | rendezvous URL errors          |
| Code attempts exceeded           | code invalidated               |
| Network drops mid-pairing        | client retries; if exceeds     |
|                                  | window, restart                |
| Scope rejected by device         | pairing fails                  |
| Recovery prompt declined         | pairing fails                  |
| Revoked-pairing reconnect        | rejected; client cleans up     |

## Performance contracts

- QR generation: <100ms
- Pairing completion: <2s typical
- Cert renewal: <1s

## Acceptance criteria

- [ ] All four pairing modes work end-to-end
- [ ] Single-use QR; expires within window
- [ ] Per-pairing scope enforced on every request
- [ ] Revocation effective immediately
- [ ] Cert renewal works without re-pairing
- [ ] Out-of-band confirmation enforced where configured
- [ ] Multi-user pairing isolation works
- [ ] Audit log records pairing events
- [ ] Client secure storage used per platform

## References

- `13-remotes/REMOTE-ARCHITECTURE.md`
- `13-remotes/REMOTE-PROTOCOL.md`
- `13-remotes/REMOTE-DISCOVERY.md`
- `09-backend/DEVICE-AUTH.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/AUDIT-LOG.md`
