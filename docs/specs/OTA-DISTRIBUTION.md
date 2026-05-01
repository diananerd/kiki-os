---
id: ota-distribution
title: OTA Distribution
type: SPEC
status: draft
version: 0.0.0
implements: [ota-distribution]
depends_on:
  - backend-contract
  - device-auth
  - oci-native-model
  - update-orchestrator
  - cosign-trust
depended_on_by:
  - self-hosting
last_updated: 2026-04-30
---
# OTA Distribution

## Purpose

Specify the over-the-air update path: how a device pulls new system images, sysext updates, app updates, model updates, and (optionally) profile updates from a backend mirror. The protocol is OCI distribution; the backend is a regular OCI registry plus a small announce/poll layer.

## What gets distributed

```
base image      bootc, atomic
sysext          incremental daemon updates between base bumps
apps            normal container updates
components       OCI artifacts
models           OCI artifacts (large; resumable)
profiles         OCI artifacts (small)
prompts pack     OCI artifacts (small)
```

Plus the metadata layer:

- Channel index (which version is current per channel)
- Release notes (attached as OCI attestations)
- Advisories (security stream)

## Flow

```
1. Update orchestrator polls the channel index every N minutes
   (configurable; default 30m) or receives a push hint.
2. For each artifact, compares device's installed version vs channel.
3. If new, pull artifact (resumable, bandwidth-aware).
4. Verify cosign + Sigstore.
5. Stage; run health checks (eval suite for models; smoke tests for
   sysexts).
6. Apply atomically (bootc commit; sysext refresh; podman image swap).
7. On success, retain prior version for grace; on failure, rollback.
8. Audit the apply.
```

## Channels

```
stable / beta / nightly
```

Per-class, the device tracks a channel. See `RELEASE-CADENCE.md`.

## Security stream

A separate URL pattern that all channels subscribe to for advisory updates:

```
GET https://ota.example/security/v1/advisories
```

Returns the list of versions affected and replacement versions. The orchestrator can prioritize security pulls.

## Resumable downloads

Models in particular are large (>5GB). Pulls use HTTP range requests and chunk hashes to resume on interruption.

```
1. Fetch artifact manifest
2. For each layer/blob, check local cache by digest
3. Pull missing portions; verify per-chunk
4. Re-verify the full digest after assembly
```

## Bandwidth awareness

The orchestrator respects:

- Connection type (Wi-Fi vs metered cellular)
- Battery state (don't pull big artifacts on battery)
- Idle time (download during user-idle windows)
- User's policy (Settings → Updates → "only on Wi-Fi", etc.)

## Mirror availability

Mirrors federate; devices can fall over to alternates if the primary is down. The device stores mirror priority in its config:

```toml
[ota.mirrors]
primary = "ota.example/kiki"
fallback = ["mirror.example/kiki", "another.mirror.example/kiki"]
```

## Push hints

For faster updates, backends can send push notifications via a per-device APNs/FCM-like channel (when network allows). Push is a *hint*; the device still pulls and verifies. Push is opt-in.

## Auth

All OTA traffic uses mTLS device certs (per `DEVICE-AUTH.md`). Public mirrors may also serve unauthenticated for public channels (the artifacts are signed; auth on read is mostly for accounting).

## Self-hosted mirror

Run zot, harbor, or distribution and seed it with the desired channels. Configure the device to point at it. Can be combined with a separate backend for auth + announce, or be the authoritative source itself.

## Privacy

OTA reveals to the mirror operator: which device pulled which version when. To minimize, mirrors can be configured to rate-aggregate logs; the user can route OTA through a relay/Tor for full privacy at the cost of speed.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Mirror unreachable               | failover; if all unreachable,  |
|                                  | retry with backoff             |
| Signature verification fails     | refuse install; alert          |
| Health check fails post-stage    | rollback                       |
| Disk full during pull            | clean cache; retry             |
| Channel index inconsistent       | flag; alert maintainer         |

## Acceptance criteria

- [ ] Channel polling honors cadence
- [ ] Resumable pulls work for large artifacts
- [ ] Security stream prioritized
- [ ] Bandwidth/policy honored
- [ ] Self-hosted mirror works end-to-end
- [ ] Verification mandatory pre-apply
- [ ] Rollback on health-check failure

## References

- `09-backend/BACKEND-CONTRACT.md`
- `09-backend/DEVICE-AUTH.md`
- `09-backend/SELF-HOSTING.md`
- `03-runtime/UPDATE-ORCHESTRATOR.md`
- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/RELEASE-CADENCE.md`
- `12-distribution/REGISTRY-OPERATIONS.md`
- `10-security/COSIGN-TRUST.md`
## Graph links

[[BACKEND-CONTRACT]]  [[DEVICE-AUTH]]  [[OCI-NATIVE-MODEL]]  [[UPDATE-ORCHESTRATOR]]  [[COSIGN-TRUST]]
