---
id: toolregistry
title: Tool Registry Daemon
type: SPEC
status: draft
version: 0.0.0
implements: [toolregistry]
depends_on:
  - agentd-daemon
  - tool-dispatch
  - capnp-rpc
depended_on_by: []
last_updated: 2026-04-29
---
# Tool Registry Daemon

## Purpose

Specify the `toolregistry` daemon: discovery and lifecycle of MCP tools, WASM tools, container tools, and shell tools, with cost-tier and side-effect metadata, lazy schema injection.

## Behavior

### Tool kinds

Three primary kinds:

```rust
enum ToolKind {
    ContainerEphemeral { image: OciRef, sandbox_preset: SandboxPreset },
    ContainerService { image: OciRef, socket: PathBuf, mcp_protocol: McpVersion },
    Wasm { wasm_path: PathBuf, component_interface: WitInterface },
}
```

`ContainerEphemeral` is per-call: each tool call spawns a transient quadlet container.
`ContainerService` is persistent: a long-running container with a Cap'n Proto socket; calls forwarded via MCP-compatible RPC.
`Wasm` is loaded into wasmtime per call (or pooled).

Plus a fourth kind for built-in tools:

```rust
ToolKind::Builtin { handler: Box<dyn ToolHandler> }
```

Built-in tools are compiled into agentd; used for tools that touch system state directly (e.g., `tools.search`).

### Discovery

Sources of tools:

1. **Installed apps**: each app's Profile declares tools. On install, `agentctl install` registers them.
2. **WASM tools**: pulled as OCI artifacts, registered.
3. **Built-ins**: registered at startup.

Tools live under URIs `kiki:<ns>/<name>/<tool>`.

### Lazy schema injection

Default catalog exposed to the agent: ~8–10 core tools.

```
tools.search(query)              # search the full catalog
tools.invoke(uri, args)          # invoke a known tool
agent.canvas.emit_block(spec)    # emit canvas block
agent.memory.recall(query)       # retrieval
agent.memory.note(content)       # episodic write
agent.workspace.spawn(profile)   # workspace creation
agent.confirm(spec)              # ask user via Confirm widget
agent.subagent.fork(...)         # fork subagent
```

When the agent needs a specific tool, it calls `tools.search` to find it, then `tools.invoke` to use it. The full schema is loaded on demand.

This prevents context bloat from large tool catalogs.

### Cost and side-effect metadata

Every tool descriptor includes:

```rust
struct ToolMetadata {
    cost_class: CostClass,         // Free | Cheap | Expensive | $$$
    expected_latency: LatencyClass, // Fast | Normal | Slow
    side_effects: SideEffectFlags,
    risk_class: RiskClass,
}

bitflags! {
    struct SideEffectFlags: u8 {
        const READ_ONLY     = 0b00001;
        const DESTRUCTIVE   = 0b00010;
        const REVERSIBLE    = 0b00100;
        const EXTERNAL      = 0b01000;
        const IRREVERSIBLE  = 0b10000;
    }
}
```

These metadata are TYPED FLAGS. The harness reads them WITHOUT consulting the LLM. `read_only` tools auto-approve; `destructive + reversible` tools prompt; `destructive + irreversible` tools require human approval.

### Wassette compatibility for WASM

WASM tools follow the Wassette format (Microsoft, Aug 2025): WASI 0.2 components with deny-by-default capabilities, distributed as OCI artifacts.

```
1. agentctl install kiki:acme/csv-converter (OCI artifact, mediaType vnd.kiki.tool.wasm.v1+oci)
2. cosign verify
3. Extract .wasm + manifest to /var/lib/kiki/tools/wasm/<ns>/<name>/<v>/
4. Register in catalog
5. On invoke: wasmtime.instantiate(wasm_path); call component_interface; capture result
```

WASM tools have predictable resource usage and no spawn overhead beyond instantiation (~few ms).

### MCP servers

Apps that expose tools via MCP register them through the Cap'n Proto adapter; `toolregistry` translates between Kiki's Cap'n Proto and the app's MCP protocol. This treats MCP as a wire format, not a trust boundary (per `10-security/ANTI-PATTERNS.md`).

### Lifecycle of a service tool

```
register at install
   → declare in Profile
on first invoke
   → start container via systemd quadlet (if not running)
   → wait for sd_notify READY
   → forward Cap'n Proto request
on idle timeout
   → stop container per Profile policy
on uninstall
   → unregister; stop container; clean up
```

### Lifecycle of an ephemeral tool

```
on invoke
   → systemd-run --transient --scope --collect (quadlet template)
   → pass args via stdin
   → read result from stdout
   → container exits; systemd cleans up
```

### Lifecycle of a WASM tool

```
on invoke
   → wasmtime instantiate (cached if pooled)
   → call component export
   → return result
   → instance dropped (or returned to pool)
```

### Tool removal

When an app is uninstalled:

- All tools from that app are unregistered.
- Active service containers stopped.
- WASM artifacts garbage-collected.
- Audit log: tools removed.

## Interfaces

### Programmatic

```rust
struct Toolregistry {
    fn register(&mut self, descriptor: ToolDescriptor) -> Result<()>;
    fn unregister(&mut self, uri: &ToolURI) -> Result<()>;
    fn lookup(&self, uri: &ToolURI) -> Option<&ToolDescriptor>;
    fn search(&self, query: &str, top_k: usize) -> Vec<&ToolDescriptor>;
    async fn invoke(&self, uri: &ToolURI, args: serde_json::Value) -> Result<ToolResult>;
}
```

### CLI

```
agentctl tools list                   # all registered
agentctl tools show <uri>
agentctl tools search <query>
agentctl tools test <uri> <json>
agentctl tools install <oci-uri>      # install a WASM tool
```

## State

### Persistent

- Tool catalog in /var/lib/kiki/system.sqlite.
- WASM artifacts in /var/lib/kiki/tools/wasm/.
- Service tool quadlets in /etc/containers/systemd/.

### In-memory

- Catalog cache.
- WASM instance pool.
- Service connection pool.

## Failure modes

| Failure | Response |
|---|---|
| Tool URI conflict on register | reject second registration |
| Schema invalid | reject; clear error |
| WASM artifact missing | mark unavailable; alert |
| Service tool fails to start | retry; mark unavailable after threshold |
| MCP protocol mismatch | error; log |

## Performance contracts

- Catalog lookup: <10µs.
- Search query (full text): <50ms.
- WASM instantiation: ~few ms (pooled); ~100ms cold.
- Container service tool dispatch (warm): <50ms.

## Acceptance criteria

- [ ] Three tool kinds + built-ins all dispatchable.
- [ ] Lazy schema injection: agent sees ~8–10 core tools by default.
- [ ] Wassette-compatible WASM tools work.
- [ ] MCP servers wired via Cap'n Proto adapter.
- [ ] Cost and side-effect metadata used by harness without LLM consultation.
- [ ] Tool URI uniqueness enforced.

## References

- `03-runtime/TOOL-DISPATCH.md`
- `03-runtime/AGENTD-DAEMON.md`
- `02-platform/CONTAINER-RUNTIME.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `05-protocol/CAPNP-RPC.md`
- `12-distribution/MEDIA-TYPES.md`
