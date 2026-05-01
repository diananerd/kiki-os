---
id: render-api
title: Render API
type: SPEC
status: draft
version: 0.0.0
implements: [render-api]
depends_on:
  - sdk-overview
  - block-types
  - drm-display
  - inference-accel
depended_on_by:
  - sdk-rust
last_updated: 2026-04-30
---
# Render API

## Purpose

Specify the optional Render contract for apps that need to draw their own pixels: video players, 3D viewers, image editors, games. Most apps use Blocks; Render is for the small set of apps where a pixel buffer is the right abstraction.

## How it works

```
app process
    └── creates a wgpu device
        └── renders into a DMA-BUF
              │
              ▼
         agentui imports the DMA-BUF
              │
              ▼
         composites into the canvas as a `surface_buffer` block
```

DMA-BUF is the Linux interface for sharing GPU buffers across processes without copying. The app's rendered frames appear inside agentui's scene graph at the size and position the agent decides.

## Why DMA-BUF, not direct compositing

agentui owns the compositor surface. Apps don't get their own Wayland surface (the kiosk compositor refuses). DMA-BUF lets them produce frames that agentui imports.

## When to use Render

- Video playback
- 3D / interactive graphics
- Image / photo editor with pan/zoom and pixel-level interactions
- Games

When *not* to use:

- Anything that fits in native blocks (most apps)
- Web content (use a web block)
- Static media (use Image block)

## API

```rust
struct RenderSurface {
    fn new(size: Size, format: Format) -> Result<Self>;
    fn frame(&mut self) -> RenderFrame;
    fn present(&mut self, frame: RenderFrame);
    fn resize(&mut self, size: Size);
}
```

The app draws into the frame using wgpu (or any GPU API on top); `present` shares the buffer; agentui composites.

## Capability scoping

`render.surface` — required to allocate a render surface.

The buffer cannot escape the app's namespace; agentui imports a read-only fence-synchronized DMA-BUF.

## Performance

- Buffer allocation: <10ms
- Per-frame submit: <2ms overhead
- Compositing in agentui: same path as native blocks

The app drives its frame rate; agentui samples at its own rate (60 FPS by default).

## Multi-output

A render surface targets one logical block; if the block appears on multiple outputs, agentui upscales / downscales without per-output rendering by the app.

## HDR

HDR is off in v0; Render surfaces are SDR. HDR may come later via a capability-gated extension.

## Audio

Render is video-only. For audio, apps use the standard audio path (PipeWire via the audio.play capability), not Render.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| GPU device lost                  | recreate; replay last frame    |
| Buffer allocation fails          | placeholder block; warn        |
| Format unsupported by output     | software fallback              |
| Buffer larger than allowed       | refuse; configurable via       |
|                                  | manifest                        |

## Acceptance criteria

- [ ] DMA-BUF buffers shared into agentui with zero copies
- [ ] Capability gating
- [ ] Resize works without re-creating
- [ ] Block composition with native blocks around
- [ ] Frame rate independent of agentui's rate

## References

- `06-sdk/SDK-OVERVIEW.md`
- `06-sdk/KERNEL-FRAMEWORK.md`
- `07-ui/BLOCK-TYPES.md`
- `02-platform/DRM-DISPLAY.md`
- `02-platform/INFERENCE-ACCEL.md`
## Graph links

[[SDK-OVERVIEW]]  [[BLOCK-TYPES]]  [[DRM-DISPLAY]]  [[INFERENCE-ACCEL]]
