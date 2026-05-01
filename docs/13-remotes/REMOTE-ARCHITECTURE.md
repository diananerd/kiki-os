---
id: remote-architecture
title: Remote Client Architecture
type: DESIGN
status: draft
version: 0.0.0
implements: [remote-client-architecture]
depends_on:
  - principles
  - trust-boundaries
  - agentd-daemon
  - backend-contract
  - voice-channels
depended_on_by:
  - device-pairing
  - fleet-management
  - remote-client-platforms
  - remote-config-sync
  - remote-discovery
  - remote-protocol
last_updated: 2026-04-30
---
# Remote Client Architecture

## Problem

Users own multiple Kiki devices and clients: a primary in the home, a foldable in their pocket, a developer-kit on the desk. They need to talk to the agent on any device from any device, configure settings, manage apps and grants, inspect audit logs, and coordinate the fleet — without breaking local-first or losing the device's authority.

A separate "remote control" app per device is fragmented; routing everything through the cloud violates local-first. We need a coherent remote-client model.

## Constraints

- **Device sovereignty.** The device is authoritative; the remote is a peer, not a controller. The device can refuse any remote request.
- **Local-first.** LAN-direct must work without backend involvement.
- **Capability-gated.** The remote inherits capabilities via pairing; per-action gates still apply.
- **No screen mirroring.** The agent is the interface; the remote talks to the agent.
- **Voice is real-time.** Voice from a remote uses WebRTC.
- **Multiple platforms.** iOS, Android, macOS, Windows, Linux, Web — same protocol, platform-specific shells.

## Decision

A remote client is a **paired peer** of one or more Kiki devices. After pairing, the client speaks `kiki-wire` (Cap'n Proto over mTLS) directly to the device on LAN; via a backend-mediated rendezvous on WAN.

The client surface covers four areas:

```
1. Agent channel       text + voice conversation
2. Configuration       settings, grants, policies
3. Fleet operations    multi-device control
4. Diagnostics         audit log, health, memory inspector
```

Each is implemented as a documented Cap'n Proto schema that the device serves to authenticated remote peers.

The remote client is itself an "app" from the device's POV, with its own pairing-derived id. Capability gates apply normally; the remote does not have ambient elevated privilege.

## Rationale

### Why peer, not controller

A controller-style design ("the phone runs the agent; the device executes") would centralize the agent on a more-stolen, less-secure device, break offline operation, and force the user to reason about which device "really" runs things. Peer matches the agent loop's existing structure.

### Why kiki-wire (Cap'n Proto)

We already have a mature, schema-driven, capability-gated wire protocol. Reusing it gives one tooling set, one trust model, one audit story.

### Why separate voice path

WebRTC is the right transport for low-latency bidirectional audio; reliable streams are the wrong tool. The remote protocol carries control; audio flows on WebRTC.

### Why no screen mirroring

Mirroring leaks pixels across users (the remote and the local user might be different people). It also makes the remote's UX dependent on the device's display geometry, defeating distinct surface formats.

### Why capability-gated pairing

A "household member" pairing has broad capabilities; a "service technician" pairing might be limited to diagnostics for a session. The pairing is the unit at which capabilities are granted; per-action gates still apply.

## Consequences

### What the remote can do (default full pairing)

- Send agent commands; receive streamed responses
- Initiate voice sessions (WebRTC)
- Read/modify settings (per gate)
- List/install/uninstall apps (per gate)
- View and revoke capability grants
- Inspect audit logs
- Browse / edit memory (per gate)
- Receive proactive notifications

### What the remote cannot do

- Bypass any capability gate
- Modify identity files outside the consent flow
- Read another user's data without explicit grant
- Override hardware kill switches
- Rewrite the audit log

### Trust boundary

The remote process is *less trusted* than processes on the device:

- Runs on hardware the device cannot verify
- May be compromised independently
- The user controls it, but so does any malware on it

Mitigations: gate everything; sensitive ops may require user-on-device confirmation; pairing scope can be narrow; audit log records every remote-originated action.

### Performance characteristics

| Connection         | Typical latency  | Throughput      |
|--------------------|------------------|-----------------|
| LAN-direct         | <10ms RTT        | LAN-bandwidth   |
| WAN-rendezvous     | <100ms RTT       | rate-limited    |
| WAN-relayed (rare) | <300ms RTT       | small payloads  |

LAN-direct is preferred when both peers are on the same network. WAN paths involve backend mediation.

### Multi-device complexity bounded

- Pairings are pairwise (client ↔ device)
- Each side knows about its peers
- Fleet operations are explicitly issued; nothing cascades implicitly

### Backend role

- WAN rendezvous (NAT traversal hints, signed peer introductions)
- Optional: relay when direct connectivity unavailable
- Discovery directory (list user's paired devices)
- Push notifications

The backend never sees the content of remote-device traffic in LAN-direct. In WAN-relayed, it sees TLS ciphertext but cannot decrypt (E2E encrypted under the pairing's key material).

## References

- `00-foundations/PRINCIPLES.md`
- `01-architecture/TRUST-BOUNDARIES.md`
- `03-runtime/AGENTD-DAEMON.md`
- `08-voice/VOICE-CHANNELS.md`
- `09-backend/BACKEND-CONTRACT.md`
- `13-remotes/DEVICE-PAIRING.md`
- `13-remotes/REMOTE-DISCOVERY.md`
- `13-remotes/REMOTE-PROTOCOL.md`
- `13-remotes/FLEET-MANAGEMENT.md`
- `13-remotes/REMOTE-CONFIG-SYNC.md`
- `13-remotes/REMOTE-CLIENT-PLATFORMS.md`
## Graph links

[[PRINCIPLES]]  [[TRUST-BOUNDARIES]]  [[AGENTD-DAEMON]]  [[BACKEND-CONTRACT]]  [[VOICE-CHANNELS]]
