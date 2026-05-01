---
id: hardware-abstraction
title: Hardware Abstraction
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - system-overview
  - principles
  - paradigm
depended_on_by:
  - hardware-manifest
  - iceoryx-dataplane
  - upstream-choice
last_updated: 2026-04-30
---
# Hardware Abstraction

## Problem

Kiki OS in v0 targets desktop-class hardware. Future versions may target other classes (mobile foldable, accelerated headless, sensor-class) without forking the OS. Forking per device class would multiply maintenance and fragment the ecosystem.

The architecture must:

- Run a single OS codebase across multiple hardware classes (now or future).
- Let apps written once run on every compatible hardware class.
- Make hardware-specific behavior configurable, not hard-coded.
- Scale resource use down: a sensor-class device cannot run a 12B-parameter model and should not try to load one.
- Make hardware presence discoverable: apps must not assume.

## Constraints

- Single OS image format (bootc OCI), parameterized per hardware class via build profile.
- Single set of system services; some optional per profile.
- Manifest-driven: hardware capabilities are declared, not detected ad-hoc.
- Multi-arch support: x86_64, arm64, riscv64.
- Must integrate with our chosen image build (mkosi).
- Must be opaque to the user (the appliance shape).

## Decision

Hardware adaptation has **three layered mechanisms**.

```
┌─────────────────────────────────────────────────────┐
│  3. RUNTIME ADAPTATION                              │
│     responds to dynamic state                       │
│     (display hot-plug, hinge, battery, etc.)        │
├─────────────────────────────────────────────────────┤
│  2. HARDWARE MANIFEST                               │
│     describes what's actually present               │
│     read at boot, queried by apps                   │
├─────────────────────────────────────────────────────┤
│  1. BUILD PROFILE                                   │
│     determines what's compiled into the image       │
│     selected at build time                          │
└─────────────────────────────────────────────────────┘
```

## Mechanism 1 — Build profile

A mkosi configuration that determines which subsystems are included in the OS image for a target hardware class.

Examples of subsystems controlled by build profile:

- Compositor (`cage`) — yes for display-class, no for sensor-class.
- Voice pipeline (`kiki-voiced`) — yes for devices with microphones.
- Cellular modem service — yes for devices with cellular.
- Multi-accelerator runtime — yes for devices with discrete GPU.
- Real-time kernel patches — yes for hard-real-time workloads.
- Servo embedded engine — yes for devices needing web blocks.

Build profiles are mkosi recipes in the build pipeline. Each inherits from a base recipe and adds or removes subsystems:

```
profile: desktop                      (v0 default)
  subsystems: [agentd, memoryd, policyd, inferenced, toolregistry,
               cage, agentui, kiki-voiced, servo-engine,
               podman, pipewire, NetworkManager]
  size_target: ~600 MB (without LLM)

profile: headless                     (future, v2)
  subsystems: [agentd, memoryd, policyd, inferenced, toolregistry,
               podman, NetworkManager]
  size_target: ~250 MB
  no display, no voice

profile: mobile-foldable              (future, multi-class)
  subsystems: [desktop subsystems + cellular, fold-aware compositor]

profile: sensor-minimal               (future, multi-class)
  subsystems: [agentd, memoryd-tiny]
  size_target: ~80 MB
  no display, no voice, no apps
```

In v0, only the `desktop` profile is implemented. Other profiles are documented as future work and reserved via RFC.

The build profile decides what is in the image. It does not determine app behavior at runtime. That comes from the manifest.

## Mechanism 2 — Hardware manifest

Every Kiki device has a hardware manifest at `/etc/kiki/hardware-manifest.toml`. It is signed at build time and read at boot.

The manifest describes the device's actual capabilities. It is the source of truth for what hardware is present:

```toml
[device]
profile = "desktop"
class = "developer-desktop"
serial = "..."

[soc]
arch = "x86_64"          # or "arm64" or "riscv64"
ram_mb = 32768
storage_gb = 512
gpu = "amd_rdna3"        # or "nvidia_ada", "intel_arc", "apple_m2", "none"

[display.primary]
present = true
type = "external_displayport"
resolution_x = 2560
resolution_y = 1440
refresh_hz = 144
size_inches = 27

[display.secondary]
present = false

[touch]
present = false

[audio]
microphones = 1
speakers = 1
echo_cancel = true

[camera]
count = 1
privacy_led = true
hardware_shutter = false

[connectivity]
wifi = "ax"
bluetooth = "5.3"
ethernet = true
cellular = false

[sensors]
imu = false
ambient_light = false
proximity = false

[battery]
present = false

[accelerators]
discrete_gpu = "amd_rdna3"
discrete_npu = false

[hardware_kill_switches]
microphone = false
camera = false
radios = false

[tpm]
present = true
version = "2.0"
```

The manifest is read at boot by:

- The compositor (knows which displays exist).
- The voice pipeline (knows microphone configuration).
- `agentd` (knows what perception channels exist).
- Apps via the SDK (`libagentos-system::hardware()`).
- The capability gate (knows which capabilities are realizable).

The manifest schema is defined in `02-platform/HARDWARE-MANIFEST.md`.

