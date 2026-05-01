---
id: remote-protocol
title: Remote Protocol
type: SPEC
status: draft
version: 0.0.0
implements: [remote-protocol]
depends_on:
  - remote-architecture
  - device-pairing
  - remote-discovery
  - capnp-rpc
  - cryptography
depended_on_by:
  - fleet-management
  - remote-client-platforms
  - remote-config-sync
last_updated: 2026-04-30
---
# Remote Protocol

## Purpose

Specify the wire protocol between a paired remote client and a Kiki device: Cap'n Proto over mTLS, the bootstrap interface, the four surfaces (agent, config, fleet, diagnostics), and how the protocol degrades on WAN.

## Transport

```
LAN-direct          TLS 1.3 (rustls + aws-lc-rs); mTLS via pairing certs;
                    TCP on the device's RPC port (advertised via mDNS)

WAN-rendezvous      Same Cap'n Proto over mTLS; the underlying TCP is
                    inside an ICE-negotiated path (sometimes through
                    a relay)

Voice               WebRTC for audio; control plane on Cap'n Proto
```

## Bootstrap

After connection setup, the device exposes a `RemoteBootstrap` capability scoped to the pairing:

```capnp
interface RemoteBootstrap {
  agent       @0 () -> (a :AgentSurface);
  config      @1 () -> (c :ConfigSurface);
  fleet       @2 () -> (f :FleetSurface);
  diagnostics @3 () -> (d :DiagnosticsSurface);
}
```

The pairing's scope determines which sub-capabilities are reachable.

## AgentSurface

```capnp
interface AgentSurface {
  send       @0 (msg :UserMessage) -> stream (chunk :AssistantChunk);
  cancel     @1 () -> ();
  context    @2 () -> (ctx :ContextSnapshot);
  voice      @3 () -> (v :VoiceSession);
  surfaces   @4 () -> stream (delta :SurfaceDelta);
  proactive  @5 () -> stream (msg :ProactiveMessage);
}

interface VoiceSession {
  webrtcOffer @0 (offer :Sdp) -> (answer :Sdp);
  cancel @1 () -> ();
}
```

`send` mirrors the on-device agent; `voice` negotiates WebRTC; `surfaces` lets the remote observe live agent surfaces (for "show me what's on the device's screen" use cases — note: the *agent's surfaces* not the *display contents*).

## ConfigSurface

```capnp
interface ConfigSurface {
  get @0 (path :Text) -> (value :Json);
  set @1 (path :Text, value :Json) -> ();
  list @2 () -> stream (entry :SettingEntry);
  apps @3 () -> (a :AppsAdmin);
  grants @4 () -> (g :GrantsAdmin);
}

interface AppsAdmin {
  list @0 () -> (apps :List(AppInfo));
  install @1 (id :Text, version :Text) -> stream (progress :InstallProgress);
  uninstall @2 (id :Text) -> ();
}

interface GrantsAdmin {
  list @0 () -> (grants :List(Grant));
  revoke @1 (grant :GrantId) -> ();
}
```

## FleetSurface

```capnp
interface FleetSurface {
  devices @0 () -> stream (d :DeviceSummary);
  health @1 () -> (h :HealthReport);
  delegate @2 (action :DeviceAction, target :DeviceId) -> ();
}
```

For coordinating a multi-device household. See `FLEET-MANAGEMENT.md`.

## DiagnosticsSurface

```capnp
interface DiagnosticsSurface {
  audit @0 () -> stream (entry :AuditEntry);
  health @1 () -> (h :HealthReport);
  memoryInspector @2 () -> (m :MemoryInspector);
  logs @3 () -> stream (line :LogLine);
}
```

The pairing's scope limits which diagnostics are accessible.

## Capability gating

Every method call goes through the device's capability gate. The pairing's scope is the *ceiling*; per-call grants narrow further. Denials return structured `ErrorPayload` with `policy.denied`.

## Streaming

`stream`-typed methods carry continuous data with backpressure (Cap'n Proto streaming RPC). The remote drains; the device pauses if the remote falls behind.

## Idempotency

Methods marked `# idempotent` may be safely retried by the client on transient errors. Non-idempotent methods (e.g., `apps.install`) are not auto-retried.

## Versioning

The Cap'n Proto schema carries a version. Clients negotiate at bootstrap; older clients see a subset of methods supported. Major bumps require coordinated app updates.

## Error model

Same as in-device IPC: `ErrorPayload` (see `ERROR-MODEL.md`).

## Out-of-band confirmation

For high-stakes calls (identity changes, ElevatedConsent grants), the device may require on-device user confirmation. The method returns `Defer` immediately; the client polls or receives a notification when the user resolves on the device.

## Voice flow

```
remote → AgentSurface.voice() → VoiceSession
                                     │
remote → VoiceSession.webrtcOffer(...) → device WebRTC stack
                                                    │
                                            ICE/DTLS/SRTP
                                                    │
                                            audio bytes flow
                                                    │
                                       device's voice pipeline
                                                    │
                                          agent loop
                                                    │
                                                TTS audio back
```

The remote's audio goes into the device's voice pipeline as if local; the device responds via TTS over WebRTC.

## Multi-session

A pairing's scope caps concurrent sessions. Going over returns `budget.rate_limited`.

## Session keepalive

TCP keepalives + an application-level ping every 30s. Stale sessions terminate after 60s of no traffic.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| mTLS auth fails                  | refuse connection              |
| Schema mismatch                  | bootstrap fails with           |
|                                  | ProtocolMismatch                |
| Capability denied                | structured error               |
| Network drops mid-stream         | stream ends; client retries     |
| WebRTC negotiation fails         | error; fall back to text       |

## Performance contracts

- Bootstrap (LAN): <100ms
- Send first chunk (LAN): <50ms
- Send first chunk (WAN-rendezvous): <300ms
- Voice round-trip (LAN): <80ms
- Voice round-trip (WAN-rendezvous): <250ms

## Acceptance criteria

- [ ] All four surfaces functional with capability gating
- [ ] Streaming with backpressure works
- [ ] WebRTC negotiation succeeds across LAN and WAN
- [ ] Pairing scope ceilings honored
- [ ] Out-of-band confirmation flow works for high-stakes
- [ ] Schema versioning negotiated at bootstrap

## References

- `13-remotes/REMOTE-ARCHITECTURE.md`
- `13-remotes/DEVICE-PAIRING.md`
- `13-remotes/REMOTE-DISCOVERY.md`
- `13-remotes/REMOTE-CONFIG-SYNC.md`
- `13-remotes/REMOTE-CLIENT-PLATFORMS.md`
- `13-remotes/FLEET-MANAGEMENT.md`
- `05-protocol/CAPNP-RPC.md`
- `05-protocol/ERROR-MODEL.md`
- `08-voice/VOICE-CHANNELS.md`
- `10-security/CRYPTOGRAPHY.md`
