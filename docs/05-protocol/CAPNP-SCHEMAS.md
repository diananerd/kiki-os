---
id: capnp-schemas
title: Cap'n Proto Schema Management
type: SPEC
status: draft
version: 0.0.0
implements: [capnp-schemas]
depends_on:
  - capnp-rpc
  - update-orchestrator
depended_on_by:
  - capnp-rpc
  - kernel-framework
  - sdk-codegen
last_updated: 2026-04-30
---
# Cap'n Proto Schema Management

## Purpose

Specify how Cap'n Proto schemas are organized, versioned,
distributed, and evolved across daemon and tool boundaries.
The schema is the contract; this document is the rule for
changing it without breaking anything in the field.

## Inputs

- The set of `.capnp` files that define daemon and tool
  interfaces
- The schema-id assignments (Cap'n Proto's `@<u64>` tags)
- The version metadata in each file
- The deprecation log

## Outputs

- A schema bundle shipped with the OS image
- Generated Rust bindings for each daemon and the tool SDK
- A schema registry queryable at runtime

## Behavior

### File layout

Schemas live at `/usr/share/kiki/capnp/`:

```
common.capnp                 shared scalar types
agentd.capnp                 agentd bootstrap and session
policyd.capnp                capability gate + grants
inferenced.capnp             inference engine
memoryd.capnp                memory layers
toolregistry.capnp           tool registry
tool.capnp                   the per-tool interface trait
audit.capnp                  audit reader/writer
mailbox.capnp                mailbox messages
focus.capnp                  focusbus payloads (mirrored to DBus)
errors.capnp                 ErrorPayload + reason codes
```

Apps that ship tools embed their tool schema under
`/var/lib/kiki/apps/<app>/capnp/` and register it with the
tool registry at install time.

### Schema id assignments

Every interface, struct, and enum has a permanent 64-bit id
(`@0xabc...`). Once assigned, never changed. The id, not the
name, is the wire identity.

ids are assigned via the standard `capnp id` tool and
recorded in a registry file:

```
/usr/share/kiki/capnp/IDS.toml

[ids]
"common.Time" = "0xa1b2c3d4..."
"agentd.Session" = "0x..."
```

The registry is consulted at build time; CI fails if a
declared name has an id that conflicts with a previously
assigned one or if a previously assigned id is missing from
the current schema.

### Version metadata

Each `.capnp` file carries a doc-comment header:

```capnp
# kiki-schema: agentd.capnp
# version: 1.3.0
# stability: stable
# owner: agentd
```

The triplet `(major.minor.patch)` follows semver:

- **patch**: doc-only or non-wire changes
- **minor**: adding new fields, methods, interfaces (forward
  compatible)
- **major**: removing or renumbering fields or methods, or
  changing field types (incompatible)

Daemons advertise their schema version in the bootstrap
handshake; clients refuse to talk to a daemon whose schema
major version is newer than what the client knows.

### Evolution rules

- **Adding a field to a struct**: append at the next free
  ordinal. Old clients ignore it; new clients see the default
  for old peers. No version bump beyond minor.
- **Adding a method to an interface**: append; old clients
  do not call it. Minor bump.
- **Renaming a field or method**: change the source name only.
  Wire id is unchanged. No version bump.
- **Removing a field or method**: never. Mark `# deprecated`
  and stop using it. Removal is a major version bump only
  during a coordinated cleanup release with a deprecation
  window of ≥ one minor release.
- **Changing a field type**: never; add a new field with the
  new type, deprecate the old.
- **Changing the layout** (group, union variants): only via
  major bump.

CI enforces these by comparing each PR's schema against the
last released one and reporting violations.

### Deprecation

A deprecated field or method is annotated:

```capnp
struct Grant {
  actor @0 :ActorRef;
  user @1 :UserRef;
  capability @2 :Text;          # deprecated since 1.4.0; use
                                # capabilityV2
  capabilityV2 @3 :Capability;
}
```

Daemons may emit a structured warning when a client uses a
deprecated field or method. Warnings are rate-limited. The
audit log records first use per session.

### Distribution

Schemas are part of the bootc base image. Tools that bring
their own schemas declare them in their app manifest; the
tool registry validates the schema at install time:

