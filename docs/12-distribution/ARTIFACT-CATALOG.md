---
id: artifact-catalog
title: Artifact Catalog
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - oci-native-model
  - namespace-model
  - media-types
depended_on_by:
  - meta-packages
  - release-cadence
last_updated: 2026-04-30
---
# Artifact Catalog

## Purpose

List the canonical Kiki-published artifacts: the ones every device pulls or might pull. Third-party publishers ship under their own namespaces; this catalog is what the Kiki Foundation produces.

## System base

```
kiki:system/base@<ver>                     bootc base image
kiki:system/base-headless@<ver>             headless variant
kiki:system/base-developer@<ver>            developer variant
kiki:system/base-minimal@<ver>              minimal kiosk variant
```

bootc images; user-invisible upstream is CentOS Stream 10.

## System extensions (sysext)

```
kiki:system/agentd@<ver>                    agent daemon
kiki:system/policyd@<ver>                   policy daemon
kiki:system/inferenced@<ver>                inference daemon
kiki:system/memoryd@<ver>                   memory daemon
kiki:system/toolregistry@<ver>              tool registry
kiki:system/cage@<ver>                      compositor
kiki:system/agentui@<ver>                   GUI client
kiki:system/voice-daemon@<ver>              voice pipeline
kiki:system/natsd@<ver>                     embedded NATS
```

## Models

```
kiki:models/llama-3.3-8b-q4@<ver>            default LLM
kiki:models/llama-3.3-70b-q4@<ver>            higher-tier LLM
kiki:models/granite-guardian-3.2-5b@<ver>     safety classifier
kiki:models/llama-prompt-guard-2-86m@<ver>     stage-1 arbiter
kiki:models/whisper-large-v3-turbo@<ver>      ASR
kiki:models/whisper-medium@<ver>              ASR (Standard)
kiki:models/whisper-small@<ver>               ASR (Reference)
kiki:models/kokoro-82m@<ver>                  TTS
kiki:models/piper-en@<ver>                    TTS fallback
kiki:models/bge-m3@<ver>                      embedder
kiki:models/jina-reranker-v2@<ver>            re-ranker
kiki:models/microwakeword-default@<ver>       wake word
kiki:models/silero-vad-v5@<ver>               VAD
```

## Components

```
kiki:components/standard@<ver>                standard component library
kiki:components/voice-waveform@<ver>          voice surface visual
kiki:components/audit-table@<ver>             audit log viewer
kiki:components/memory-inspector@<ver>        memory browser
```

## Tools

```
kiki:tools/calculator@<ver>
kiki:tools/web-fetch@<ver>
kiki:tools/markdown-render@<ver>
kiki:tools/file-search@<ver>
kiki:tools/code-edit@<ver>
kiki:tools/calendar@<ver>
... (curated set)
```

## Apps

```
kiki:apps/launcher@<ver>                      the launcher
kiki:apps/settings@<ver>                      Settings app
kiki:apps/setup@<ver>                         provisioning flow
kiki:apps/audit@<ver>                         audit viewer
kiki:apps/memory@<ver>                        memory inspector
kiki:apps/files@<ver>                         file browser
kiki:apps/terminal@<ver>                      terminal app
kiki:apps/dev-console@<ver>                   developer console
```

## Profiles

```
kiki:profiles/default@<ver>                   default for normal users
kiki:profiles/kid-friendly@<ver>              child users
kiki:profiles/secops-engagement@<ver>         security engagements
kiki:profiles/kiosk-museum@<ver>              kiosk variants
kiki:profiles/headless-server@<ver>           headless deployment
kiki:profiles/developer@<ver>                 developer tooling on
kiki:profiles/accessibility-first@<ver>       a11y-default tuning
```

## Skills

A small Foundation-curated set of skills (recipes) that ship by default; users add their own:

```
kiki:skills/morning-news@<ver>
kiki:skills/weekly-summary@<ver>
kiki:skills/calendar-prep@<ver>
kiki:skills/memory-housekeeping@<ver>
```

## Agent bundles

```
kiki:agents/default@<ver>                     default subagent set
kiki:agents/coding-buddy@<ver>                coding-specialized
kiki:agents/research-assistant@<ver>          research-specialized
kiki:agents/writer@<ver>                      writing-specialized
```

## Prompts pack

```
kiki:prompts/system@<ver>                     curated prompts
                                              (arbiter, compaction, ...)
```

## Versioning

All artifacts follow semver. Major bumps may require coordinated release across artifacts (e.g., a system base v3 might require sysext v3 for its daemons). Cross-artifact compatibility matrix documented per release.

## Total catalog size

Roughly 30 core artifacts. Third-party adds to it but stays under separate namespaces.

## Removal

If an artifact is retired, it's marked deprecated with a replacement pointer. Devices warn users; the OS update flow may auto-migrate where safe.

## References

- `12-distribution/OCI-NATIVE-MODEL.md`
- `12-distribution/NAMESPACE-MODEL.md`
- `12-distribution/META-PACKAGES.md`
- `12-distribution/RELEASE-CADENCE.md`
- `03-runtime/INFERENCE-MODELS.md`