## Mechanism 3 — Runtime adaptation

Even within a single hardware manifest, runtime conditions vary:

- A second display is hot-plugged.
- A foldable opens or closes.
- An external camera connects via USB.
- The user enters a meeting; the agent should not interrupt.
- Battery drops below threshold.
- Cellular signal degrades; Wi-Fi is connected.

Runtime adaptation responds to these without requiring a manifest change.

Components that adapt at runtime:

- **Compositor (cage).** Hot-plug events reconfigure displays. Foldable state shifts UI between interior and exterior surfaces.
- **Voice pipeline.** Adjusts noise cancellation, speaker level, and wake word sensitivity to the acoustic environment.
- **Capability gate.** Some grants are context-sensitive (location auto-grants when relevant; prompts otherwise).
- **Inference router.** Battery-aware (`disable_cloud_below_battery_pct`), network-aware (falls back to local on disconnection).
- **The agent.** Receives manifest and runtime state in its context. It does not pretend to capabilities it lacks.

Runtime adaptation does not change the signed manifest. The manifest remains the static description; runtime is dynamic context layered on top.

## How apps adapt

Apps that need hardware adapt through patterns documented in the SDK:

### Pattern 1 — Detect, present what fits

```rust
let hw = kiki::hardware::manifest();

if hw.display.has_external() {
    register_full_ui_surfaces();
} else if hw.audio.has_speaker() {
    register_voice_only_tools();
} else {
    register_headless_tools();
}
```

### Pattern 2 — Voice-first, UI as enhancement

The app exposes voice-addressable tools. UI surfaces are additional. On headless devices the app is fully functional without UI.

### Pattern 3 — Hardware refusal

The app declares required hardware in its Profile:

```yaml
requires_hardware:
  camera: any
  display: any
```

The registry hides apps incompatible with the user's hardware. Install fails on incompatible hardware with a clear message.

### Pattern 4 — Graceful degradation

The app declares optional hardware. Features depending on it activate only when available; otherwise they are silently disabled.

## Hardware classes (canonical)

The following hardware classes are recognized. New classes are added via RFC.

| Class | Profile | Distinguishing features | Status |
|---|---|---|---|
| `desktop` | desktop | x86_64/arm64 desktop with display | v0 |
| `developer-desktop` | desktop | desktop with full I/O for development | v0 |
| `accelerated-desktop` | desktop | desktop with discrete GPU | v0.5 |
| `headless` | headless | no display; agent-only | v2 |
| `mobile-foldable` | mobile-foldable | cellular, foldable, cameras | future |
| `accelerated-headless` | accelerated-headless | GPU/NPU, headless, real-time | future |
| `sensor-minimal` | sensor-minimal | <512MB RAM, no display, no audio | future |

In v0, only `desktop`, `developer-desktop`, and `accelerated-desktop` are implemented. Each corresponds to the `desktop` build profile with manifest variations. The class name is what apps and capability checks reference, not specific product names.

## Cross-architecture support

Kiki OS targets:

- **x86_64** as primary in v0.
- **arm64 (aarch64)** as primary in v0; Apple Silicon and ARM SBCs.
- **riscv64** as a v1 target as CentOS Stream 10 bootc matures riscv support.

The build profile determines the architecture target. The same profile recipe builds for any architecture; the SOC field in the manifest distinguishes at runtime.

OCI manifest list publishes all architectures under one tag. bootc fetches the correct architecture automatically:

```
registry.kiki-os.dev/os/stable:1.0.0
  → linux/amd64 → manifest A
  → linux/arm64 → manifest B
  → linux/riscv64 → manifest C
```

Apps written in Rust compile to all three. SDK bindings (Python, TypeScript, Go, C) work across architectures.

## What is NOT assumed by the architecture

The architecture does not assume:

- A specific display panel technology.
- A specific touchscreen technology.
- A specific sensor count or arrangement.
- A specific accelerator vendor.
- A specific cellular generation.
- A specific connectivity method.

These are all expressed in the hardware manifest. Adding support for new hardware is adding fields to the manifest schema and implementing the HAL contract for the new hardware.

## Consequences

- A new hardware class is a build profile + manifest schema extension + HAL contract implementation. Not a new operating system.
- Apps query the manifest. Apps that hard-code hardware assumptions are flagged in registry review.
- The capability gate denies grants for unrealizable capabilities. An app requesting `device.camera.use` on a device with no camera is denied at install.
- Cross-class apps share the same SDK, the same APIs, the same protocol. Differences appear in their UI tier and their feature flags.
- Boot order, sandbox configuration, and process model are identical across classes. What changes is which subsystems are present.
- Future hardware classes are paths, not commitments. The architecture reserves the abstraction even if v0 ships only desktop.

## References

- `02-platform/HARDWARE-MANIFEST.md`
- `02-platform/HAL-CONTRACT.md`
- `02-platform/BOOT-CHAIN.md`
- `02-platform/UPSTREAM-CHOICE.md`
- `02-platform/IMAGE-COMPOSITION.md`
- `06-sdk/APP-CONTAINER-FORMAT.md`
- `07-ui/ADAPTATION-RULES.md`
