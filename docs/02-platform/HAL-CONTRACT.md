---
id: hal-contract
title: HAL Contract
type: SPEC
status: draft
version: 0.0.0
implements: [hal-daemons]
depends_on:
  - hardware-manifest
  - kernel-config
  - process-model
depended_on_by:
  - audio-stack
  - hardware-kill-switches
last_updated: 2026-04-30
---
# HAL Contract

## Purpose

Specify the contract between hardware and the rest of Kiki OS. HAL daemons (`kiki-hald-*`) abstract specific hardware and expose a consistent interface to system services and apps.

## Inputs

- Kernel device events (uevent, sysfs).
- Hardware manifest (declaring which devices are present).
- HAL configuration in the OS image.

## Outputs

- DBus or Cap'n Proto interfaces exposing hardware operations.
- Hot-plug events on the kiki-bus.
- Hardware state telemetry to agentd.

## Behavior

### Why HAL daemons

Apps and the agent should not poke `/dev/*` directly. Doing so:

- Bypasses the capability gate.
- Skips hardware validity checks.
- Couples app code to specific hardware.

A HAL daemon provides:

- A stable interface independent of specific hardware.
- Capability gating by virtue of being mediated by a privileged daemon.
- Hardware state coherence (only one process talks to the device).

### HAL daemons in Kiki

```
kiki-hald-audio       microphones, speakers, audio routing
kiki-hald-camera      cameras (when present)
kiki-hald-input       keyboards, pointers, touch (mostly delegated to libinput via cage)
kiki-hald-power       battery, power state, kill switches
kiki-hald-network     wired/wireless interfaces (mostly delegated to NetworkManager)
kiki-hald-bluetooth   Bluetooth (when present and enabled)
kiki-hald-sensor      IMU, ambient light, proximity (when present)
```

Not every device class has a Kiki-specific daemon. Where upstream provides a mature daemon (NetworkManager, PipeWire, BlueZ), we use it directly and expose its DBus interface to the agent. Kiki-specific HAL daemons exist where:

- The upstream interface is ill-suited for the agent's needs.
- We want capability mediation that upstream doesn't provide.
- Specific Kiki-policy decisions need to live in the daemon.

In v0, only `kiki-hald-power` is Kiki-specific (for kill switch state and power policy integration with workspace hibernation). Audio, camera, input, network, Bluetooth, sensor delegate to upstream daemons.

### Interface convention

Each HAL daemon exposes:

- A DBus service at `org.kiki.hal.<domain>` (e.g., `org.kiki.hal.power`).
- A Cap'n Proto interface for high-throughput data plane (e.g., audio frames over iceoryx2 + control plane on DBus).
- Events on kiki-bus subjects `hal.<domain>.*` (e.g., `hal.power.battery_low`).

Standard methods:

```
status() -> HardwareStatus
configure(config: Configuration) -> Result
subscribe_events(filter: EventFilter) -> Stream<Event>
```

Plus domain-specific methods.

### Capability gating

Every HAL operation is capability-gated. The capability gate inside `policyd` checks:

- Whether the calling app has the relevant capability (`device.audio.input`, `device.camera.use`, etc.).
- Whether the operation is realizable per the hardware manifest.

The HAL daemon trusts agentd's authentication of the caller; it does not implement its own.

### Audio

Audio is handled by:

- **PipeWire** as the primary system service for audio routing.
- **wireplumber** as session manager.
- `kiki-voiced` as the voice pipeline consumer.
- Apps consuming audio via the PipeWire DBus API mediated through capability gates.

PipeWire's `module-echo-cancel` provides AEC. PipeWire is configured at boot via `kiki-base.target`.

### Camera

Cameras are accessed via:

- libcamera (the upstream camera framework).
- `pipewire-libcamera` for video streams.
- HAL exposes camera control (privacy LED state, hardware shutter state).

Privacy LED is hardware-coupled where supported; the OS reflects the LED state but cannot override the hardware.

### Input

Input devices (touch, keyboard, pointer) are consumed by:

- libinput, used directly by cage compositor.
- agentui receives input events via Wayland.

There is no general "input HAL" exposed to apps; apps receive input from agentui through the Cap'n Proto block protocol.

### Power

Power state is exposed by `kiki-hald-power`:

- Battery level (where applicable).
- Charging state.
- Power source (AC/battery).
- Hardware kill switch states (mic, camera, radios).
- System power events (lid close, idle timeout).

`agentd` consumes power events to decide on workspace hibernation, dreaming triggers, and inference router policy (e.g., disable cloud below battery threshold).

### Network

Network is handled by NetworkManager. The HAL boundary is NetworkManager's DBus interface. agentd subscribes to network state changes.

### Bluetooth

Bluetooth via BlueZ where present. Off by default; enabled per user policy.

### Sensors

Where present, sensor data flows through `kiki-hald-sensor` to apps with appropriate capability. v0 desktop typically has none; future hardware classes may have IMU, ambient light, etc.

### Hot-plug

Hot-plug events flow:

```
kernel uevent → udev → HAL daemon → kiki-bus event → agentd consumers (compositor, agent)
```

The agent and compositor adapt to hot-plug without restart (e.g., a new display appears; cage reconfigures).

## Interfaces

### DBus services

```
org.kiki.hal.power
org.kiki.hal.audio       (delegated to PipeWire's interface)
org.kiki.hal.camera
org.kiki.hal.bluetooth   (delegated to BlueZ)
org.kiki.hal.network     (delegated to NetworkManager)
org.kiki.hal.sensor
```

### kiki-bus events

```
hal.power.battery_low
hal.power.charging_changed
hal.power.kill_switch_changed
hal.audio.device_added
hal.audio.device_removed
hal.camera.privacy_led_changed
hal.network.connection_changed
```

### CLI

```
agentctl hardware show       # full hardware status
agentctl hardware power      # power state
agentctl hardware audio      # audio devices
```

## State

### Persistent

- HAL daemon configuration in /etc/kiki/hal/.

### In-memory

- Current hardware state cached by each daemon.

## Failure modes

| Failure | Response |
|---|---|
| HAL daemon crash | systemd restarts; subscribers see disconnect/reconnect |
| Hardware unplug | event emitted; depending state cleaned up |
| Hardware unresponsive | timeout; log; alert |
| Hot-plug for unknown device | log; ignore; safe defaults |

## Performance contracts

- Hot-plug event to subscriber: <100ms.
- HAL DBus call: <5ms for status queries; <20ms for configuration changes.

## Acceptance criteria

- [ ] HAL daemons follow the convention above.
- [ ] Capability gating is enforced for every operation.
- [ ] Hot-plug events propagate to subscribers.
- [ ] Kill switch state is reported faithfully.
- [ ] PipeWire and NetworkManager integrations work.

## Open questions

- Whether to have a Kiki-specific kiki-hald-camera vs delegating fully to PipeWire's camera node model.

## References

- `02-platform/HARDWARE-MANIFEST.md`
- `02-platform/AUDIO-STACK.md`
- `02-platform/HARDWARE-KILL-SWITCHES.md`
- `02-platform/NETWORK-STACK.md`
- `01-architecture/PROCESS-MODEL.md`
