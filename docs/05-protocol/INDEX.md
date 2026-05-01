---
id: protocol-index
title: Protocol — Index
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# Protocol

IPC and wire formats: Cap'n Proto for tool dispatch, NATS for service bus, iceoryx2 for bulk data, DBus for desktop integration, focusbus for cross-app state.

## Tool dispatch and cross-app

- `../../specs/CAPNP-RPC.md` — Cap'n Proto RPC over Unix sockets.
- `../../specs/CAPNP-SCHEMAS.md` — schema management and evolution.
- `../../specs/TRANSPORT-UNIX-SOCKET.md` — authentication via SO_PEERCRED.

## Service bus

- `../../specs/NATS-BUS.md` — embedded NATS, JWT scoping, subject taxonomy.

## Desktop integration

- `../../specs/DBUS-INTEGRATION.md` — zbus and `org.kiki.*` interfaces.

## Bulk data plane

- `../../specs/ICEORYX-DATAPLANE.md` — zero-copy shared memory for audio/video.

## Patterns and shared concerns

- `IPC-PATTERNS.md` — request/response, streaming, events.
- `../../specs/ERROR-MODEL.md` — error codes and retry semantics.
- `../../specs/FOCUSBUS.md` — `org.kiki.Focus1` cross-app selection.
