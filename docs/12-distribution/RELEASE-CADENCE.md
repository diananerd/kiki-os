---
id: release-cadence
title: Release Cadence
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - artifact-catalog
  - meta-packages
  - oci-native-model
depended_on_by: []
last_updated: 2026-04-30
---
# Release Cadence

## Purpose

Document the expected release frequency per artifact class and the channel structure for stable / beta / nightly. Cadence sets expectations for users (when to expect updates), maintainers (when to ship), and CI (when to gate).

## Channels

```
stable        production; the default; thoroughly tested
beta          one-step-ahead; opt-in users help validate
nightly       latest; daily; for development and testing
edge          per-commit; for contributors; not for users
```

A device subscribes to a channel per artifact class. Defaults: stable for everything; users can opt in to beta on selected classes (e.g., apps).

## Cadence per class

```
class                 stable           beta             nightly
─────────────────────────────────────────────────────────────────
base / sysext         monthly          weekly           daily
apps                  weekly           daily            daily
components            weekly           daily            daily
models                quarterly+       monthly          on-demand
profiles              ad-hoc           ad-hoc           ad-hoc
skills                continuous       continuous       continuous
agents                ad-hoc           ad-hoc           ad-hoc
prompts pack          monthly          weekly           daily
```

These are *expected* cadences; security or critical fixes ship out-of-band.

## Security advisory channel

A separate "security" stream that any channel can pull from for advisories:

- CVE-class fixes shipped within hours where possible
- All channels (stable / beta / nightly) get security fixes simultaneously
- Users may auto-apply security updates regardless of their channel cadence (configurable; default on)

## Versioning rules

- Major bumps: rare; coordinated across artifacts
- Minor bumps: feature additions; compatible
- Patch bumps: fixes; compatible

The compatibility matrix between sysexts and base must hold: a base v1.x runs sysexts v1.y for any compatible y. Major bumps require everyone to update together.

## Per-meta-package cadence

A meta-package update aggregates the per-class cadences:

- desktop stable: monthly meta-package release
- desktop beta: weekly
- developer stable: monthly
- minimal: monthly

## Coordination across artifacts

Some changes require simultaneous updates across multiple artifacts (e.g., a Cap'n Proto schema major bump). The build system coordinates:

- Pre-release bundle in beta for a window
- Both old and new daemons for the deprecation period
- Stable rollout once satisfied

## Maintainer workflow

For a Kiki Foundation maintainer:

```
1. Implement change in main
2. CI runs full test suite + eval suite + reproducibility check
3. Tagged release in nightly
4. Promote to beta after N days of green
5. Promote to stable after M days in beta with no regressions
```

Specifics per-artifact in maintainer-guide.

## User-controlled overrides

Users can:

- Pin a specific artifact to a specific version
- Opt into beta for selected classes
- Defer non-security updates per class

The update orchestrator honors these.

## Communications

Each release has:

- A signed release note in Markdown attached as an OCI attestation
- A changelog with public-facing items
- A list of advisories addressed
- Compatibility notes

The Kiki client surfaces notes in Settings → Updates.

## Anti-patterns

- Continuous-deploying to stable
- Skipping beta on major changes
- Hidden cadence (users can't tell when to expect updates)
- Mixing security and feature updates without separation

## Acceptance criteria

- [ ] Cadence documented per class
- [ ] Security stream operates independently
- [ ] CI gates promotion through channels
- [ ] User overrides respected
- [ ] Release notes attached to each version

## References

- `12-distribution/ARTIFACT-CATALOG.md`
- `12-distribution/META-PACKAGES.md`
- `12-distribution/OCI-WORKFLOWS.md`
- `12-distribution/MAINTAINER-GUIDE.md`
- `03-runtime/UPDATE-ORCHESTRATOR.md`
## Graph links

[[ARTIFACT-CATALOG]]  [[META-PACKAGES]]  [[OCI-NATIVE-MODEL]]
