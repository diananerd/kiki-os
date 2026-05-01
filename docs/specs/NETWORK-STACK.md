---
id: network-stack
title: Network Stack
type: SPEC
status: draft
version: 0.0.0
implements: [networking]
depends_on:
  - sandbox
  - init-system
depended_on_by:
  - dns-resolution
last_updated: 2026-04-30
---
# Network Stack

## Purpose

Specify the network stack: how connectivity is configured, how per-app network namespaces enforce isolation, what policies apply to outbound traffic.

## Behavior

### NetworkManager as connectivity manager

NetworkManager is the user-facing network manager. It handles:

- Wi-Fi network selection and authentication (WPA, WPA3, captive portals).
- Wired Ethernet auto-configuration.
- VPN integration (OpenVPN, WireGuard plugins).
- Hotspot and mobile broadband (where applicable).

We use NetworkManager rather than systemd-networkd because:

- Wi-Fi UX (captive portal, dynamic networks) is much better.
- Roaming between networks is solid.
- GUI/IPC integration via DBus is mature.

NetworkManager runs as a system service (Category B) and exposes its DBus interface. agentd subscribes to network state changes.

### Per-app network namespaces

Each app container has its own network namespace. The default policy is **deny all outbound, deny all inbound**.

The app's Profile declares allowed outbound hosts:

```yaml
network:
  outbound_hosts:
    - https://api.example.com
    - https://cdn.example.com
  outbound_local: false       # connect to LAN hosts
  inbound_local: false        # accept LAN connections
  inbound_wan: false          # accept WAN connections (always denied for apps)
```

The container's network namespace is configured with iptables/nftables rules permitting only the declared outbound destinations.

### Namespace topology

```
Host network (NetworkManager-managed)
   │
   ├── kiki-runtime (no namespace; agentd, etc., share host network)
   │
   ├── App namespace 1 (kiki-acme-notes)
   │     veth-pair to host bridge
   │     iptables rules per Profile
   │
   ├── App namespace 2 (kiki-foo-app)
   │     ...
   │
   └── ...
```

App namespaces communicate with the host via veth pairs into a host bridge. Each app's iptables rules permit only declared outbound destinations.

App-to-app communication via the network is impossible by default (apps in different namespaces, host bridge does not route between them). Apps communicate via Cap'n Proto over Unix sockets to agentd.

### DNS

DNS resolution is done via systemd-resolved (running on host). App namespaces are configured to use the host's resolver via a stub DNS server in their namespace. systemd-resolved does the actual resolution.

The app sees `127.0.0.53:53` as its DNS server (the systemd-resolved stub address). Detail in `02-platform/DNS-RESOLUTION.md`.

### Outbound enforcement

When an app calls `connect()`:

```
1. Container's connect syscall sees declared netns.
2. iptables OUTPUT chain checks destination.
3. If destination matches declared host (resolved via DNS), permit.
4. If destination not in allowlist, REJECT with EPERM.
5. agentd's audit log records the connection attempt outcome.
```

Apps requesting "any host" are flagged at install for review. The default policy is per-host or per-API-class, not wildcard.

### Inbound

Apps almost never need inbound. The default is deny. Apps that legitimately need to listen (e.g., a local web server for development) declare:

```yaml
network:
  inbound_local: true
  listen_ports: [8080]
```

The app's namespace permits inbound on declared ports from the host. Cross-namespace inbound (other app reaches this app's port) is still blocked unless explicitly granted.

WAN inbound is always denied for apps. If an app must accept WAN traffic, it does so via the backend's relay protocol, not direct WAN exposure.

### VPN

User can configure VPN via NetworkManager. When VPN is active, all app traffic routes through the VPN by default (host's default route changes). Apps remain in their namespaces; their veth pairs connect to the host bridge, which routes via the VPN.

### Hotspot / tethering

Hotspot is supported via NetworkManager. Off by default; user opt-in.

### Hardware kill switches

Hardware kill switches for Wi-Fi/Bluetooth/cellular are honored at the HAL level (per `02-platform/HARDWARE-KILL-SWITCHES.md`). When a kill switch is engaged:

- The radio is physically disconnected.
- NetworkManager reports the radio as off.
- Apps cannot reach the network through that radio.

The OS does not falsely report network availability when a hardware switch is off.

### IPv6

IPv6 is enabled by default. NetworkManager handles auto-configuration. Apps can use either IPv4 or IPv6 transparently.

### Captive portals

NetworkManager detects captive portals. agentd surfaces a notification: "Sign in to <network> to access the internet." The user can complete the captive portal sign-in via a Servo-rendered block in agentui.

## Interfaces

### NetworkManager DBus

```
org.freedesktop.NetworkManager
   ├── ActiveConnections
   ├── Devices
   ├── Settings
   └── ...
```

agentd uses zbus to query and subscribe.

### CLI

```
nmcli                              # NetworkManager CLI (developer mode)
agentctl network status            # user-friendly summary
agentctl network connect <ssid>    # via agent prompt for password
```

## State

### Persistent

- NetworkManager configurations in /etc/NetworkManager/.
- VPN credentials per user (encrypted).

### In-memory

- Active connections.
- Per-app namespace state.

## Failure modes

| Failure | Response |
|---|---|
| No connectivity | system continues offline; apps that require network see EHOSTUNREACH |
| DNS resolution fails | systemd-resolved reports; apps see EAI_AGAIN |
| Per-app netns setup fails | container does not start |
| iptables rules fail to apply | container does not start; alert |
| VPN connection drops | NetworkManager retries; apps see brief connectivity gap |

## Performance contracts

- Connection establishment to allowed host: typical TCP handshake (10s of ms).
- Per-app netns setup overhead at container start: ~10ms.
- iptables rule check: <10µs.

## Acceptance criteria

- [ ] NetworkManager is the connectivity manager.
- [ ] Per-app netns enforces declared outbound hosts.
- [ ] Apps cannot reach undeclared hosts.
- [ ] Hardware kill switches reflect in NetworkManager state.
- [ ] VPN integration works.
- [ ] Captive portals surfaced via agentui.

## Open questions

- Whether to support nftables-only (deprecate iptables compatibility) when ready.

## References

- `02-platform/SANDBOX.md`
- `02-platform/DNS-RESOLUTION.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `02-platform/HARDWARE-KILL-SWITCHES.md`
## Graph links

[[SANDBOX]]  [[INIT-SYSTEM]]
