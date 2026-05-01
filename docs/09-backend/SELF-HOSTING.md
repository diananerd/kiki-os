---
id: self-hosting
title: Self-Hosting
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - backend-contract
  - device-auth
  - ota-distribution
  - ai-gateway
  - memory-sync
  - registry-protocol
  - namespace-federation
last_updated: 2026-04-30
---
# Self-Hosting

## Purpose

Walk through running the five backend services on your own infrastructure: a LAN server, a small cloud VM, or a private cloud. The reference implementations are open source and small.

## Reference deployment

A single host can run a viable backend for a household or small org:

```
host:
├── caddy / traefik       reverse proxy + Let's Encrypt
├── kiki-auth             device auth + provisioning CA
├── zot                    OCI registry (OTA + namespace artifacts)
├── kiki-namespace        namespace registry
├── kiki-gateway          AI gateway (optional)
└── kiki-sync             memory sync (optional)
```

All Rust services; ~50MB each. Docker Compose or systemd-managed.

## Reference docker-compose

```yaml
version: "3.8"
services:
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: ["./caddy:/etc/caddy"]

  auth:
    image: kiki/auth-reference:latest
    environment:
      KIKI_AUTH_CA_KEY: /run/secrets/ca_key
    secrets: [ca_key]

  zot:
    image: ghcr.io/project-zot/zot:latest
    volumes: ["./zot:/var/lib/zot"]
    ports: ["5000:5000"]

  namespace:
    image: kiki/namespace-reference:latest
    volumes: ["./namespace:/var/lib/namespace"]

  gateway:
    image: kiki/gateway-reference:latest
    secrets: [providers_yml]

  sync:
    image: kiki/sync-reference:latest
    volumes: ["./sync:/var/lib/sync"]
```

## Caddy / Traefik

Reverse proxy + automatic TLS. Routes:

- `auth.example.com` → kiki-auth
- `registry.example.com` → zot
- `namespace.example.com` → kiki-namespace
- `ai.example.com` → kiki-gateway
- `sync.example.com` → kiki-sync

## Domain setup

You need a domain with proper TLS:

- A wildcard cert for `*.example.com`, or
- Per-subdomain Let's Encrypt certs

DNS A records pointing at the host.

## Initial CA setup

```
kiki-auth init-ca \
  --ca-key=ca.key \
  --ca-cert=ca.crt \
  --validity-years=20 \
  --org="My Household"
```

The CA cert is what your devices will pin during provisioning.

## Bootstrapping a device

When provisioning a Kiki device, point it at your backend:

```
kiki provision \
  --auth-server=https://auth.example.com \
  --ota-server=https://registry.example.com \
  --namespace-server=https://namespace.example.com \
  --ca-cert=ca.crt
```

The device installs the CA, generates a CSR, gets a cert, and is ready.

## Mirroring upstream

For OTA, you can:

- **Pull-through cache**: zot fetches Kiki Foundation artifacts on demand
- **Pre-mirror**: periodically replicate the channels you care about

Pull-through is simplest; pre-mirror suits air-gapped.

## Namespace registry

Register your private namespaces:

```
kiki-namespace add \
  --namespace=myorg \
  --registry=registry.example.com/myorg \
  --sigstore-identity '^https://github.com/myorg/.*'
```

Your devices' configs add `namespace.example.com` to their registry list.

## AI gateway

Configure providers and budgets:

```yaml
# /etc/kiki-gateway/config.yaml
providers:
  - name: claude
    type: anthropic
    api_key_env: ANTHROPIC_API_KEY
    allow:
      - tools_calling
      - thinking
  - name: local-llamacpp
    type: openai-compatible
    base_url: http://localhost:8080
    api_key: ""

users:
  - id: alice
    monthly_token_limit_in: 10000000
    monthly_token_limit_out: 2500000
    allowed_providers: ["claude", "local-llamacpp"]
```

## Memory sync

Set up storage; the service is otherwise stateless beyond per-user encrypted records:

```yaml
# /etc/kiki-sync/config.yaml
storage:
  kind: filesystem
  root: /var/lib/sync
limits:
  per_user_quota_gb: 5
  retention_days: 365
```

## Backups

Back up:

- The CA key (offline storage)
- Registry storage
- Sync storage
- Gateway provider keys (separately encrypted)

Run periodically; test restoration.

## Monitoring

Metrics endpoints (Prometheus-compatible) on each service. Recommended dashboards:

- Auth: cert issuance, renewal latency
- OTA: pull bandwidth, cache hit rate
- Gateway: per-user usage, provider error rates
- Sync: per-user storage, replication lag

## Updates

Update reference services like any other Rust service:

```
docker-compose pull
docker-compose up -d
```

Configs are backward-compatible across minor versions; major bumps documented.

## Multi-tenant

The reference services support multiple users / households. For org deployments, run a single instance per org with per-user accounts; no need for one VM per user.

## Air-gapped

For air-gapped: pull artifacts via a transit machine, push to your local zot. The device's namespace and OTA servers can be local-only.

## Anti-patterns

- Running auth on the same host as untrusted services
- Skipping TLS or using self-signed without device pinning
- Not backing up the CA key
- Letting any service auto-update without testing

## Acceptance criteria

- [ ] Reference compose runs with TLS
- [ ] A device provisions against the self-hosted backend end-to-end
- [ ] OTA pulls from your zot
- [ ] Namespace lookup resolves your private namespace
- [ ] Gateway and sync serve their reference flows
- [ ] Backups + restore tested

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/DEVICE-AUTH.md`
- `09-backend/DEVICE-PROVISIONING.md`
- `09-backend/OTA-DISTRIBUTION.md`
- `09-backend/AI-GATEWAY.md`
- `09-backend/MEMORY-SYNC.md`
- `09-backend/REGISTRY-PROTOCOL.md`
- `09-backend/NAMESPACE-FEDERATION.md`
- `12-distribution/REGISTRY-OPERATIONS.md`
## Graph links

[[BACKEND-CONTRACT]]  [[DEVICE-AUTH]]  [[OTA-DISTRIBUTION]]  [[AI-GATEWAY]]  [[MEMORY-SYNC]]  [[REGISTRY-PROTOCOL]]  [[NAMESPACE-FEDERATION]]
