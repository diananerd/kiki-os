---
id: dns-resolution
title: DNS Resolution
type: SPEC
status: draft
version: 0.0.0
implements: [dns-stack]
depends_on:
  - network-stack
  - init-system
depended_on_by: []
last_updated: 2026-04-29
---
# DNS Resolution

## Purpose

Specify the DNS stack: systemd-resolved as the resolver, DNS-over-TLS (DoT) by default, the `inference.local` virtual hostname mechanism, and per-app namespace DNS access.

## Behavior

### systemd-resolved

systemd-resolved is the system DNS resolver. It runs on host and exposes a stub resolver at `127.0.0.53:53`.

Configuration in `/etc/systemd/resolved.conf`:

```ini
[Resolve]
DNS=1.1.1.1#cloudflare-dns.com 9.9.9.9#dns.quad9.net
FallbackDNS=
DNSOverTLS=opportunistic
DNSSEC=allow-downgrade
Cache=yes
DNSStubListener=yes
ReadEtcHosts=yes
```

Defaults:

- DoT (DNS-over-TLS) opportunistic. Used when the upstream resolver supports it.
- DNSSEC validation when the zone is signed.
- Cloudflare 1.1.1.1 and Quad9 9.9.9.9 as upstreams. User can change.

### DoT and DoH

DoT is the default privacy-enhancing measure. DoH (DNS-over-HTTPS) is not enabled by default; if a user wants DoH, they configure a forwarder like `dnscrypt-proxy` or use Cloudflare's hidden HTTPS resolver.

### inference.local

Kiki's `inference.local` virtual hostname is resolved locally:

```
/etc/systemd/resolved.conf.d/inference.conf
[Resolve]
Domains=~inference.local
```

Plus an entry in `/etc/hosts` (managed by Kiki):

```
127.0.0.1   inference.local
```

When an app or daemon looks up `inference.local`, it gets `127.0.0.1`, where `inferenced` listens. This way, agents in containers reach `inferenced` without leaking provider URLs into app code.

### Per-app namespace DNS

App containers have their own network namespaces. By default, they would not have DNS resolution because `127.0.0.53` is in the host namespace.

Solution: each container's namespace runs a tiny DNS forwarder (or uses an iptables redirect rule) that forwards to `host:53`. Apps see their stub at `127.0.0.53:53` as if on the host.

systemd-resolved on the host handles the actual lookup. The app's outbound iptables rules then check the resolved IP against the allowlist; if the app's Profile says `outbound_hosts: [https://api.example.com]`, the lookup succeeds, but the connection to a different IP would still be denied.

### DNS over kill switches

When a hardware kill switch disconnects the radio, NetworkManager reports no network. systemd-resolved fails with EAI_AGAIN. Apps handle the offline state.

### Caching

systemd-resolved caches DNS responses per its TTL. Cache size is bounded.

### Custom domains

Users can add custom hostnames via:

```
agentctl network add-host <name> <ip>
```

Which writes to a managed entry in `/etc/hosts`. agentctl is the only writer; systemd-resolved reads.

### Privacy

DNS lookups go to the user's chosen upstream. DoT prevents passive observation. The user can change upstream in:

```
agentctl network set-dns 1.1.1.1
```

For maximum privacy, a user can configure a self-hosted resolver on their LAN, point systemd-resolved at it. Kiki does not run its own recursive resolver.

## Interfaces

### CLI

```
resolvectl status                  # systemd-resolved status (developer mode)
resolvectl query <hostname>        # debug query
agentctl network dns               # user-friendly status
agentctl network set-dns <server>  # change upstream
agentctl network add-host <name> <ip>
```

## State

### Persistent

- /etc/systemd/resolved.conf and drop-ins.
- /etc/hosts (managed by Kiki).

### In-memory

- DNS cache.
- Per-namespace forwarder state (negligible).

## Failure modes

| Failure | Response |
|---|---|
| Upstream DNS unreachable | systemd-resolved fails over; if all upstreams fail, queries fail |
| DoT handshake fails | falls back to plain DNS (per `DNSOverTLS=opportunistic`) |
| Captive portal blocking DNS | NetworkManager detects; surfaces to user |
| inference.local resolution misconfigured | inferenced unreachable; fallback paths in inference router |

## Performance contracts

- Cache hit: <1ms.
- Cache miss with DoT: 20–100ms (network-bounded).
- Per-namespace forwarder overhead: <2ms.

## Acceptance criteria

- [ ] systemd-resolved active with DoT opportunistic.
- [ ] DNSSEC validation enabled for signed zones.
- [ ] Per-app namespaces resolve via host stub.
- [ ] inference.local resolves to 127.0.0.1.
- [ ] User can change DNS upstream.

## Open questions

- Whether to default to DoH instead of DoT in v1 (broader adoption, easier through firewalls).

## References

- `02-platform/NETWORK-STACK.md`
- `02-platform/INIT-SYSTEM.md`
- `03-runtime/INFERENCE-ROUTER.md`
## Graph links

[[NETWORK-STACK]]  [[INIT-SYSTEM]]
