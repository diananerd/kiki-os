---
id: audit-merkle-chain
title: Audit Merkle Chain
type: SPEC
status: draft
version: 0.0.0
implements: [audit-merkle]
depends_on:
  - audit-log
  - cryptography
  - sigstore-witness
depended_on_by:
  - audit-log
  - sigstore-witness
last_updated: 2026-04-29
---
# Audit Merkle Chain

## Purpose

Specify the cryptographic hash chain over audit log entries: how entries are linked, how the chain is verified, and how periodic Merkle roots are submitted to optional Sigstore witnesses for transparency.

## Behavior

### Per-entry hash chain

Each audit log entry is hashed:

```
canonical(entry) = CBOR-encode(timestamp_ns, user_id, category, event_kind, actor, target, payload, privacy, severity, correlate_with)
entry_hash = SHA-256(prev_hash || canonical(entry))
```

The first entry's `prev_hash` is `0x0000...` (32 zero bytes).

`prev_hash` and `entry_hash` are stored as columns in the SQLite table.

A change to any entry invalidates all subsequent `entry_hash` values; verification detects tampering.

### RFC 9162 binary Merkle tree

In addition to the per-entry hash chain, a binary Merkle tree (RFC 9162 / Certificate Transparency v2 style) is built over batches of entries:

- Domain-separated leaf hashes: `H(0x00 || canonical(entry))`.
- Domain-separated node hashes: `H(0x01 || left || right)`.
- Tree heads computed periodically (every N entries or every M minutes).

Each tree head is signed with the device key (Ed25519). Tree heads accumulate as a chain of "signed checkpoints."

We use the `ct-merkle` crate for the implementation.

### Why both per-entry chain and Merkle tree

- **Per-entry chain**: cheap, detects sequential tampering, no extra verification cost on read.
- **Merkle tree**: enables efficient inclusion and consistency proofs. A single signed tree head proves that a specific entry exists in the log without sharing the entire log.

The Merkle tree is what we publish externally (via Sigstore witness, when opted in). The per-entry chain is for local integrity.

### Sigstore witness submission

When the user opts in to transparency:

- Each Merkle tree head is submitted to a Sigstore witness (sigsum, by default).
- The witness counter-signs the tree head and publishes its log.
- The user (or anyone) can verify the witness's log includes our tree heads.

This provides non-repudiation: we cannot retroactively claim our log was different than what the witness saw at the time.

Sigstore witness submission is opt-in. The default is local-only (per-entry chain + local Merkle tree). Submission is configurable per user.

### Verification

#### Per-entry chain verification

```rust
pub fn verify_chain(db: &SqliteDb) -> Result<VerifyReport> {
    let mut prev_hash = ZERO_HASH;
    for entry in db.iter() {
        let computed = sha256(prev_hash || canonical(&entry));
        if computed != entry.entry_hash { return Err(...); }
        prev_hash = entry.entry_hash;
    }
    Ok(VerifyReport { entries: count, last_hash: prev_hash })
}
```

Run by `agentctl audit verify`.

#### Merkle inclusion proof

To prove that entry E is in the log at tree head T:

```rust
pub fn prove_inclusion(entry_id: &EventId, tree_head: &TreeHead) -> InclusionProof;
pub fn verify_inclusion(entry: &Entry, proof: &InclusionProof, tree_head: &TreeHead) -> bool;
```

Proof size is logarithmic in tree size.

#### Consistency proof between tree heads

To prove that tree at head T1 is a prefix of tree at head T2:

```rust
pub fn prove_consistency(t1: &TreeHead, t2: &TreeHead) -> ConsistencyProof;
pub fn verify_consistency(t1: &TreeHead, t2: &TreeHead, proof: &ConsistencyProof) -> bool;
```

Proves the log only appended (no rewrites).

### Witness operators

Default sigsum witnesses (when opted in):

- Glasklar Teknik (sigsum primary).
- Other community witnesses operated by Mullvad and others.

Users can configure additional witnesses or self-host one.

### What this protects against

- **In-place tampering**: detected by hash chain verification.
- **Silent rewrite**: detected by consistency proof against witness.
- **Targeted hiding**: an entry deleted from the local log would invalidate the chain; even retroactively rebuilding the chain is detectable via witness consistency.
- **Plausible deniability about past events**: non-repudiation via witness signing.

### What this does NOT protect against

- An adversary who controls the device entirely and never submits anything to the witness can run a separate "hidden" log; the witness only proves what was submitted.
- A compromised device key could forge tree head signatures; mitigation: device key in TPM, sealed against PCRs.
- The user choosing to wipe their own audit log; this is logged itself but the wipe action is recorded. Forensic reconstruction is then a witness exercise.

### Storage cost

- Per-entry overhead: ~64 bytes (prev_hash + entry_hash).
- Merkle tree state: O(log n) per tree head.
- Witness submissions: ~256 bytes per submission, every N entries or M minutes.

For a typical user generating ~50KB/day of audit log content, the chain overhead adds ~5KB/day; witness submissions add bytes-per-submission × frequency. All well within budget.

### Performance

- Per-append hash computation: <10µs.
- Tree head computation per batch: <1ms for 1000 entries.
- Inclusion proof: <100µs.
- Consistency proof: <1ms.
- Witness submission: bounded by network (~500ms).

## Interfaces

### Programmatic

```rust
pub fn append_with_chain(event: AuditEvent) -> Result<(EventId, Hash)>;
pub fn current_tree_head() -> TreeHead;
pub fn submit_to_witness(witness_url: &str) -> Result<WitnessReceipt>;
pub fn verify_inclusion(entry: &Entry, proof: &InclusionProof, head: &TreeHead) -> bool;
pub fn verify_consistency(old: &TreeHead, new: &TreeHead, proof: &ConsistencyProof) -> bool;
```

### CLI

```
agentctl audit verify                  # verify per-entry chain
agentctl audit witness submit          # submit current tree head
agentctl audit witness verify <head>   # verify witness has this head
agentctl audit prove-inclusion <id>    # generate inclusion proof
```

## State

### Persistent

- Hash columns in audit_log table.
- Tree head history.
- Witness submission receipts.

### In-memory

- Active Merkle tree (incremental).

## Failure modes

| Failure | Response |
|---|---|
| Chain verification fails | alert; mark log as compromised; user-driven recovery |
| Witness unreachable | retry; queue submission for later |
| Witness rejects submission | log; alert user; investigate |
| Tree head signature invalid (replay) | alert; reject |

## Acceptance criteria

- [ ] Per-entry hash chain in place.
- [ ] ct-merkle Merkle tree built over entries.
- [ ] Tree heads signed with device key.
- [ ] Sigstore witness submission opt-in works.
- [ ] Inclusion and consistency proofs verifiable.
- [ ] `agentctl audit verify` detects tampering.

## References

- `10-security/AUDIT-LOG.md`
- `10-security/CRYPTOGRAPHY.md`
- `10-security/SIGSTORE-WITNESS.md`
- `14-rfcs/0036-ct-merkle-audit-chain.md`
- RFC 9162 (Certificate Transparency v2)
- sigsum project documentation
## Graph links

[[AUDIT-LOG]]  [[CRYPTOGRAPHY]]  [[SIGSTORE-WITNESS]]
