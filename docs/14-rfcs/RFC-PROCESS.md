---
id: rfc-process
title: RFC Process
type: GUIDE
status: draft
version: 0.0.0
last_updated: 2026-04-29
---
# RFC Process

RFCs propose major changes to Kiki OS. The process is designed to surface objections, alternatives, and consequences before a change becomes load-bearing.

## When an RFC is required

Open an RFC when the proposed change:

- Adds, removes, or restructures a chapter of documentation.
- Modifies a foundational document (`00-foundations/*` or `01-architecture/*`).
- Changes the paradigm, principles, or trust boundaries.
- Adds a new daemon or system service.
- Adds or removes a media type or namespace.
- Changes the capability taxonomy or grant levels.
- Modifies the audit log schema or hash chain.
- Adds a new hardcoded restriction.
- Changes the OTA channel structure.
- Introduces a new wire protocol or transport.

Most other changes use ADRs (lighter weight). When in doubt, ask a maintainer.

## RFC structure

Use `RFC-TEMPLATE.md`. Sections:

- **Summary** — one paragraph. The change in plain English.
- **Motivation** — what problem does this solve? Why now?
- **Detailed design** — concrete proposal. Schemas, APIs, semantics.
- **Drawbacks** — costs, consequences, what we accept losing.
- **Alternatives** — other approaches considered, why rejected.
- **Unresolved questions** — open issues that block acceptance.
- **Adoption strategy** — migration path, deprecation plan, version strategy.

## Lifecycle

```
draft → discussion → revision → accepted | rejected
```

1. **Draft.** Author copies `RFC-TEMPLATE.md` to `14-rfcs/RFC-<short-name>.md` and opens a PR labeled `rfc`.
2. **Discussion.** Minimum 7 days for non-trivial RFCs. Reviewers engage in PR comments. Author revises.
3. **Revision.** Author updates the RFC based on feedback. Multiple iterations are normal.
4. **Decision.** A maintainer with the relevant area of expertise decides:
   - **Accept.** RFC merges with `status: draft` and a sequential `RFC-NNNN` number; renamed accordingly. It graduates to `stable` once the subsystem it describes has working, exercised code.
   - **Reject.** RFC merges with `status: deprecated` and a closing comment explaining why. Sequential number assigned for traceability.
5. **Implementation.** Accepted RFCs trigger implementation work. The RFC remains the canonical reference for the design.

## Quorum

- **Trivial RFCs** (clarifications, schema additions): one maintainer approval.
- **Architectural RFCs**: two maintainer approvals.
- **Foundational RFCs** (paradigm, principles, trust boundaries): three maintainer approvals plus a 14-day discussion period.

## Numbering

Sequential, one global namespace. Numbers are assigned at acceptance.

- 0001–0099: foundational and stack decisions. Assigned at v0.
- 0100+: post-v0 decisions in order of acceptance.

## Withdrawing an RFC

The author may withdraw an RFC at any time before acceptance. A withdrawn RFC merges with `status: deprecated` and a note. Withdrawing does not preclude reopening with a new RFC number.

## Superseding an RFC

A new RFC may supersede an existing one. The new RFC explicitly states which RFC it supersedes. The old RFC is updated with `status: superseded-by:RFC-NNNN`.

## Implementation status

After acceptance, an RFC's implementation status is tracked in the RFC itself:

- `pending` — no implementation started.
- `in-progress` — implementation underway.
- `complete` — implementation merged.
- `abandoned` — implementation halted (with note).

This is a separate field from the document `status`.

## Templates

See `RFC-TEMPLATE.md`.

## References

- `14-rfcs/ADR-PROCESS.md` — when to use an ADR instead.
- `14-rfcs/RFC-TEMPLATE.md`
