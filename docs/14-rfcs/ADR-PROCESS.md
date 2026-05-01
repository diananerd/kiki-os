---
id: adr-process
title: ADR Process
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# ADR Process

Architectural Decision Records (ADRs) document decisions already made. They are lighter weight than RFCs.

## When to use an ADR

Use an ADR when:

- A non-trivial choice was made between alternatives.
- The choice affects more than one document.
- Future contributors will need to know why this choice was made.
- The choice is unlikely to change but worth documenting.

Use an RFC instead when:

- The change is structural, foundational, or paradigm-affecting.
- A discussion period is warranted before a decision is made.
- See `RFC-PROCESS.md`.

## ADR structure

Use `ADR-TEMPLATE.md`. Sections:

- **Status** — proposed, accepted, deprecated, superseded.
- **Context** — what motivated this decision. What constraints apply.
- **Decision** — the actual decision in one or two paragraphs.
- **Consequences** — both positive and negative outcomes.
- **Alternatives considered** — what else was evaluated, briefly.
- **References** — related docs, RFCs, external sources.

ADRs are short. A typical ADR is 1–3 pages.

## Lifecycle

```
proposed → accepted → eventual deprecated | superseded-by:NNNN
```

1. **Propose.** Author copies `ADR-TEMPLATE.md` to `14-rfcs/NNNN-<short-name>.md` (next available number).
2. **Review.** One or two maintainer approvals depending on scope. Reviewers check that the decision is consistent with the paradigm and principles.
3. **Accept.** ADR merges with `status: draft`. It graduates to `stable` once the decision it records is reflected in implemented and exercised code.
4. **Eventual change.** When superseded, the ADR is updated with `status: superseded-by:NNNN` pointing to its replacement.

## Numbering

ADRs and RFCs share a sequential number space. The `0001-0099` range is reserved for foundational v0 ADRs.

## ADR vs RFC

| Trait | ADR | RFC |
|---|---|---|
| Discussion period | Optional, brief | Mandatory, ≥7 days |
| Approvals | 1–2 maintainers | 2–3 maintainers depending on scope |
| Length | 1–3 pages | Often 5–15 pages |
| Audience | Future contributors | All stakeholders during decision |
| When | Decision is already clear | Decision needs collective input |

## Granularity

One ADR per discrete decision. Avoid:

- ADRs that bundle multiple decisions.
- ADRs that re-litigate paradigm-level choices (those are RFCs).
- ADRs without alternatives (decisions without choices are not worth recording).

## References

- `14-rfcs/RFC-PROCESS.md`
- `14-rfcs/ADR-TEMPLATE.md`
