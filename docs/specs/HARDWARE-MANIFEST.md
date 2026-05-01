---
id: hardware-manifest
title: Hardware Manifest
type: SPEC
status: draft
version: 0.0.0
implements: [hardware-manifest]
depends_on:
  - hardware-abstraction
depended_on_by:
  - drm-display
  - hal-contract
  - hardware-kill-switches
  - inference-accel
last_updated: 2026-04-30
---
# Hardware Manifest

## Purpose

Specify the format and lifecycle of `/etc/kiki/hardware-manifest.toml`: a signed TOML file describing the device's hardware capabilities, read at boot by the runtime and queryable by apps via the SDK.

## Inputs

- The build process for OEM/factory devices, which writes the manifest based on attested hardware.
- The user's first-boot setup, which finalizes any user-determined fields.
- Optional re-detection on hardware changes (rare).

## Outputs

- A signed TOML file at `/etc/kiki/hardware-manifest.toml`.
- A typed in-memory representation accessible to system services and apps.

## Behavior

### Schema

```toml
manifest_version = 1

[device]
profile = "desktop"           # build profile this image was made for
class = "developer-desktop"   # canonical class name
serial = "<stable-uuid>"      # device unique identifier

[soc]
arch = "x86_64"               # x86_64 | aarch64 | riscv64
ram_mb = 32768
storage_gb = 512

[gpu]
present = true
vendor = "amd"                # amd | intel | nvidia | apple | none
family = "rdna3"              # vendor-specific family name
vram_mb = 16384
vulkan = "1.3"
metal = false                 # true on Apple Silicon

[display.primary]
present = true
type = "external_displayport"
resolution_x = 2560
resolution_y = 1440
refresh_hz = 144
size_inches = 27
hdpi = false

[display.secondary]
present = false

[touch]
present = false
multitouch_points = 0

[audio]
microphones = 1
speakers = 1
echo_cancel_supported = true

[camera]
count = 1
privacy_led = true
hardware_shutter = false

[connectivity]
wifi = "ax"                   # ax | n | none
bluetooth = "5.3"             # version | none
ethernet = true
cellular = false

[sensors]
imu = false
ambient_light = false
proximity = false

[battery]
present = false               # desktop typically false; laptop true

[accelerators]
discrete_npu = false

[hardware_kill_switches]
microphone = false
camera = false
radios = false

[tpm]
present = true
version = "2.0"
fIDO_supported = false

[hardware_attestation]
supported = true              # for provisioning attestation
mechanism = "tpm2-quote"

[signature]
key_id = "<oem-or-build-key-id>"
signature_b64 = "<base64-signature>"
```

### Field semantics

- `profile` and `class` together identify the hardware class; the runtime uses these to apply class-specific defaults.
- `arch` determines which OCI image variant runs.
- `gpu.vulkan` indicates Vulkan support level (used by the inference router for routing local LLM inference).
- `display.*` informs the compositor about display configuration.
- `audio` informs the voice pipeline.
- `tpm.present` determines whether TPM-sealed disk encryption can be used.
- `hardware_kill_switches` informs the agent which hardware controls exist.

### Signing

The manifest is signed at build/provisioning time. The signature key is one of:

- The OEM's manufacturing key (for factory-provisioned devices).
- The Kiki build key (for self-built or developer images).
- A user's enrollment key (after re-provisioning).

`agentd` verifies the signature at startup. An unsigned or invalidly-signed manifest causes `agentd` to refuse to start.

### Reading

The manifest is read at:

- `agentd` startup.
- After hardware change events (e.g., display hot-plug; the runtime adapts dynamically without rewriting the manifest).
- On `SIGUSR1` reload signal.

The parsed manifest is exposed to apps via:

```rust
let hw = kiki::hardware::manifest();
if hw.gpu.present && hw.gpu.vulkan_at_least("1.3") {
    use_local_inference();
}
```

### Updates

The manifest changes only on:

- Re-provisioning (factory reset and re-imaging).
- Adding/removing hardware that materially changes capabilities (rare).

The manifest is not modified during normal operation. Runtime adaptation responds to dynamic state without touching the manifest.

### Trust

The manifest is trusted because:

- It is signed by a key chain rooted in the OEM, build process, or user enrollment.
- It lives on read-only encrypted storage.
- Tampering would invalidate the signature.

A tampered manifest causes agentd to refuse to start with a clear error.

### Multi-instance hardware

When a class has multiple variants (e.g., the same SOC paired with different displays), the manifest captures the actual configuration. Runtime adaptation handles dynamic changes (hot-plug).

## Interfaces

### File

`/etc/kiki/hardware-manifest.toml` — read-only after provisioning.

### SDK

```rust
pub struct HardwareManifest {
    pub device: Device,
    pub soc: Soc,
    pub gpu: Gpu,
    pub display_primary: Option<Display>,
    pub display_secondary: Option<Display>,
    pub touch: Touch,
    pub audio: Audio,
    pub camera: Camera,
    pub connectivity: Connectivity,
    pub sensors: Sensors,
    pub battery: Battery,
    pub accelerators: Accelerators,
    pub hardware_kill_switches: KillSwitches,
    pub tpm: Tpm,
}

pub fn manifest() -> &'static HardwareManifest;
```

### CLI

```
agentctl hardware show       # human-readable manifest
agentctl hardware verify     # re-verify signature
```

## State

### Persistent

- The manifest file in `/etc/kiki/`.
- Cached parsed representation in agentd memory.

## Failure modes

| Failure | Response |
|---|---|
| Manifest missing | agentd refuses to start; recovery prompt |
| Manifest signature invalid | agentd refuses to start; alert |
| Manifest schema mismatch | agentd refuses to start; clear error |
| Field missing for required hardware | log; continue with conservative defaults |
| Hot-plug detected, manifest doesn't list device | use safe defaults; log; alert |

## Performance contracts

- Manifest read at startup: <10ms.
- Signature verification: <50ms.

## Acceptance criteria

- [ ] Manifest schema matches version 1 spec.
- [ ] Signature verification works at startup.
- [ ] Apps can query the manifest via the SDK.
- [ ] Hot-plug events do not modify the manifest; runtime adaptation handles them.
- [ ] An invalid manifest prevents agentd from starting.

## Open questions

- Whether to support unsigned manifests for development convenience (currently no; developer mode bypasses some checks but not this one).

## References

- `01-architecture/HARDWARE-ABSTRACTION.md`
- `02-platform/HAL-CONTRACT.md`
- `02-platform/BOOT-CHAIN.md`
- `09-backend/DEVICE-PROVISIONING.md`
## Graph links

[[HARDWARE-ABSTRACTION]]
