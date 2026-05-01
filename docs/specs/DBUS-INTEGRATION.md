---
id: dbus-integration
title: DBus Integration
type: SPEC
status: draft
version: 0.0.0
implements: [dbus-integration]
depends_on:
  - agentd-daemon
  - transport-unix-socket
  - capability-gate
depended_on_by:
  - focusbus
  - ipc-patterns
last_updated: 2026-04-30
---
# DBus Integration

## Purpose

Specify the DBus surfaces Kiki exposes and consumes. DBus is
the lingua franca for Linux desktop integration: portals,
device events from systemd-logind, NetworkManager, UPower,
PulseAudio/pipewire, BlueZ, and Wayland compositors all
speak it. Kiki participates in this ecosystem so that
existing Linux components can interoperate without a
translation layer.

DBus is not the primary IPC for our daemons; Cap'n Proto and
NATS are. DBus is for the surface where Kiki meets the rest
of the Linux stack and for cross-app coordination via the
focusbus.

## Why DBus

- **Standard.** systemd, logind, UPower, NetworkManager,
  BlueZ, pipewire — all DBus-native. We get integration for
  free.
- **dbus-broker** is a fast, modern implementation; replaces
  the older dbus-daemon with no API change.
- **zbus** (pure-Rust) is the client and server library; no
  C dependency in our daemons.
- **AppArmor and SELinux mediation** is well-understood for
  DBus; sandbox profiles can constrain method calls
  precisely.

## Bus topology

```
System bus    /run/dbus/system_bus_socket
  - dbus-broker, root-owned, mediated by AppArmor
  - logind, UPower, NetworkManager, BlueZ, systemd
  - org.kiki.System1 (read-only system info)
  - org.kiki.Hardware1 (hardware kill switches)

Session bus   /run/user/<uid>/bus
  - per-user dbus-broker
  - org.kiki.Agent1 (per-user agent surface)
  - org.kiki.Mailbox1 (per-user mailbox)
  - org.kiki.Focus1 (focusbus)
  - org.kiki.Voice1 (voice control plane)
  - org.kiki.Apps1 (installed apps directory)
```

The system bus carries device-level signals; the session bus
carries user-facing surfaces. Apps connect to the session
bus.

## Services we publish

### org.kiki.System1 (system bus)

Read-only system information. Mostly for system tray apps and
remote diagnostics:

```
Methods:
  GetUptime() -> u
  GetVersion() -> a{ss}
  GetHealth() -> a{sv}      summary of daemon health

Signals:
  HealthDegraded(s reason)
  UpdateAvailable(s channel, s new_version)
  UpdateApplied(s channel, s version)
```

### org.kiki.Hardware1 (system bus)

Hardware kill switches and capability state. Read-only;
toggling is a privileged operation that goes through the
hardware-abstraction layer, not over DBus.

```
Properties:
  CameraKilled b
  MicKilled b
  RadiosKilled b

Signals:
  KillStateChanged(s component, b state)
```

### org.kiki.Agent1 (session bus)

Lightweight surface to the agent for shell scripts and
desktop integration. Heavy use should go through Cap'n
Proto; DBus is for "talk to my agent from anywhere":

```
Methods:
  Send(s message) -> s response
  StartSession() -> o session_path
  Cancel(o session_path) -> ()

Signals:
  StreamingChunk(s session_id, s chunk)
  SessionEnded(s session_id)
```

The Send method is rate-limited per caller; long sessions
should use the Cap'n Proto path.

### org.kiki.Mailbox1 (session bus)

Mailbox surface for the launcher and per-app integrations:

```
Methods:
  List() -> ao paths
  Get(o path) -> a{sv}
  Acknowledge(o path) -> ()
  Dismiss(o path) -> ()

Signals:
  MessageNew(o path, a{sv} preview)
  MessageRemoved(o path)
```

### org.kiki.Focus1 (session bus)

The focusbus (see `FOCUSBUS.md`). Apps publish their current
focus context here; the agent and other apps subscribe.

### org.kiki.Voice1 (session bus)

Control plane only — audio flows over pipewire or iceoryx2,
not DBus.

```
Methods:
  StartListening() -> o session_path
  StopListening(o session_path) -> ()
  Mute() -> ()
  Unmute() -> ()
  GetState() -> s

Signals:
  WakeWordDetected()
  TranscriptPartial(s text)
  TranscriptFinal(s text)
  TtsStarted(s session_id)
  TtsEnded(s session_id)
```

### org.kiki.Apps1 (session bus)

Directory of installed apps and their declared DBus services:

```
Methods:
  List() -> a(sss) (id, name, dbus_well_known)
  Get(s id) -> a{sv}

Signals:
  AppInstalled(s id)
  AppRemoved(s id)
  AppUpdated(s id, s version)
```

## Services we consume

- `org.freedesktop.login1` — sessions, idle, suspend, lid
  events
- `org.freedesktop.UPower` — battery, AC state
- `org.freedesktop.NetworkManager` — network state, captive
  portal
