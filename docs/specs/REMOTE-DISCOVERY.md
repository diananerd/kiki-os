---
id: remote-discovery
title: Remote Discovery
type: SPEC
status: draft
version: 0.0.0
implements: [remote-discovery]
depends_on:
  - remote-architecture
  - device-pairing
  - backend-contract
depended_on_by:
  - remote-protocol
last_updated: 2026-04-30
---
# Remote Discovery

## Purpose

Specify how a paired remote client locates its paired Kiki device(s) on the network: mDNS for LAN, backend rendezvous for WAN, and a directory of paired devices the remote can use to choose among them.

## LAN discovery

The device advertises itself via mDNS:

```
_kiki._tcp                          presence
_kiki-pairing._tcp.<device-id>      pairing endpoint
_kiki-rpc._tcp.<device-id>          RPC endpoint after pairing
```

A remote client browses for `_kiki._tcp`; finds devices it has paired with by their device id; connects.

mDNS is multicast on the LAN; works on all common home networks. Some VLANs or guest networks block multicast — the remote falls back to a manual IP entry or backend rendezvous.

## TXT records

Each advertisement includes:

```
device-id = <id>
device-name = <human name>
api-version = 1
fingerprint = <pubkey-fingerprint>
```

The remote verifies the fingerprint matches what it has stored from pairing. A man-in-the-middle on the LAN cannot impersonate the device without the matching key.

## Direct connection

After mDNS resolution, the remote opens a TLS connection to the advertised endpoint. mTLS uses the pairing certs. No backend involvement.

## WAN rendezvous

When the remote and device are on different networks:

- Device registers presence with the backend's rendezvous service
- Remote queries the backend: "where is device X?"
- Backend returns NAT-traversal hints (STUN/TURN candidates) and a signed peer introduction
- Remote and device complete an ICE / hole-punching handshake
- Cap'n Proto over the established mTLS tunnel

The backend never sees decrypted traffic.

## Relayed fallback

If direct connectivity fails (symmetric NATs, firewalls), the backend can relay encrypted bytes via a TURN-class relay. Higher latency, lower throughput; opt-in per pairing.

## Discovery directory

The backend hosts a directory of a user's paired devices:

```
GET /v1/users/<uid>/devices
[
  { "id": "...", "name": "Home", "last_seen": "...", "online": true },
  { "id": "...", "name": "Office", "last_seen": "...", "online": false }
]
```

Used by the remote to pick a device when multiple are available; or by the user to manage their fleet.

## Privacy

- Backend sees: device exists, came online at time T, IP region (for STUN)
- Backend does not see: traffic content, user data
- Self-hosted backend: the user controls all of the above

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| mDNS blocked on LAN              | manual IP / WAN rendezvous     |
| Fingerprint mismatch             | refuse; alert user             |
| Backend rendezvous unavailable   | LAN-only; degrades for         |
|                                  | distant cases                   |
| Direct connection blocked        | relay fallback; opt-in         |
| Stale directory                  | refresh; ignore offline        |

## Performance

- mDNS resolve: <200ms typical
- LAN connect: <50ms
- WAN rendezvous: <500ms total (including STUN)
- Relay: <300ms RTT typical

## Acceptance criteria

- [ ] mDNS discovery works on common home networks
- [ ] Fingerprint verified pre-connect
- [ ] WAN rendezvous succeeds on standard NATs
- [ ] Relay fallback when direct fails
- [ ] Discovery directory shows correct online state
- [ ] No backend visibility into traffic content

## References

- `13-remotes/REMOTE-ARCHITECTURE.md`
- `13-remotes/DEVICE-PAIRING.md`
- `13-remotes/REMOTE-PROTOCOL.md`
- `09-backend/BACKEND-CONTRACT.md`
- `02-platform/NETWORK-STACK.md`
## Graph links

[[REMOTE-ARCHITECTURE]]  [[DEVICE-PAIRING]]  [[BACKEND-CONTRACT]]
