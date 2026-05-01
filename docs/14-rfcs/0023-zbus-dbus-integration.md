---
id: 0023-zbus-dbus-integration
title: zbus for DBus Integration
type: ADR
status: draft
version: 0.0.0
depends_on: [0014-rust-only-shell-stack]
last_updated: 2026-04-29
---
# ADR-0023: zbus for DBus Integration

## Status

`accepted`

## Context

Linux desktop integration runs on DBus: logind sessions, UPower battery, NetworkManager, BlueZ, systemd, pipewire, portals. Kiki needs to consume these to react to system events and to expose a small set of `org.kiki.*` services that desktop apps and remote diagnostics can use. We also need DBus mediation that respects AppArmor labels. Candidates: dbus-rs (libdbus FFI), zbus (pure Rust), busctl + custom.

## Decision

Use **zbus** (pure Rust) as the DBus client and server library for all daemon integration. Use **dbus-broker** (the modern C broker) on the system and per-user buses, with policy files generated from app manifests at install time. Expose `org.kiki.System1`, `org.kiki.Hardware1`, `org.kiki.Agent1`, `org.kiki.Mailbox1`, `org.kiki.Focus1`, `org.kiki.Voice1`, `org.kiki.Apps1`.

## Consequences

### Positive

- No FFI to libdbus from any Kiki daemon.
- zbus generates introspection XML from `#[interface]` attributes; types match Cap'n Proto-side definitions cleanly.
- dbus-broker is the modern, fast implementation; AppArmor mediation is well-tested.
- Apps automatically get DBus integration via their manifest; nothing custom per app.

### Negative

- DBus is not the right tool for high-frequency or large payloads; we keep it to small UI surfaces.
- Two surfaces (Cap'n Proto + DBus) for some daemons; the bridge code mirrors NATS events to DBus signals one-way to avoid cycles.

## Alternatives considered

- **dbus-rs (FFI to libdbus)**: works, but adds a C dependency and a build-time complication.
- **No DBus, expose only Cap'n Proto**: cuts us off from the Linux desktop ecosystem (logind, portals, NetworkManager).
- **Custom IPC with adapters per integration**: massive amount of work for marginal gain.

## References

- `05-protocol/DBUS-INTEGRATION.md`
- `05-protocol/FOCUSBUS.md`
- `01-architecture/HARDWARE-ABSTRACTION.md`
## Graph links

[[0014-rust-only-shell-stack]]