- `org.bluez` — Bluetooth devices, pairing
- `org.freedesktop.systemd1` — service status
- `org.pipewire.PipeWire` — audio routing (where applicable;
  much of this is via libpipewire directly)
- `org.freedesktop.portal.*` — desktop portals (file
  picker, screenshot) where apps need them

The hardware-abstraction layer is the mediator: it consumes
these signals and republishes them as Kiki events on NATS
or as Cap'n Proto streams. App tools never speak these
buses directly; they go through HAL.

## Authentication

dbus-broker enforces policy via AppArmor labels and via XML
policy files in `/usr/share/dbus-1/system.d/`,
`/usr/share/dbus-1/session.d/`. Policies are part of the
bootc base image:

```xml
<policy user="kiki">
  <allow own="org.kiki.Agent1"/>
  <allow send_destination="org.kiki.Agent1"/>
</policy>

<policy context="default">
  <deny send_destination="org.kiki.Hardware1"
        send_member="SetKillState"/>
</policy>
```

Apps' manifests declare their DBus claims; the install-time
generator emits the policy file. Apps cannot grant themselves
new claims at runtime.

## zbus usage

Daemons use zbus' async API; `#[interface]` attributes
generate the introspection XML. Object paths follow:

```
/org/kiki/Agent1/<session-id>
/org/kiki/Mailbox1/messages/<id>
/org/kiki/Focus1
/org/kiki/Voice1
```

Each object's properties, methods, and signals are
documented in the relevant daemon spec.

## Mapping to internal events

Many DBus signals are mirrors of NATS events:

| NATS subject              | DBus signal                 |
|---------------------------|------------------------------|
| `mailbox.message.new`      | `org.kiki.Mailbox1.MessageNew` |
| `agent.cycle.start`        | `org.kiki.Agent1.SessionStarted` |
| `system.update.available`  | `org.kiki.System1.UpdateAvailable` |
| `focus.changed`            | `org.kiki.Focus1.Changed` |

Internally, the bridge is one-way: NATS event arrives →
zbus emits the DBus signal. We don't re-emit DBus signals
back onto NATS to avoid cycles.

For methods that originate from a DBus client (e.g., a
shell script calling `Send`), the daemon translates the DBus
call into a Cap'n Proto request internally, runs the gate,
and returns the result.

## Object paths and well-known names

Well-known names are reserved at startup:

```
org.kiki.System1            owned by agentd (via system-helper)
org.kiki.Hardware1          owned by HAL
org.kiki.Agent1             owned by per-user agentd-user.service
org.kiki.Mailbox1           owned by agentd-user.service
org.kiki.Focus1             owned by agentd-user.service
org.kiki.Voice1             owned by agentd-user.service
org.kiki.Apps1              owned by toolregistry-user.service
```

If a daemon crashes, the well-known name is released; on
restart it is reclaimed. Clients subscribe to NameOwnerChanged
to know when to reconnect.

## Capability mapping

DBus calls map to capabilities. The capability gate is
consulted before the call body runs, exactly as for Cap'n
Proto calls. The DBus dispatcher records:

- The peer uid (DBus connection metadata)
- The peer's AppArmor label (via dbus-broker's policy hooks)
- The method called

The gate's `Decision` translates back to either:

- Allow → method runs
- Deny → DBus error `org.kiki.Error.PolicyDenied` with the
  reason string
- Prompt → method blocks until the mailbox returns; or the
  client may pass a `kiki-defer-id` header to be notified
  asynchronously

## Async operations

DBus has limited support for streaming; long operations
return a path to a transient object that exposes
`Progress` properties and a `Completed` signal. Clients
that need real streaming use Cap'n Proto.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| dbus-broker not running          | systemd restarts; daemons      |
|                                  | reconnect                      |
| Well-known name stolen           | should not happen; broker      |
|                                  | enforces; alert if it does     |
| Policy file rejected at parse    | bootc rolls back               |
| Method called by unauthorized    | DBus error PolicyDenied        |
| peer                             |                                |
| App tries to claim a name        | broker rejects                 |
| outside its prefix               |                                |

## Performance contracts

- Method call (small payload) p99: <2ms
- Signal emission to N subscribers: <1ms for N<100
- Connection setup: <10ms

## Acceptance criteria

- [ ] All seven `org.kiki.*` services exposed and
      introspectable
- [ ] Policy files generated correctly at install for apps
- [ ] DBus signals mirror NATS events for the listed pairs
- [ ] Capability gate runs before any DBus method body
- [ ] AppArmor labels enforced via dbus-broker

## Open questions

None.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `01-architecture/HARDWARE-ABSTRACTION.md`
- `05-protocol/FOCUSBUS.md`
- `05-protocol/NATS-BUS.md`
- `05-protocol/TRANSPORT-UNIX-SOCKET.md`
- `08-voice/VOICE-CHANNELS.md`
## Graph links

[[AGENTD-DAEMON]]  [[TRANSPORT-UNIX-SOCKET]]  [[CAPABILITY-GATE]]
