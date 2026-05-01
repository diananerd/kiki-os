---
id: 0021-nats-service-bus
title: Embedded NATS as Service Bus
type: ADR
status: draft
version: 0.0.0
depends_on: [0020-capnp-rpc-tool-dispatch]
last_updated: 2026-04-29
---
# ADR-0021: Embedded NATS as Service Bus

## Status

`accepted`

## Context

Kiki needs a publish/subscribe substrate for events: hooks fanning out, mailbox notifications, audit tail, focus changes, system health. Cap'n Proto RPC is the request/response substrate, but it is a poor fit for ambient broadcast where we have many ad-hoc subscribers. Candidates: ZeroMQ, Redis pub/sub, Kafka, MQTT, NATS.

## Decision

Run an **embedded NATS server** (`nats-server`) at `/run/kiki/nats/nats.sock`. Use **JWT-scoped accounts** for system, per-user, and per-app isolation. Use NATS Core for best-effort fanout and **JetStream** sparingly for at-least-once delivery (mailbox durables, audit live tail). Apps speak NATS via async-nats.

## Consequences

### Positive

- Subject hierarchies map naturally to our event taxonomy.
- JWT scoping isolates apps and users without changing wire format.
- Cheap subscriptions; hooks subscribe directly without a custom dispatch table.
- JetStream provides bounded durability where needed.
- nats-server is widely deployed and battle-tested.

### Negative

- Two pub/sub layers in the brain (NATS for events, Cap'n Proto stream for typed RPC); developers must choose correctly.
- JetStream has a non-trivial disk budget; we cap at 256MB across system streams.
- Slow consumer policy needs tuning per-stream (drop vs block).

## Alternatives considered

- **ZeroMQ**: no built-in auth scoping; we'd build it ourselves.
- **Redis pub/sub**: heavier than needed; Redis is a database.
- **Kafka**: dramatically oversized for in-machine eventing.
- **MQTT (mosquitto)**: weaker subject semantics; weaker auth model for our case.

## References

- `05-protocol/NATS-BUS.md`
- `03-runtime/EVENT-BUS.md`
- `03-runtime/HOOKS.md`
