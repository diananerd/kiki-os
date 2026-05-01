---
id: sdk-bindings-python
title: Python SDK Bindings
type: SPEC
status: draft
version: 0.0.0
implements: [sdk-bindings-python]
depends_on:
  - sdk-codegen
  - sdk-rust
last_updated: 2026-04-30
---
# Python SDK Bindings

## Purpose

Specify the Python SDK: ergonomic asyncio API over the generated Cap'n Proto stubs. Python is a popular choice for tools, scripts, and ML-adjacent integrations.

## Package

`pip install kiki-sdk`

```python
from kiki import App, command, query, tool, view, Card, Text, Button

class State:
    counter: int = 0

@command
async def increment(state: State):
    state.counter += 1

@view("home")
def home(state):
    return Card(title="Counter", children=[
        Text(content=f"Count: {state.counter}"),
        Button(label="Increment", intent=increment.cmd()),
    ])

if __name__ == "__main__":
    App[State]() \
      .with_view(home) \
      .with_command(increment) \
      .run()
```

## Idioms

- `async def` for commands and queries
- Decorators replace Rust macros
- Dataclass-like state with type hints
- Views return tree of Block instances; the runtime serializes

## System clients

```python
async with App.connect() as app:
    hits = await app.memory.search("trip Lisbon")
    for hit in hits:
        print(hit.content)
```

## Errors

`KikiError` is a subclass of `Exception`; carries the structured `ErrorPayload`:

```python
try:
    await app.tools.dispatch(...)
except KikiError as e:
    if e.code == "policy.denied":
        print("need a grant")
```

## Packaging

Python apps still ship as OCI containers. The SDK provides helpers for packaging:

```
kiki-pkg build .   # uses the Python entrypoint
```

The container has a Python runtime; the manifest declares Python deps.

## Performance

Python is slower than Rust; for tools that need throughput, the agent dispatches the Rust-native or WASM tools first. Python shines for orchestration and integration glue.

## Type checking

`mypy --strict` clean. Stubs are generated alongside the runtime.

## Anti-patterns

- Heavy compute inside a Python tool (use Rust)
- Long-running Python services with many tools (consider Rust for footprint)

## Acceptance criteria

- [ ] PyPI package installs cleanly
- [ ] Hello-world example runs
- [ ] mypy --strict passes
- [ ] Errors map to KikiError with structured fields
- [ ] System clients functional

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/SDK-RUST.md`
- `06-sdk/SDK-CODEGEN.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
