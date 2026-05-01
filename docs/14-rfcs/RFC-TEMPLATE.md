---
id: rfc-template
title: RFC Template
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# RFC Template

Copy this template to `14-rfcs/RFC-<short-name>.md`, fill it in, and open a PR labeled `rfc`. After acceptance, the file is renamed to `RFC-NNNN-<short-name>.md`.

---

```yaml
---
id: rfc-<short-name>
title: <Human Title>
type: RFC
status: draft
version: 0.0.0
implementation_status: pending
depends_on: []
last_updated: <ISO-date>
---
```

# RFC: <Title>

## Summary

One paragraph. The change in plain English. What problem this RFC addresses, the proposed solution, the impact.

## Motivation

What problem does this solve?

Why now? What changed (research, deployment data, ecosystem evolution) that makes this RFC timely?

What is the cost of inaction?

## Detailed design

Concrete proposal. Include:

- **Schemas, APIs, protocols** — exact shape of any contract.
- **Semantics** — what each operation means.
- **Failure modes** — how the change behaves when things go wrong.
- **Backward compatibility** — how existing systems continue to work.
- **Performance implications** — measured or estimated.
- **Security implications** — threat model considerations.
- **Privacy implications** — data flow consequences.

Pseudocode is welcome. Concrete examples are required.

## Drawbacks

What does this cost? What do we accept losing?

Common drawbacks to consider:

- Implementation complexity.
- Maintenance burden.
- Compatibility breaks.
- Performance regressions in some cases.
- Cognitive load on contributors.

## Alternatives

What other approaches were considered?

For each alternative, briefly state:

- The alternative.
- Why it was rejected.

The strongest RFCs honestly engage with two or three credible alternatives.

## Unresolved questions

Open issues that block acceptance, or questions for the discussion period:

- [ ] Question 1
- [ ] Question 2

If there are no unresolved questions, state "None" explicitly.

## Adoption strategy

How does this RFC get adopted?

- Migration path for existing systems.
- Deprecation timeline if any.
- Version strategy (major bump? minor?).
- Documentation that needs to follow.
- Test coverage that needs to follow.
- Rollout sequence (which subsystems first).

## References

- Related RFCs.
- Related ADRs.
- External research, papers, prior art.
