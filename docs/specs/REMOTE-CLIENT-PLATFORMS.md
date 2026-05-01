---
id: remote-client-platforms
title: Remote Client Platforms
type: SPEC
status: draft
version: 0.0.0
implements: [remote-client-platforms]
depends_on:
  - remote-architecture
  - remote-protocol
  - device-pairing
depended_on_by: []
last_updated: 2026-04-30
---
# Remote Client Platforms

## Purpose

Specify the per-platform shape of the remote client: iOS, Android, macOS, Windows, Linux, Web. Same underlying protocol; platform-specific shells. The shared core is the Cap'n Proto + WebRTC stack written in Rust; platform-specific UI sits on top.

## Shared core

```
kiki-remote-core (Rust)
├── Cap'n Proto client (capnp-rpc-rs)
├── mTLS (rustls + aws-lc-rs)
├── WebRTC (webrtc-rs)
├── secure storage abstraction
├── pairing flow
├── reconnect / failover
```

Compiled to native libraries for each platform; UI shells link against it.

## Platform specifics

### iOS

```
- Native UI: SwiftUI
- kiki-remote-core via XCFramework
- Secure storage: Keychain
- Push: APNs (opt-in for proactive notifications)
- WebRTC: AVAudioEngine integration
- App Store distribution
```

iOS-specific:

- Background modes: VoIP for voice sessions
- UI follows iOS HIG; design tokens themed for iOS
- Accessibility via UIKit / SwiftUI's standard support

### Android

```
- Native UI: Jetpack Compose
- kiki-remote-core via JNI / cargo-ndk
- Secure storage: Android Keystore
- Push: FCM (opt-in)
- WebRTC: WebRTC Android library
- Distribution: Google Play + APK
```

Android-specific:

- Foreground service for active voice sessions
- Material Design theming with Kiki tokens
- Accessibility via Android's standard tree

### macOS

```
- Native UI: SwiftUI / AppKit hybrid
- kiki-remote-core via XCFramework
- Secure storage: Keychain
- Distribution: notarized DMG, optional App Store
```

### Windows

```
- Native UI: WinUI 3 (preferred) or Tauri-equivalent
- kiki-remote-core via Rust crate + bindings
- Secure storage: Credential Manager / DPAPI
- Distribution: MSIX, Microsoft Store
```

### Linux

```
- Native UI: GTK4 or Slint (consistent with Kiki devices)
- kiki-remote-core natively
- Secure storage: GNOME Keyring / KWallet via Secret Service
- Distribution: Flatpak (preferred), AppImage, native package
```

### Web

```
- UI: TypeScript + a small framework (we use the official Kiki TypeScript SDK)
- Cap'n Proto over WebSocket (server bridge required)
- Storage: IndexedDB with WebCrypto-derived encryption
- WebRTC: browser-native
```

Web is the most constrained: no mDNS, no fancy permissions; relies on WAN rendezvous + a backend WebSocket bridge for Cap'n Proto.

## Capability scope per platform

| Capability                | iOS | Android | macOS | Win | Linux | Web |
|---------------------------|-----|---------|-------|-----|-------|-----|
| LAN mDNS discovery        |  ✓  |    ✓    |   ✓   |  ✓  |   ✓   |  ✗  |
| Backend rendezvous        |  ✓  |    ✓    |   ✓   |  ✓  |   ✓   |  ✓  |
| WebRTC voice              |  ✓  |    ✓    |   ✓   |  ✓  |   ✓   |  ✓  |
| Background sessions       |  ✓* |    ✓    |   ✓   |  ✓  |   ✓   |  ✗  |
| Push notifications        |  ✓  |    ✓    |   ✓   |  ✓  |   ✓   |  ✗  |
| Secure-enclave keys       |  ✓  |    ✓*   |   ✓   |  ✓* |   ✓*  |  ✗  |

\* = depends on hardware. Web's lack of secure-enclave means web pairings have lower trust by default.

## Pairing UX per platform

- iOS / Android / macOS / Windows / Linux: native QR scanner; in-app code entry
- Web: code entry only (no camera reliable in browsers)

## Secure storage

Each platform uses its native API. The kiki-remote-core abstracts:

```rust
trait SecureStorage {
    fn put(&self, key: &str, value: &[u8]) -> Result<()>;
    fn get(&self, key: &str) -> Result<Option<Vec<u8>>>;
    fn delete(&self, key: &str) -> Result<()>;
}
```

Implementations: KeychainStorage (iOS/macOS), KeystoreStorage (Android), CredManagerStorage (Windows), SecretServiceStorage (Linux), IndexedDB+WebCrypto (Web).

## Push notifications

For proactive messages from the device:

- Device sends to backend; backend forwards via APNs/FCM
- Push payloads are E2E encrypted; the push provider sees ciphertext only
- The remote decrypts on receipt; renders the prompt

Web has no equivalent; web users see notifications only when the app is open.

## Distribution

- iOS: App Store (Apple's review)
- Android: Google Play + sideloadable APK
- macOS: notarized DMG
- Windows: MSIX
- Linux: Flatpak primary; native packages secondary
- Web: served from `app.kiki.example` (or any trusted domain)

Each release of the remote core is built once (Rust) and cross-compiled per target; UI is platform-native.

## Versioning

Remote clients track the device's protocol version. Newer device, older client: works with reduced features. Older device, newer client: works at the device's older API.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Platform secure-storage absent   | refuse pairing; explain        |
| WebRTC unavailable               | text-only mode                 |
| Push not configured              | proactive nudges visible only  |
|                                  | when app open                   |
| LAN discovery blocked            | manual IP / WAN rendezvous     |
| Background killed by OS          | reconnect on foreground        |

## Acceptance criteria

- [ ] All six platforms ship a viable client
- [ ] Native secure storage used per platform
- [ ] WebRTC voice works on all platforms that support it
- [ ] Push integration where supported
- [ ] LAN + WAN both functional
- [ ] Capability scope honored per platform constraints

## References

- `13-remotes/REMOTE-ARCHITECTURE.md`
- `13-remotes/REMOTE-PROTOCOL.md`
- `13-remotes/DEVICE-PAIRING.md`
- `13-remotes/REMOTE-DISCOVERY.md`
- `06-sdk/SDK-BINDINGS-TYPESCRIPT.md`
## Graph links

[[REMOTE-ARCHITECTURE]]  [[REMOTE-PROTOCOL]]  [[DEVICE-PAIRING]]
