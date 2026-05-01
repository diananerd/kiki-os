---
id: adr-template
title: ADR Template
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# ADR Template

Copy this template to `14-rfcs/NNNN-<short-name>.md` (next available number), fill it in, open a PR.

---

```yaml
---
id: NNNN-<short-name>
title: <Human Title>
type: ADR
status: draft
version: 0.0.0
depends_on: []
last_updated: <ISO-date>
---
```

# ADR-NNNN: <Title>

## Status

`accepted` | `proposed` | `deprecated` | `superseded-by:NNNN`

## Context

What forces are at play that led to this decision?

- Constraints (technical, business, paradigmatic).
- Trade-offs being navigated.
- What's known and what's uncertain.

Two to four paragraphs.

## Decision

The decision. Stated clearly.

One or two paragraphs. Concrete enough that a reader knows what was chosen, not just what was considered.

## Consequences

What follows from this decision.

### Positive

- Outcomes the decision enables.
- Problems the decision resolves.

### Negative

- Costs we accept.
- Constraints this decision imposes.
- What this decision rules out.

Be honest about negative consequences. A decision without negative consequences is suspicious.

## Alternatives considered

Brief list of alternatives with one-line rejection reasons.

- **Alternative A** — Rejected because [reason].
- **Alternative B** — Rejected because [reason].

Two to four alternatives is typical. If there are no alternatives, the decision was not really a decision.

## References

- Related ADRs.
- Related RFCs.
- External research, blog posts, papers.
- SPECs that depend on this decision.
