---
id: browser-engine
title: Browser Engine
type: SPEC
status: draft
version: 0.0.0
implements: [browser-engine]
depends_on:
  - agentui
  - block-types
  - capability-gate
  - sandbox
depended_on_by:
  - block-types
last_updated: 2026-04-30
---
# Browser Engine

## Purpose

Specify how Servo is embedded in agentui to render web blocks. The web engine is for blocks whose content is naturally HTML/CSS — articles, documentation, constrained third-party widgets — not for general web browsing. Kiki is not a browser.

## Why Servo

- Pure Rust; integrates as a library, not a separate process
- Embeddable; renders into a wgpu texture
- Modern: incremental layout, GPU compositing
- Not Chromium-sized; tractable to audit
- Constrainable: we can disable JS, popups, third-party storage

## Topology

```
agentui (Slint scene)
    └── web block
          └── ServoEngine (per block)
                ├── Network (mediated by agentd)
                ├── Storage (sandboxed per block)
                ├── Media (none by default)
                ├── JS engine (off unless explicitly granted)
                └── Renderer (wgpu, shared with Slint)
```

Each web block is a separate Servo instance with its own constrained context.

## Constraints

### Network

The web block declares its host(s); the capability gate enforces. Servo's networking goes through agentd's outbound HTTP path, which:

- Validates the host against the capability
- Enforces TLS (no plaintext)
- Logs the request

A web block cannot reach hosts outside its declared list.

### JavaScript

Off by default. A web block may declare `js_required = true` in its manifest; the user (or the app's installer) approves the elevated capability `web.js.<host>`. JavaScript blocks are limited:

- No service workers
- No web sockets unless explicitly granted
- No background tabs
- No notification API
- No web USB / Bluetooth

### Storage

Per-block IndexedDB and localStorage; cleared on canvas dismiss unless the block declares `persist_storage = true`.

### Cookies

None by default. With explicit grant, first-party cookies allowed; third-party cookies always blocked.

### Media

`<video>` and `<audio>` require a separate capability (`audio.play`). Default off. Autoplay disabled.

### Popups / new windows

Blocked. A web block lives in its block; it cannot escape.

## Embedding

```rust
struct WebBlock {
    fn new(url: Url, profile: WebProfile) -> Result<Self>;
    fn render(&mut self, target: &wgpu::Texture, size: Size);
    fn dispatch(&mut self, evt: WebEvent);
    fn shutdown(self);
}

struct WebProfile {
    js_enabled: bool,
    storage_persist: bool,
    cookies_enabled: bool,
    network_hosts: Vec<Host>,
    timeout_ms: u32,
}
```

agentui constructs a WebProfile from the web block's declared capabilities.

## Performance

- First paint: <800ms p99
- Memory per block: <128MB
- Multiple web blocks per canvas: feasible up to ~4 small or 1 medium

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Servo crashes                    | replace block with placeholder;|
|                                  | "reload" affordance            |
| Network capability denied        | block error; do not load       |
| JS error                         | block continues; error logged  |
| Memory exceeded                  | unload block; warn user        |

## Anti-patterns

- Embedding a general browser into a web block
- Using web blocks as a substitute for native blocks for trust-sensitive UI
- Long-running web pages with persistent JS — those should be apps with native surfaces

## Acceptance criteria

- [ ] Web blocks render via Servo into wgpu
- [ ] Network is mediated by agentd
- [ ] JS off by default; opt-in only
- [ ] Storage scoped per block
- [ ] Popups blocked
- [ ] Crash isolated to the block

## References

- `07-ui/AGENTUI.md`
- `07-ui/BLOCK-TYPES.md`
- `02-platform/SANDBOX.md`
- `03-runtime/CAPABILITY-GATE.md`
