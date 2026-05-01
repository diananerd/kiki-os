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

- `CAPNP-RPC.md` — Cap'n Proto RPC over Unix sockets.
- `CAPNP-SCHEMAS.md` — schema management and evolution.
- `TRANSPORT-UNIX-SOCKET.md` — authentication via SO_PEERCRED.

## Service bus

- `NATS-BUS.md` — embedded NATS, JWT scoping, subject taxonomy.

## Desktop integration

- `DBUS-INTEGRATION.md` — zbus and `org.kiki.*` interfaces.

## Bulk data plane

- `ICEORYX-DATAPLANE.md` — zero-copy shared memory for audio/video.

## Patterns and shared concerns

- `IPC-PATTERNS.md` — request/response, streaming, events.
- `ERROR-MODEL.md` — error codes and retry semantics.
- `FOCUSBUS.md` — `org.kiki.Focus1` cross-app selection.
