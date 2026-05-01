---
id: nats-bus
title: NATS Service Bus
type: SPEC
status: draft
version: 0.0.0
implements: [nats-bus]
depends_on:
  - agentd-daemon
  - transport-unix-socket
  - capability-gate
depended_on_by:
  - focusbus
  - ipc-patterns
last_updated: 2026-04-30
---
# NATS Service Bus

## Purpose

Specify the embedded NATS server used for loosely coupled
event distribution between agentd, the other daemons, apps,
and tools that subscribe to system events. NATS is the
publish/subscribe substrate; Cap'n Proto RPC is the
request/response substrate. The two complement each other.

## Why NATS

- **Subject hierarchy** with wildcards matches our event
  taxonomy naturally (`agent.cycle.*`, `mailbox.*`,
  `audit.*`).
- **Subscriptions are cheap and fan out without daemon
  bookkeeping.** Hooks register subscriptions; we don't keep
  a separate dispatch table.
- **JWT-scoped accounts** isolate apps from each other and
  from system topics without changing the wire format.
- **Embedded mode** runs in-process or as a sibling daemon
  with no extra TCP exposure; the local NATS listens on a
  Unix socket.
- **Mature.** nats-server is widely deployed; nats.rs and
  async-nats are first-class clients.

ZeroMQ, Redis pub/sub, and Kafka were considered. ZeroMQ has
no built-in auth scoping; Redis is heavier than we need;
Kafka is wildly oversized for in-machine eventing.

## Topology

```
                ┌────────────────┐
                │ embedded NATS  │
                │ (nats-server)  │
                │  /run/kiki/    │
                │   nats/nats.sock│
                └───────▲────────┘
                        │ pub/sub
        ┌───────────────┼────────────────┐
        │               │                │
   ┌────┴───┐     ┌─────┴────┐     ┌─────┴────┐
   │ agentd │     │ memoryd  │     │ tools/   │
   │        │     │          │     │ apps     │
   └────────┘     └──────────┘     └──────────┘
```

NATS runs as `kiki-natsd.service`, started at boot. agentd
publishes the bulk of system events; subscribers register on
behalf of hooks, mailbox observers, audit readers, etc.

## Subjects

System subjects use a stable taxonomy:

```
agent.cycle.start                     cycle begins
agent.cycle.complete                  cycle ends
agent.tool.*                          tool dispatch events
agent.thinking.*                      reasoning events

mailbox.message.new                   new message
mailbox.message.read                  read by user
mailbox.message.dismissed             dismissed

policy.grant.created
policy.grant.revoked
policy.gate.denied

inference.route.decided               routing chosen
inference.engine.token                streaming token (rare;
                                      most token streams use
                                      Cap'n Proto stream RPC)
inference.cost.budget                 budget tick

memory.episodic.appended
memory.semantic.fact_added
memory.consent.requested

audit.entry                           a new audit entry
                                      written

system.update.available
system.update.applied
system.health.warn

remote.pairing.created
remote.pairing.revoked
remote.session.connected
remote.session.disconnected

focus.changed                         focusbus changes
                                      (mirrored from
                                      org.kiki.Focus1)

app.<id>.*                            per-app namespace
user.<uid>.*                          per-user namespace
```

Wildcards: `*` matches one token; `>` matches the rest.
Hooks subscribe to e.g. `mailbox.>` or `agent.tool.*`.

### Reserved prefixes

- `agent.`, `mailbox.`, `policy.`, `inference.`, `memory.`,
  `audit.`, `system.`, `remote.`, `focus.` — system; only
  daemons publish.
- `app.<id>.` — owned by an app; the app may publish anything
  under its prefix.
- `user.<uid>.` — daemons publish per-user variants of system
  events here when relevant; user-mode apps may subscribe.

Apps cannot publish to system prefixes; the JWT scope blocks
it.

## Authentication and scoping

NATS in operator mode uses signed JWTs. We run a small
operator/account/user setup:

- **Operator**: the OS image's signing key; established at
  build time
- **System account**: agentd, policyd, inferenced, memoryd,
  toolregistry; full publish on system subjects
- **User accounts** (per system user): per-user `user.<uid>.>`
  prefix, plus subscribe-only on opted-in system subjects
- **App accounts** (per app id): `app.<id>.>` plus
  subscribe-only on whitelisted system subjects per the
  app's manifest

JWT claims encode the allowed publish/subscribe lists. NATS
enforces them server-side.

The local socket transport (see `TRANSPORT-UNIX-SOCKET.md`)
is the auth layer beneath NATS: only authenticated peers may
even open a NATS connection. The JWT is then matched against
the SO_PEERCRED-derived identity.

## Message format

Subject conveys the event kind. Payload is Cap'n Proto when
crossing trust boundaries, JSON when the consumer is a
script or a third-party app that prefers JSON. Schemas live
in `audit.capnp` and `mailbox.capnp` for the structured
events; ad-hoc JSON payloads are namespaced under `app.<id>.>`.

Headers carry:

- `kiki-msg-id` — content hash for dedup
- `kiki-actor` — actor that produced the event
- `kiki-trace-id` — for correlation
- `kiki-schema` — schema name@version when payload is Cap'n
  Proto

