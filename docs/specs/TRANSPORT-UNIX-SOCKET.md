---
id: transport-unix-socket
title: Unix-Socket Transport
type: SPEC
status: draft
version: 0.0.0
implements: [transport-unix-socket]
depends_on:
  - sandbox
  - process-model
depended_on_by:
  - capnp-rpc
  - dbus-integration
  - nats-bus
last_updated: 2026-04-30
---
# Unix-Socket Transport

## Purpose

Specify the local-socket layer used by Cap'n Proto RPC, the
embedded NATS server's local listeners, and Unix-DBus for
desktop integration. This layer's job is connection
authentication, lifecycle, and isolation — not framing.

The Cap'n Proto, NATS, and DBus protocols all share the same
underlying socket discipline; gathering it here keeps the
authentication story in one place.

## Inputs

- A peer connecting to a known socket path
- The kernel's SO_PEERCRED metadata
- The process's sandbox profile (Landlock + AppArmor)
- The user account database

## Outputs

- An authenticated connection with an attached identity
- A capability binding (the connection's "actor token")
- An audit entry on connect/disconnect for sensitive sockets

## Behavior

### Why Unix sockets

- **Kernel-mediated authentication.** SO_PEERCRED gives uid,
  gid, and pid of the peer. No tokens to steal, no MAC to
  forge. The kernel is the witness.
- **No network exposure.** Sockets in `/run/kiki/` are not
  reachable off-box. Local-first by construction.
- **Cheap.** No TLS, no certificate management. Latency is
  microseconds.
- **Sandbox-friendly.** Landlock and AppArmor know how to
  describe Unix-socket reachability per process.

TCP loopback is not used between local components. Remote
components use mTLS over TCP (see remotes).

### Socket layout

```
/run/kiki/                              shared system sockets
├── agentd.sock                         agentd public RPC
├── policyd.sock                        policyd RPC
├── inferenced.sock                     inference RPC
├── memoryd.sock                        memory RPC
├── toolregistry.sock                   tool registry RPC
├── nats/                               NATS local listener
│   └── nats.sock
├── focusbus.sock                       focusbus
├── tools/                              per-tool persistent
│   └── <id>.sock                       sockets
└── users/<uid>/                        per-user sockets
    ├── agentd.sock                     user-scoped agentd
    ├── voice.sock                      voice control plane
    └── apps/<app>.sock                 app-private sockets
```

DBus uses the standard system bus path
`/run/dbus/system_bus_socket` and per-session path
`/run/user/<uid>/bus`; these are managed by dbus-broker
(see `DBUS-INTEGRATION.md`).

### File modes and ownership

```
/run/kiki/                            kiki:kiki  0750
/run/kiki/*.sock (system)             kiki:kiki  0660
/run/kiki/users/<uid>/                <uid>:kiki 0750
/run/kiki/users/<uid>/*.sock          <uid>:kiki 0660
/run/kiki/tools/<id>.sock             tool-uid:kiki 0660
```

Sockets are created by their owning daemon at startup with
explicit `umask` and post-bind `chmod`. Socket activation via
systemd is supported but not required; agentd creates its own
sockets to keep startup ordering explicit.

### SO_PEERCRED on connect

Server side, immediately after `accept()`:

1. `getsockopt(fd, SOL_SOCKET, SO_PEERCRED, ...)` →
   `(uid, gid, pid)`
2. Resolve `pid` to a process (exe path, cgroup, AppArmor
   label, capabilities) via `/proc/<pid>/`. Read once at
   connect; do not re-read (the pid may be reused later).
3. Match the (exe, AppArmor label, cgroup) against the
   expected identity for the socket. For example, the
   `policyd.sock` listener may only accept connections from
   processes labelled `kiki-agentd`.
4. If the match fails, log a warning and close the
   connection.
5. If it passes, attach an `ActorRef` to the connection state
   identifying the caller (system component, app id, user,
   pairing).

The `ActorRef` is the key fed into the capability gate for
every operation that crosses the connection.

### Identity resolution

The server resolves the peer to one of:

- **System component**: by AppArmor label
  (`kiki-agentd`, `kiki-policyd`, etc.)
- **App tool**: by AppArmor label `kiki-tool-<app>` and by
  cgroup membership in the app's slice
- **User process**: by uid, with no specific app affiliation
  (e.g., a `kiki` CLI invocation)
- **Remote pairing**: via the `mTLS` proxy on a separate
  socket (see remotes)

Mismatches always close the connection.

### Connection lifecycle

```
1. Client connects.
2. Server reads SO_PEERCRED, resolves identity.
3. Server attaches ActorRef + Bootstrap capability.
4. Protocol-specific handshake (Cap'n Proto, NATS, DBus).
5. Operation phase.
6. Client closes (or server closes on idle/policy).
7. Server tears down state owned by the connection
   (capabilities, subscriptions, queued work).
```

Idle timeout: 600s default. The agent loop's session has its
own keepalive and is exempt from idle timeout while a
session is active.

### Buffer sizes and flow control

- `SO_SNDBUF` and `SO_RCVBUF` set to 256KB at accept (tunable
  per socket).
- Cap'n Proto and NATS handle their own framing and
  backpressure on top.
- For streaming, the server applies high-watermark
  backpressure: pause reads if the outgoing buffer exceeds
  64KB.

### Sandbox interaction

A daemon's sandbox profile lists exactly which sockets it may
read or connect to:

```
# Landlock + AppArmor: kiki-agentd
allow connect /run/kiki/policyd.sock
allow connect /run/kiki/inferenced.sock
allow connect /run/kiki/memoryd.sock
allow connect /run/kiki/toolregistry.sock
allow listen /run/kiki/agentd.sock
allow listen /run/kiki/users/*/agentd.sock
deny connect /**
```

Tools have a stricter profile: they may listen on their own
`/run/kiki/tools/<id>.sock` and connect to nothing else
unless their manifest grants it.

### Multiplexing

A single socket carries one logical stream per connection.
Cap'n Proto multiplexes RPCs over that stream internally.
NATS multiplexes subjects. DBus multiplexes
service-name/path/interface/method.

### Authentication beyond SO_PEERCRED

For some operations, kernel-derived identity is not enough:

- A capability that requires user consent (e.g., the
  capability gate's prompt flow) needs explicit user input
  via the mailbox; the socket only proves *who* asked, not
  *that the user agreed*.
- A capability that requires re-authentication (elevated
  consent) layers a passphrase or biometric step on top.

The transport's job ends at "you are who you say you are";
authorization is the gate's job.

### Error reporting

Connection-level errors (refused, closed mid-handshake,
timed out) are reported to the local audit channel only;
they are not surfaced to remote clients to avoid leaking
internal topology. Per-call errors are protocol-specific and
follow `ERROR-MODEL.md`.

### Privileged sockets

Some sockets are reachable only by root or kiki-admin:

- `/run/kiki/maintenance.sock` — recovery operations
- `/run/kiki/keyring.sock` — accessing decryption keys
  (mediated by `policyd`)

These check `(uid, gid)` against an explicit allowlist before
proceeding past the handshake.

## Interfaces

### Programmatic

```rust
struct PeerIdentity {
    uid: u32,
    gid: u32,
    pid: u32,
    exe_path: PathBuf,
    cgroup_path: PathBuf,
    apparmor_label: Option<String>,
    actor: ActorRef,
}

trait SocketServer {
    fn bind(&self, path: &Path) -> Result<UnixListener>;
    fn accept(&self, listener: &UnixListener)
              -> Result<(UnixStream, PeerIdentity)>;
}
```

### CLI

```
kiki-sock list                       # what daemons are listening
kiki-sock peers /run/kiki/agentd.sock
                                     # current peers + identities
kiki-sock check <peer-pid> <socket>  # would the connection be
                                     # accepted? (dry-run)
```

### Configuration

`/etc/kiki/transport.toml`:

```toml
[transport]
idle_timeout_seconds = 600
sndbuf_kb = 256
rcvbuf_kb = 256

[transport.audit]
log_connect = ["policyd.sock", "memoryd.sock"]
log_disconnect = ["policyd.sock", "memoryd.sock"]
```

## State

### Persistent

- The socket files themselves
- The transport audit log entries

### In-memory

- Per-connection PeerIdentity
- Idle-timer state

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| SO_PEERCRED returns invalid data | close connection; alert        |
| /proc/<pid>/ unreadable          | log; reject if identity needed |
| AppArmor label mismatches        | refuse connection              |
| Socket file removed externally   | daemon recreates on next       |
|                                  | listen; alert maintenance      |
| Buffer high-watermark hit        | pause reads; resume after      |
|                                  | drain                          |
| Permission change at runtime     | systemd path watch fires;      |
|                                  | daemon resets perms or alerts  |

## Performance contracts

- accept() to handshake start: <100µs
- Identity resolution: <500µs typical
- 10k concurrent connections: feasible (Unix sockets are
  cheap; bound by FDs and memory)

## Acceptance criteria

- [ ] All sockets created with correct mode, owner, and label
- [ ] Mismatched AppArmor labels are rejected
- [ ] SO_PEERCRED is read once and cached for the connection
- [ ] Tools cannot reach sockets their profile doesn't permit
- [ ] Idle timeout closes stale connections
- [ ] Connection-level audit is recorded for sensitive sockets

## Open questions

None.

## References

- `05-protocol/CAPNP-RPC.md`
- `05-protocol/NATS-BUS.md`
- `05-protocol/DBUS-INTEGRATION.md`
- `02-platform/SANDBOX.md`
- `01-architecture/PROCESS-MODEL.md`
## Graph links

[[SANDBOX]]  [[PROCESS-MODEL]]
