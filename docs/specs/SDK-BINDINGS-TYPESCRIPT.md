---
id: sdk-bindings-typescript
title: TypeScript SDK Bindings
type: SPEC
status: draft
version: 0.0.0
implements: [sdk-bindings-typescript]
depends_on:
  - sdk-codegen
  - sdk-rust
last_updated: 2026-04-30
---
# TypeScript SDK Bindings

## Purpose

Specify the TypeScript SDK: ergonomic Promise-based API over the generated Cap'n Proto stubs. Useful for integration tools, web-block content, and remote clients (the Kiki remote app is TS).

## Package

`npm install @kiki/sdk`

```ts
import { App, command, view, Card, Text, Button } from "@kiki/sdk";

interface State { counter: number; }
const initialState: State = { counter: 0 };

const increment = command<State>(async (state) => {
  state.counter += 1;
});

const home = view<State>("home", (state) => (
  <Card title="Counter">
    <Text content={`Count: ${state.counter}`} />
    <Button label="Increment" intent={increment.cmd()} />
  </Card>
));

await App.create<State>(initialState)
  .withView(home)
  .withCommand(increment)
  .run();
```

JSX-like view syntax via TS templates; the runtime handles diffing.

## System clients

```ts
const memory = await app.memory();
const hits = await memory.search({ text: "trip Lisbon" });
```

## Errors

`KikiError extends Error` with `category`, `code`, `message`, `detail`:

```ts
try {
  await app.tools.dispatch(...);
} catch (e) {
  if (e instanceof KikiError && e.code === "policy.denied") {
    // ...
  }
}
```

## Runtimes

- **Node.js**: server-side tools, headless services, remote clients
- **Deno**: tools that benefit from Deno's permission model
- **Browser** (limited): only via the remote client when running in a paired-remote context

We do not run TS apps directly on-device GUI; UI in the device is Slint via the agentui binary. TS apps targeting a Kiki device produce containers (OCI) just like Rust apps.

## Bundling

esbuild or rollup; produces a single bundle. The package supports tree-shaking so unused features (Render contract) drop out.

## Type checking

Strict TypeScript; full type definitions generated from schemas.

## Async iterators

Streaming methods are async iterators:

```ts
for await (const hit of memory.searchStream(query)) {
  console.log(hit);
}
```

## Anti-patterns

- Bundling massive frameworks (React + everything) into a tool
- Browser-only paths in tools meant for headless services

## Acceptance criteria

- [ ] npm package installs and types
- [ ] Hello-world tool runs
- [ ] tsc --strict passes
- [ ] Streaming via async iterators
- [ ] Errors typed

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/SDK-RUST.md`
- `06-sdk/SDK-CODEGEN.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `13-remotes/REMOTE-CLIENT-PLATFORMS.md`
