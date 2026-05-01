---
id: speaker-id
title: Speaker ID
type: SPEC
status: draft
version: 0.0.0
implements: [speaker-id]
depends_on:
  - voice-pipeline
  - audio-io
  - capability-gate
  - privacy-model
depended_on_by: []
last_updated: 2026-04-30
---
# Speaker ID

## Purpose

Specify the on-device speaker identification system. Speaker id distinguishes which household member is speaking so the agent answers in the right context (right user's memory, right preferences, right capability scope). It is local-only; voice prints never leave the device.

## Why local-only

A voice print is biometric. Sending biometric data off-device would be both a privacy violation and a regulatory minefield. Speaker id stays on-device by design.

## Approach

Speaker id is performed by a small embedding model + a per-user voice-print stored locally:

```
audio (post-AEC) → speaker embedding model → voice vector
                                                 │
                                          cosine similarity
                                                 │
                                       per-user enrolled vector
                                                 │
                                       best match + confidence
```

Models considered: small ECAPA-TDNN derivatives, on-device speaker verification networks. The exact model is shipped per the `INFERENCE-MODELS.md` catalog.

## Enrollment

When a user is created or wants to enable speaker id:

1. The user reads a short enrollment prompt aloud (5-10 phrases, ~30 seconds)
2. The model produces an embedding per phrase; mean is the user's voice print
3. Voice print stored at `/var/lib/kiki/users/<uid>/voice/voice-print.bin` (encrypted at rest)

Optional re-enrollment over time as the user's voice changes.

## Identification

For each utterance:

- Compute the embedding
- Compare against all enrolled voice prints
- Pick the best match if confidence is above threshold
- If no match above threshold: "guest" — limited capability scope

The threshold is tunable (default 0.75 cosine).

## Multi-user disambiguation

If two voice prints are close (siblings, twins), the system marks the result as ambiguous and may:

- Ask the user "is that you, Diana?"
- Default to the foreground user
- Use additional signals (typing user, paired-remote-source) for context

## Effects on the agent

When speaker id resolves to user X:

- The agent loop loads X's identity, X's policies, X's grants
- The voice session is bound to X's user account
- Episodic memory writes go to X's session
- Capabilities are X's

A "guest" speaker has the most-restricted scope: read-only general agent, no identity reads, no scoped grants.

## Privacy

- Voice prints encrypted at rest with the user's keys
- Never transmitted (cloud STT may receive *audio* in hybrid mode, but the voice print itself stays local)
- The user can delete their voice print at any time
- The user can disable speaker id entirely; the system then defaults to the foreground user

## Capability

`agent.voice.speaker_id` — daemon-internal. Per-user enrollment is gated by the user themselves (consent flow if it touches identity files).

## Configuration

```toml
[speaker_id]
enabled = true
threshold = 0.75
on_low_confidence = "ask"      # ask | guest | foreground
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| No enrollment for any user       | guest scope; surface           |
|                                  | enrollment prompt              |
| All matches below threshold      | guest scope; ask if user wants |
|                                  | to enroll                      |
| Enrollment quality too low       | re-prompt                      |
| Voice has changed (illness)      | retry; offer re-enrollment     |

## Performance

- Embedding inference: <50ms per utterance
- Comparison against N voice prints: O(N), typically <5ms total
- Memory: ~30MB for the embedding model

## Acceptance criteria

- [ ] Enrollment is on-device and quick
- [ ] Multi-user identification works above threshold
- [ ] Voice prints encrypted at rest
- [ ] Voice prints never leave the device
- [ ] User can disable, delete, re-enroll
- [ ] Guest scope applies on low confidence

## References

- `08-voice/VOICE-PIPELINE.md`
- `08-voice/AUDIO-IO.md`
- `08-voice/BARGE-IN.md`
- `03-runtime/INFERENCE-MODELS.md`
- `10-security/PRIVACY-MODEL.md`
- `10-security/STORAGE-ENCRYPTION.md`
## Graph links

[[VOICE-PIPELINE]]  [[AUDIO-IO]]  [[CAPABILITY-GATE]]  [[PRIVACY-MODEL]]
