---
id: agentd-daemon
title: agentd Daemon
type: SPEC
status: draft
version: 0.0.0
implements: [agent-harness-daemon]
depends_on:
  - process-model
  - sandbox
  - capability-taxonomy
depended_on_by:
  - agent-loop
  - capability-gate
  - capnp-rpc
  - coordinator
  - dbus-integration
  - event-bus
  - hooks
  - iceoryx-dataplane
  - inference-router
  - loop-budget
  - mailbox
  - memory-architecture
  - nats-bus
  - remote-architecture
  - subagents
  - tool-dispatch
  - toolregistry
  - update-orchestrator
  - workspace-lifecycle
last_updated: 2026-04-30
---
# agentd Daemon

## Purpose

Specify the central agent harness daemon: process structure, configuration, startup sequence, internal task organization, lifecycle management, and integration points with every other runtime component.

`agentd` is the supervisor and orchestrator of the agent runtime. The other four daemons (`policyd`, `inferenced`, `memoryd`, `toolregistry`) are specialized peers; `agentd` coordinates them.

## Inputs

- Configuration at `/etc/kiki/agentd.toml` (static) and `/var/lib/kiki/agentd-runtime.toml` (hot-reload).
- Hardware manifest at `/etc/kiki/hardware-manifest.toml`.
- Identity files (SOUL.md, IDENTITY.md, USER.md).
- Apps registered in `toolregistry`.
- Local model files referenced by `inferenced`.
- Memory subsystem databases via `memoryd`.

## Outputs

- A running daemon listening on `/run/kiki/agentd.sock`.
- Tool dispatch via Cap'n Proto to apps and to peer daemons.
- Audit log entries.
- Memory writes via `memoryd`.
- Surface render commands via `agentui`.

## Behavior

### Process identity

```
binary: /usr/lib/kiki/agentd
uid:    kiki-runtime (dedicated)
caps:   minimal — relies on systemd directives, not capabilities
```

Runs as `kiki-runtime` user; not root after init.

### Internal task organization

`agentd` is a single tokio multi-thread process:

```
├── event_bus_task                  central event router (priority biased)
├── perception_input_tasks
│   ├── voice                       from kiki-voiced
│   ├── touch                       from agentui
│   ├── messaging                   from messaging bridges
│   └── hardware_event              from HAL daemons via DBus
├── service_listener_tasks          one per registered app service (lazy)
├── tool_dispatch_workers           pool for concurrent tool calls
├── coordinator_task                per-active-user agent loop
├── subagent_manager_tasks          one per active subagent
├── mailbox_task                    routes async messages
├── memory_io_tasks                 batched calls to memoryd
├── audit_log_writer_task           append-only writes via SQLite + ct-merkle
├── workspace_manager               per-user workspace lifecycle
├── update_orchestrator             OTA channel coordination
└── health_telemetry_task           local DuckDB metrics
```

### Concurrency rules

- One inference at a time per primary agent.
- Subagent inference is parallel.
- Tool dispatch is parallel.
- Memory and audit writes serialized.
- Per-user state isolated.

### Startup sequence

```
1. systemd starts agentd.
2. Read /etc/kiki/agentd.toml; validate schema.
3. Read hardware manifest; verify signature.
4. Connect to memoryd; verify integrity.
5. Initialize audit log writer; verify hash chain.
6. Connect to policyd; load capability grants.
7. Open Cap'n Proto socket on /run/kiki/agentd.sock.
8. Connect to inferenced; warm up local model.
9. Connect to toolregistry; discover registered tools.
10. Connect to kiki-voiced (if present).
11. Start coordinator per active user.
12. systemd-notify READY=1.
13. Begin processing events.
```

Total startup: 8–12s on reference hardware.

### Event-driven core

```rust
loop {
    tokio::select! {
        biased;
        evt = event_bus.recv_critical() => handle(evt).await,
        evt = event_bus.recv_high() => handle(evt).await,
        evt = event_bus.recv_internal() => handle(evt).await,
        evt = event_bus.recv_normal() => handle(evt).await,
        evt = event_bus.recv_background() => handle(evt).await,
        ctl = control_signal.recv() => handle_control(ctl).await,
    }
}
```

### Multi-user

agentd tracks per-user state. Active user determined by speaker ID, active session, or messaging channel ownership. Per-user state in working memory, isolated.

### Configuration hot-reload

`/var/lib/kiki/agentd-runtime.toml` is watched; changes reload without restart. Static config requires restart.

## Interfaces

### Local socket

`/run/kiki/agentd.sock` — Cap'n Proto. Apps connect via SDK.

### kiki-bus events

`agentd/state` (ready, busy), `agentd/inference` (start, complete), `agentd/tool_call`.

### Signals

```
SIGTERM    graceful shutdown
SIGUSR1    reload runtime config
SIGUSR2    dump diagnostic state
```

### CLI

```
agentctl status
agentctl reload
agentctl users
agentctl grants summary
```

## State

In-memory: event bus channels, per-user UserState, active subagents, mailbox queue, tool dispatch worker pool, cached app manifests.

Persistent: audit log, capability grants (redb), memory subsystem, mailbox.

### Crash recovery

systemd restarts. Memory state recovered from disk. Mailbox messages replayed. In-flight tool calls lost (apps see drop). Working memory for active conversations rebuildable from journal. ~12s restart.

## Failure modes

| Failure | Response |
|---|---|
| Config invalid | refuse to start; clear error |
| Hardware manifest invalid | refuse |
| Memory subsystem corrupt | start in read-only mode; alert |
| Local model load fails | continue; router falls back |
| Audit log write fails | crash (audit mandatory) |
| 4 crashes in 60s | maintenance mode |

## Performance contracts

- Idle CPU: <2% averaged.
- Idle RAM: <4 GB (without LLM models).
- Inference dispatch latency: ~5ms.
- Tool dispatch latency (warm service): <5ms.
- Boot to ready: 8–12s.

## Acceptance criteria

- [ ] agentd starts within 12s on reference hardware.
- [ ] Survives app crashes.
- [ ] Survives memoryd unavailable (degraded mode).
- [ ] Hot-reloads runtime config.
- [ ] Records every capability decision in audit log.
- [ ] Restart from crash recovers state.
- [ ] Multi-user switching without state leakage.

## References

- `03-runtime/AGENT-LOOP.md`
- `03-runtime/COORDINATOR.md`
- `03-runtime/EVENT-BUS.md`
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/TOOL-DISPATCH.md`
- `03-runtime/MAILBOX.md`
- `04-memory/MEMORY-ARCHITECTURE.md`
- `05-protocol/CAPNP-RPC.md`