## Reliability

NATS Core is at-most-once. We use it for:

- Notifications and ambient events
- Hook fanout (hooks tolerate occasional drop)
- Cross-app focus changes

For at-least-once, we use **JetStream** (NATS' persistence
layer) sparingly:

- The audit log uses a JetStream-backed stream for the live
  tail; the canonical store is the Merkle log on disk
- The mailbox uses JetStream durables for client delivery
  receipts

JetStream storage is bounded:

- Max 256MB across system streams
- Per-subject retention of 24h or 10k messages, whichever
  comes first
- Lost messages on a hard crash are acceptable for non-audit
  paths; the audit Merkle log is the source of truth

## Backpressure

Slow consumers are tracked. NATS' default behavior is to
drop messages on slow subscribers; we configure per-stream
policies:

- System events: drop on slow consumer (the canonical log
  catches up via the audit reader)
- Mailbox: pause publisher (the mailbox is durable; we'd
  rather block the producer briefly than miss a delivery)

A consumer that repeatedly falls behind is logged; agentd's
maintenance loop may unsubscribe a runaway hook.

## Cross-machine

The local NATS does not federate to a cloud. Cross-device
events (paired remotes seeing fleet activity) flow over the
remote protocol, not NATS. The backend has no pub/sub view
of device events.

## Hooks integration

Hooks subscribe to NATS subjects. The hooks subsystem (see
`03-runtime/HOOKS.md`) is a thin adapter: a hook handler is
materialized as a NATS subscriber. The capability gate scopes
which subjects a hook may subscribe to based on the
declaring app's manifest.

When a hook fires synchronously (e.g., `BeforeToolDispatch`
in `intercept` mode), the dispatcher calls the hook over
Cap'n Proto, not NATS — NATS is for async fanout. Hooks
declare their mode (`observe` vs `intercept`) at registration.

## Mailbox integration

Each new mailbox message produces a NATS event on
`mailbox.message.new`; the mailbox UI subscribes via the
launcher or a per-user app. The actual message body fetch
goes through Cap'n Proto for typed access.

## Tools integration

Tools subscribe to `app.<own-id>.>` for their own ad-hoc
needs. They may not publish on system subjects. A tool that
wants to react to e.g. `mailbox.message.read` declares the
subscription in its manifest; toolregistry adds it to the
tool's NATS scope at install time.

## Replay and debugging

```
kiki-bus tail agent.>                  # tail subjects
kiki-bus tail audit.> --from=10m       # JetStream replay
kiki-bus subjects                      # active subjects
kiki-bus subscribers <subject>         # who's listening
kiki-bus pub <subject> <payload>       # for debugging
                                       # (requires kiki-admin)
```

## Configuration

`/etc/kiki/nats.conf` is generated from the system policy:

```hocon
listen: "/run/kiki/nats/nats.sock"
operator: /etc/kiki/jwts/operator.jwt
system_account: SYS
resolver: MEMORY
resolver_preload {
  # account JWTs assembled by policyd at startup
}

jetstream {
  store_dir: /var/lib/kiki/nats/js
  max_memory_store: 64MB
  max_file_store: 256MB
}
```

policyd assembles the account JWTs from the grant table at
startup and on policy changes (hot reload via SIGHUP).

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| nats-server crashes              | systemd restarts; subscribers  |
|                                  | reconnect; some events lost on |
|                                  | non-JetStream subjects         |
| JetStream disk full              | refuse new messages; alert;    |
|                                  | trim oldest                    |
| Slow consumer                    | per-stream policy (drop or     |
|                                  | block)                         |
| JWT signing key compromise       | re-issue accounts; force       |
|                                  | reconnect                      |
| Subscriber leak (hook fires      | timeout the call; mark hook    |
| forever)                         | misbehaving                    |
| Subject typo in publish          | message delivered to nobody;   |
|                                  | logged at debug                |

## Performance contracts

- Publish to local subscriber: <100µs typical
- Fanout to 100 subscribers: <1ms
- JetStream durable ack: <5ms p99
- Subjects per server: 100k+ (not a bottleneck for our scale)

## Acceptance criteria

- [ ] All system subjects published with the correct schema
      version
- [ ] Account JWTs assembled correctly at startup; apps see
      only their own subjects + whitelisted system ones
- [ ] JetStream-backed mailbox delivers reliably across
      restarts
- [ ] Slow consumer doesn't block the publisher on best-
      effort streams
- [ ] CLI tail/replay works for debugging

## Open questions

None.

## References

- `03-runtime/AGENTD-DAEMON.md`
- `03-runtime/EVENT-BUS.md`
- `03-runtime/HOOKS.md`
- `03-runtime/MAILBOX.md`
- `05-protocol/CAPNP-RPC.md`
- `05-protocol/TRANSPORT-UNIX-SOCKET.md`
- `10-security/AUDIT-LOG.md`
## Graph links

[[AGENTD-DAEMON]]  [[TRANSPORT-UNIX-SOCKET]]  [[CAPABILITY-GATE]]
