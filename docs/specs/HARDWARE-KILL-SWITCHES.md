---
id: hardware-kill-switches
title: Hardware Kill Switches
type: SPEC
status: draft
version: 0.0.0
implements: [kill-switch-handling]
depends_on:
  - hal-contract
  - hardware-manifest
depended_on_by: []
last_updated: 2026-04-29
---
# Hardware Kill Switches

## Purpose

Specify how hardware kill switches (microphone, camera, radios) are honored at the HAL level, so that no software can override the hardware state and the user has a verifiable physical control.

## Behavior

### Why hardware kill switches

A software toggle that disables the microphone is good UX but can be bypassed by:

- Bugs.
- Malicious software (in theory).
- Misconfiguration.

A hardware kill switch physically disconnects the hardware. The software cannot override; the OS does not even see the device when the switch is engaged. This is the strongest privacy guarantee for users in adversarial contexts (journalists, dissidents, executives).

### Supported kill switches

When the hardware supports them (declared in `hardware-manifest.toml`):

- **Microphone kill switch.** Engaged → microphone is electrically disconnected. PipeWire reports the source as gone.
- **Camera kill switch.** Engaged → camera is electrically disconnected. v4l2 reports the device as gone.
- **Radios kill switch.** Engaged → Wi-Fi/Bluetooth/cellular radios are powered off. NetworkManager reports the radios as off.

Some hardware combines these (e.g., one switch for all radios; one switch for mic + camera). The manifest declares the granularity.

### How Kiki reports state

The state of each kill switch is reflected in the agentui status bar:

- Mic icon with strikethrough if the mic kill switch is engaged.
- Camera icon with strikethrough if camera kill switch is engaged.
- Radio icon with strikethrough if radios kill switch is engaged.

The status bar reads the state from `kiki-hald-power` (which polls or is notified by the kernel).

When a user asks the agent "is my microphone on?", the agent answers truthfully based on the kill switch state, not on what software thinks.

### How the OS responds

When a kill switch is engaged:

- `agentd` records the event in the audit log.
- The relevant subsystem (voice pipeline, camera apps, network apps) sees the device as unavailable and falls back to "feature unavailable" mode.
- The user is informed (status bar update; optional notification).

When a kill switch is disengaged:

- The device reappears in the OS.
- Services that were using it (voice pipeline) re-initialize.
- Audit log records the event.

### What software CANNOT do

The OS does not pretend the kill switch is engaged when the hardware says otherwise. Conversely, the OS cannot pretend the kill switch is disengaged.

There is no "soft override" path in Kiki. If the user wants to disable the mic without engaging the hardware switch, they can do so through the agent, but this is a software-only disable that does not provide the same guarantees and is reflected differently in the status bar.

### Hardware without kill switches

Most desktops do not have hardware kill switches. The manifest declares `present = false` for the relevant fields. In this case, software-only mute exists but does not pretend to be a hardware kill switch. The user understands the difference.

### Provisioning

Whether a device has hardware kill switches is set at manufacture time and reflected in the signed hardware manifest. Adding kill switches to an existing device is a hardware modification.

### Attestation

For users who need to verify the kill switches are real (not just labelled), the manifest is signed and attestable via TPM. A user can confirm that the device manufacturer attested kill switch presence.

## Interfaces

### kiki-bus events

```
hal.power.kill_switch_changed
   { switch: "microphone" | "camera" | "radios", state: "engaged" | "disengaged" }
```

### Status query

```
agentctl hardware kill-switches
```

Returns the current state.

## State

### In-memory

- Current kill switch state in `kiki-hald-power`.

### Persistent

- Audit log entries for state changes.

## Failure modes

| Failure | Response |
|---|---|
| Hardware does not have kill switches | manifest reports `present = false`; agentui shows software-only disable |
| Kernel does not report kill switch state | log; assume disengaged (most permissive); alert |
| Kill switch flips rapidly | debounce; record both events but rate-limit notifications |

## Performance contracts

- Kill switch event to status bar update: <100ms.

## Acceptance criteria

- [ ] Manifest accurately declares kill switch presence.
- [ ] Engaging mic kill switch causes PipeWire source to disappear.
- [ ] Engaging camera kill switch causes v4l2 device to disappear.
- [ ] Engaging radios kill switch causes NetworkManager radios off.
- [ ] Status bar reflects state.
- [ ] Audit log records changes.

## Open questions

None.

## References

- `02-platform/HAL-CONTRACT.md`
- `02-platform/HARDWARE-MANIFEST.md`
- `02-platform/AUDIO-STACK.md`
- `02-platform/NETWORK-STACK.md`
- `10-security/PRIVACY-MODEL.md`
## Graph links

[[HAL-CONTRACT]]  [[HARDWARE-MANIFEST]]