- Parses the schema
- Checks ids do not collide with reserved (system) ranges
- Generates Rust bindings as part of the install pipeline (or
  uses precompiled bindings shipped with the app)

Apps reuse `tool.capnp` by importing it, never by redefining
it. This keeps the tool dispatch interface stable for
agentd's planner.

### Reserved id ranges

To prevent collisions:

```
0x0000_0000_0000_0000 — 0x0fff_ffff_ffff_ffff   reserved
0x1000_... — 0x4fff_...                          system schemas
0x5000_... — 0x8fff_...                          first-party apps
0x9000_... — 0xffff_...                          third-party tools
```

`capnp id` produces random ids that fall outside the system
range with overwhelming probability; the install-time check
is belt-and-braces.

### Generated code

The OS image ships compiled Rust bindings for system schemas
under each daemon's crate. Apps that ship Rust tools either:

- Bring precompiled bindings, or
- Declare schemas in their manifest; the tool registry runs
  `capnpc-rust` at install time inside a sandboxed builder
  task

Generated code is reproducible — same schema in produces same
bindings out — verified by hash in the audit log.

### Runtime schema registry

agentd hosts a small schema registry callable via Cap'n Proto:

```capnp
interface SchemaRegistry {
  list @0 () -> (entries :List(SchemaEntry));
  get @1 (name :Text) -> (schema :Schema);
}
```

Tools and remote clients can query at runtime to pick the
right schema version for a daemon. This is rare in practice
— bootstraps already advertise the version — but useful for
debugging and for the `kiki-schemas` CLI:

```
kiki-schemas list                  # show all loaded schemas
kiki-schemas show agentd           # dump agentd schema
kiki-schemas diff agentd 1.2 1.3   # version diff
kiki-schemas check                 # validate registry
```

### Cross-language support

System code is Rust. Tool authors may write tools in other
languages where supported (WASM via Wassette is the primary
non-Rust path). Cap'n Proto has bindings for C++, Go, JS, and
others; the SDK wraps them so a tool author writes against
the same `tool.capnp` regardless of language.

WASM tools see Cap'n Proto messages as flat byte buffers
exchanged through the WASI ABI; the Wassette runtime in
`toolregistry` does the unwrap.

### Compatibility testing

The release pipeline runs a wire-compatibility matrix:

- Old daemon × new client (forward compat: should work for
  same major)
- New daemon × old client (backward compat: new fields ignored)
- Old × old (control)

Failures block the release.

## Interfaces

### CLI

```
kiki-schemas list
kiki-schemas show <name>
kiki-schemas diff <name> <old-ver> <new-ver>
kiki-schemas check
kiki-schemas register <path>            # install-time use
```

### Programmatic

```rust
struct SchemaRegistry {
    fn list(&self) -> Vec<SchemaEntry>;
    fn get(&self, name: &str) -> Option<Schema>;
    fn validate(&self, schema: &Schema) -> Result<()>;
    fn record(&self, schema: Schema) -> Result<()>;
}
```

## State

### Persistent

- `/usr/share/kiki/capnp/` (read-only system schemas)
- `/var/lib/kiki/capnp/registry.db` (installed app schemas)
- `/usr/share/kiki/capnp/IDS.toml`

### In-memory

- The agentd schema registry cache

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Id collision at install          | reject the install; report     |
| Schema parse fails               | reject the install             |
| Major version mismatch at        | refuse RPC; surface error to   |
| handshake                        | user                           |
| Generated code mismatch          | rebuild; if persistent, fail   |
| (hash differs)                   | the build                      |
| Removed-field reuse              | CI lint blocks the PR          |

## Performance contracts

- Schema parse on install: <500ms typical
- Registry lookup: <100µs (cached)
- Bootstrap version negotiation: <1ms

## Acceptance criteria

- [ ] All system schemas loaded at boot
- [ ] Registry populated from `/usr/share/kiki/capnp/` plus
      installed apps
- [ ] CI checks for id collisions, removed fields, and major
      bump justification
- [ ] Cross-version compatibility matrix passes
- [ ] `kiki-schemas` CLI works against the live registry

## Open questions

None.

## References

- `05-protocol/CAPNP-RPC.md`
- `03-runtime/TOOLREGISTRY.md`
- `03-runtime/UPDATE-ORCHESTRATOR.md`
- `03-runtime/TOOL-DISPATCH.md`
