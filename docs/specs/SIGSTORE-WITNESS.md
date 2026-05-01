---
id: sigstore-witness
title: Sigstore Witness (Opt-in Transparency)
type: SPEC
status: draft
version: 0.0.0
implements: [sigstore-witness]
depends_on:
  - cosign-trust
  - audit-merkle-chain
depended_on_by:
  - audit-merkle-chain
  - oci-native-model
  - oci-workflows
last_updated: 2026-04-29
---
# Sigstore Witness (Opt-in Transparency)

## Purpose

Specify the optional transparency log integration via Sigstore Rekor and sigsum witnesses for two use cases: signing-side (publishers' artifacts in transparency log) and audit-side (Kiki audit log's Merkle heads in witness).

## Behavior

### Two use cases

1. **Publisher transparency.** A maintainer signing an artifact submits the signature to Sigstore Rekor. Anyone can verify that maintainer X signed artifact Y at time Z, and the maintainer cannot retroactively deny it.

2. **Audit log transparency.** A Kiki device submits its audit log's Merkle tree heads to a sigsum witness. Anyone can verify that the device's audit log was in a specific state at a specific time, and the device cannot retroactively rewrite history.

Both use cases are opt-in.

### Why opt-in

- Privacy: not every maintainer wants their artifacts in a public log.
- Network requirement: submission requires connectivity at signing or per-checkpoint time.
- Cost: maintainers/users don't pay for sigsum (free witness operators) but the operation has a small overhead.

The defaults are conservative: signing-side opt-in per maintainer, audit-side opt-in per user.

### Sigstore Rekor (publisher side)

When a maintainer signs with `cosign sign --rekor-url https://rekor.sigstore.dev ...`, the signature plus the artifact digest is submitted to Rekor. Rekor returns a Rekor entry index and a Merkle inclusion proof.

The Rekor entry is publicly visible. Anyone can:

- Query Rekor by signing identity to find all artifacts signed.
- Verify a specific artifact's Rekor entry exists.
- Detect a maintainer signing something they should not have (e.g., after key compromise, the rate of signing changes suspiciously).

Devices verifying with `cosign verify --rekor-url ...` confirm the signature is in Rekor at install time. This provides:

- **Non-repudiation**: maintainer cannot deny signing.
- **Detection of stolen keys**: anomalous signing activity is observable.
- **Time of signing**: cryptographically attested.

### Sigsum (audit side)

For Kiki's audit log: a sigsum witness signs Merkle tree heads from the device's audit log Merkle tree.

```
1. Device computes a Merkle tree head every N entries or M minutes.
2. Device signs the head with its device key.
3. Device submits the signed head to a sigsum witness.
4. Witness counter-signs the head and publishes its log.
5. Anyone can verify: "Kiki device X had audit log in state Y at time Z, witnessed by W."
```

This provides:

- **Non-repudiation**: the device cannot retroactively rewrite the audit log without detection.
- **Forensic verifiability**: investigators can verify the audit log's claimed state.

The user opts in:

```
agentctl audit witness enable --witness sigsum.glasklarteknik.com
```

After opt-in:

- Tree heads are submitted at the configured frequency.
- Receipts are stored locally.
- agentui shows a "Transparency: ON" indicator.

### Witness operators

Default sigsum witnesses:

- Glasklar Teknik (project maintainers).
- Mullvad-operated witness.
- Self-hosted witness for sovereignty-conscious deployments.

Users can configure multiple witnesses; submission is fan-out.

### Privacy of submissions

What is published to Rekor or sigsum:

- The signature/Merkle root and metadata (timestamp, signing identity, artifact digest).
- Not the artifact content.
- Not the audit log entries' content.

The witness sees only cryptographic commitments, not the underlying data.

For audit log: Kiki publishes only Merkle roots, never entries. Even if all witness submissions are observed, they do not reveal what Kiki users did — only that they did things at certain times.

### Frequency tuning

Tree head submission frequency:

- High (every entry): real-time non-repudiation, more network traffic.
- Medium (every 100 entries or 1 hour): default.
- Low (daily): minimal traffic, eventually-consistent non-repudiation.

User configures per audit log policy.

### Verification by third parties

Anyone with access to a tree head from a witness can verify:

```
1. Get tree head from witness's log.
2. Get inclusion proof for a specific entry from the device.
3. Verify the proof against the witness's tree head.
```

This is how an investigator might verify an audit claim.

### What this does NOT protect against

- A device that never opts in: no witness, no transparency. Detection requires comparing with peer devices or other forensic methods.
- An adversary who controls the device and submits fake heads: but if they're also in the witness log, peers can detect inconsistency.
- A compromised witness: mitigated by submitting to multiple witnesses; consistency across them is required.

## Interfaces

### Programmatic

```rust
pub fn submit_tree_head(witness_url: &str, head: &SignedTreeHead) -> Result<WitnessReceipt>;
pub fn verify_against_witness(witness_url: &str, head: &TreeHead, proof: &ConsistencyProof) -> Result<bool>;
pub fn rekor_submit(signature: &Signature, artifact: &ArtifactRef) -> Result<RekorEntry>;
pub fn rekor_verify(signature: &Signature, artifact: &ArtifactRef) -> Result<RekorEntry>;
```

### CLI

```
agentctl audit witness enable --witness <url>
agentctl audit witness disable
agentctl audit witness submit-now           # force submission
agentctl audit witness verify <head>        # verify a head against witness
agentctl trust verify --rekor <oci-url>     # verify cosign signature via Rekor
```

## State

### Persistent

- Witness submission receipts.
- Configured witness endpoints per user.

### In-memory

- Pending submission queue.

## Failure modes

| Failure | Response |
|---|---|
| Witness unreachable | retry; queue for later submission |
| Witness rejects | log; alert; investigate |
| Multiple witness inconsistency | alert; potential compromise |
| Rekor unreachable on signing | local-only signing; retry submission later |
| Rekor unreachable on verify | option: fail closed (require Rekor) or fail open (warn) |

## Performance contracts

- Submission to witness: bounded by network (~500ms typical).
- Verification of inclusion proof: <10ms.

## Acceptance criteria

- [ ] Sigsum witness submission opt-in works.
- [ ] Submission receipts stored.
- [ ] Multiple witness fan-out supported.
- [ ] Verification by third parties via witness logs possible.
- [ ] Rekor integration on cosign sign/verify works.

## Open questions

- Whether to default audit witness on for users in regulated contexts.

## References

- `10-security/AUDIT-MERKLE-CHAIN.md`
- `10-security/COSIGN-TRUST.md`
- `10-security/AUDIT-LOG.md`
- `14-rfcs/0003-cosign-sigstore-trust.md`
- sigsum project: https://sigsum.org
- Sigstore Rekor: https://docs.sigstore.dev/rekor/
## Graph links

[[COSIGN-TRUST]]  [[AUDIT-MERKLE-CHAIN]]
