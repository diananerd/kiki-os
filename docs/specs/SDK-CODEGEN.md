---
id: sdk-codegen
title: SDK Codegen
type: SPEC
status: draft
version: 0.0.0
implements: [sdk-codegen]
depends_on:
  - sdk-rust
  - capnp-schemas
depended_on_by:
  - sdk-bindings-c
  - sdk-bindings-go
  - sdk-bindings-python
  - sdk-bindings-typescript
last_updated: 2026-04-30
---
# SDK Codegen

## Purpose

Specify how SDK bindings are generated from the Rust core. The Rust SDK is the canonical source of truth; bindings for Python, TypeScript, C, Go are generated rather than hand-written, so they stay in sync.

## Strategy

```
canonical Rust API
        │
        ▼
  capnp schemas (auto-derived from #[command], #[query], #[tool])
        │
        ▼
  language-specific code generators (capnp-python, capnp-ts, capnp-c, capnp-go)
        │
        ▼
  language-specific runtime helpers (per-binding crate)
        │
        ▼
  ergonomic per-language SDK
```

## Pipeline

1. Build the Rust SDK; macros emit Cap'n Proto schemas.
2. Run the language code generator over the schemas.
3. Wrap the generated stubs with per-language ergonomic helpers (auth context, error mapping, view DSL where applicable).

## What's generated

- Wire-level RPC stubs for all SDK clients (MemoryClient, InferenceClient, ...)
- Type definitions for all schemas
- Error mapping (ErrorPayload → idiomatic exceptions / errors)
- The kernel-side commands/tools schema as data classes

## What's NOT generated

- The view DSL (each language has its own UI idioms; we hand-write thin wrappers per language)
- Lifecycle hooks (idiomatic per language)
- Macros / decorators (per-language)

## Versioning

Generated bindings track the Rust SDK's version. Patch bumps are auto; minor and major involve human review of the generated diff (especially for breaking changes).

## CI

The CI pipeline:

- Builds Rust SDK
- Generates schemas
- Generates each binding
- Runs binding-specific tests
- Compares schema diffs against the prior release

A schema break that's not declared a major bump fails the build.

## Distribution per language

Each binding ships through its language's package manager:

- Python: PyPI (`kiki-sdk`)
- TypeScript: npm (`@kiki/sdk`)
- C: tarball + pkg-config
- Go: Go modules

## Cap'n Proto language support

We use existing Cap'n Proto bindings:

- Python: `pycapnp` or `capnp-python`
- TypeScript: `capnp-ts`
- C: the official `capnpc-c` family
- Go: `capnproto.org/go/capnp/v3`

## Hand-written wrapper

Each binding has a thin runtime crate / package that:

- Provides the connection setup (Unix socket, auth)
- Maps ErrorPayload to language-idiomatic exceptions
- Adds typed convenience constructors
- Provides per-language testing helpers

## Anti-patterns

- Hand-writing one binding by hand and generating others (drift)
- Letting bindings drift from the Rust SDK's behavior (CI prevents)
- Adding Python-only or TypeScript-only fields (must be in the Rust SDK first)

## Acceptance criteria

- [ ] Schema generation deterministic
- [ ] Each binding builds + tests pass
- [ ] CI catches schema drift
- [ ] Versioning aligns with Rust SDK

## References

- `06-sdk/SDK-RUST.md`
- `06-sdk/SDK-BINDINGS-PYTHON.md`
- `06-sdk/SDK-BINDINGS-TYPESCRIPT.md`
- `06-sdk/SDK-BINDINGS-C.md`
- `06-sdk/SDK-BINDINGS-GO.md`
- `05-protocol/CAPNP-SCHEMAS.md`
## Graph links

[[SDK-RUST]]  [[CAPNP-SCHEMAS]]
