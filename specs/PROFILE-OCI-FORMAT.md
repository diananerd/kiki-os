---
id: profile-oci-format
title: Profile OCI Format
type: SPEC
status: draft
version: 0.0.0
implements: [profile-oci-format]
depends_on:
  - oci-native-model
  - cosign-trust
  - capability-taxonomy
depended_on_by:
  - publishing
last_updated: 2026-04-30
---
# Profile OCI Format

## Purpose

Specify the on-disk layout of a Kiki **device profile** packaged as an OCI artifact. A profile is a signed YAML/TOML document that bundles defaults, capabilities, recipes, and policies for a particular use case (kid mode, kiosk for a museum, secops engagement, accessibility-first).

## Why profiles

A profile is what happens when "set up these 30 things consistently" repeats often. Rather than a manual setup, a profile artifact ships with a curated bundle, signed by its publisher, applied atomically.

## OCI artifact shape

```
artifact descriptor
  config: application/vnd.kiki.profile.config.v1+toml
  layers:
    - application/vnd.kiki.profile.bundle.v1+tar
```

## Bundle layout

```
profile/
├── manifest.toml                     profile manifest
├── policy.toml                       capability defaults, restrictions
├── identity-template.md              optional pre-filled SOUL/USER
├── recipes/                          procedural recipes to install
├── apps.toml                         apps to install (by id@version)
├── components.toml                   components to install
├── theme.toml                        token overrides
├── settings.toml                     system settings to apply
├── locale.toml                       locale defaults
└── README.md
```

## Manifest

```toml
id = "kiki:profiles/kid-friendly"
version = "1.0.0"
title = "Kid-friendly"
description = "Restricted profile for child users."
authors = ["Kiki"]
license = "Apache-2.0"

[applies_to]
device_kinds = ["any"]
user_kind = "child"

[required_capabilities_minimum]
# anything this profile needs to function

[capabilities_locked]
# capabilities this profile pins (cannot be widened by user
# without admin override)
agent.memory.write.identity = "denied"
network.outbound.host = "allowlist"

[apps]
include = ["kiki:apps/kids-music", "kiki:apps/storytime"]
exclude = ["kiki:apps/email", "kiki:apps/finance"]

[bundled_with]
# other profiles that compose with this
"kiki:profiles/large-text" = "optional"
```

## Application

A profile is applied via:

```
kiki profile apply <id>@<version>
kiki profile apply <id>@<version> --user=<uid>
```

The flow:

1. Pull artifact; verify signature + Sigstore
2. Diff against current state; show changes to admin/user
3. Apply: install apps, install components, set policies, write identity template, set theme, set locale
4. Audit entry

Removing a profile reverses what it added; settings the user has changed since are preserved unless the user requests "full reset to profile".

## Layered profiles

Profiles can compose:

```
profile.base
  └── profile.kid_friendly
        └── profile.large_text
```

Conflicts resolve by most-restrictive wins (similar to adaptation rules).

## Capability locks

A profile can *lock* capabilities — meaning the user cannot widen them without admin override. Useful for kid mode, kiosk, secops.

A locked capability shows up in Settings as locked with a note pointing to the profile that set it.

## Identity templates

A profile can ship an identity template (SOUL.md / USER.md prefilled) for first-run. The user reviews and confirms before the template is committed; the consent flow runs.

## Profile signing

cosign-signed; Sigstore log entry required. Profiles are high-stakes (they reshape the system); signature verification is mandatory.

## Multi-tenant

Profiles can be applied per-user on a multi-user device (e.g., one user has kid_friendly, another has default).

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Signature invalid                | refuse to apply                |
| Required app not installable    | partial apply with warning;    |
|                                  | user decides                   |
| Conflict with active profile     | most-restrictive wins; show    |
|                                  | diff                            |
| Lock conflicts                   | reject if cannot reconcile     |

## Acceptance criteria

- [ ] Profile artifact pulls + verifies
- [ ] Apply is atomic (rollback on failure)
- [ ] Capability locks enforced
- [ ] Layered profiles compose
- [ ] Per-user profiles supported
- [ ] Audit log captures apply / remove

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/MEDIA-TYPES.md`
- `06-sdk/PUBLISHING.md`
- `04-memory/IDENTITY-FILES.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/COSIGN-TRUST.md`
