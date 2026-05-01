# Contributing to Kiki OS Documentation

## Before you write

1. Read `00-foundations/PARADIGM.md`. It defines what Kiki OS is. Documents that contradict the paradigm will be rejected.
2. Read `00-foundations/PRINCIPLES.md`. The principles are ordered; higher-priority principles win when in conflict.
3. Read `CONVENTIONS.md`. Frontmatter, structure, and validation rules are non-negotiable.

## What kind of change are you making?

| Change type | Process |
|---|---|
| Typo, clarification, rephrasing | Direct edit, normal review |
| New SPEC for an existing chapter | New file, normal review |
| Major design change to existing component | Open an RFC first |
| New cross-cutting capability or constraint | Open an RFC first |
| Decision worth recording (any pick from alternatives) | Add an ADR |
| New chapter | Open an RFC; chapters are structural |

The line is: **does this change the contract that other documents depend on?** If yes, RFC. If no, direct PR.

## RFC workflow

1. Copy `14-rfcs/RFC-TEMPLATE.md` to `14-rfcs/RFC-<short-name>.md`.
2. Fill in the sections.
3. Open a PR labeled `rfc`.
4. Discussion period: minimum 7 days for non-trivial RFCs.
5. On acceptance: assign a sequential number, rename to `RFC-NNNN-<short-name>.md`, merge with `status: draft`. The doc graduates to `stable` only after the subsystem it describes has a working implementation that exercises the contract.

## ADR workflow

ADRs are lighter weight than RFCs. They record decisions you have already made.

1. Copy `14-rfcs/ADR-TEMPLATE.md` to `14-rfcs/NNNN-<short-name>.md` (next available number).
2. Fill in Context, Decision, Consequences, Alternatives.
3. Open a PR. Reviewers check that the decision is consistent with paradigm and principles.
4. Merge with `status: draft`. ADRs graduate to `stable` once the decision they record is reflected in implemented and exercised code.

## Authoring a SPEC

1. Confirm the SPEC has a clear `Purpose` and lives in the right chapter.
2. Cite `depends_on` correctly in frontmatter.
3. Write `## Acceptance criteria` as a concrete checklist. A SPEC without testable criteria is not done.
4. Add `## Open questions` for known unknowns; do not pretend everything is resolved.

## Authoring a DESIGN

1. State `## Problem` first. A design without a problem is decoration.
2. List `## Constraints` exhaustively. The constraints rule out alternatives; if constraints are weak, the decision is weak.
3. The `## Rationale` explains why this decision and not the alternatives. If you cannot articulate why this is better, the decision is not ready.
4. `## Consequences` includes negative consequences. State what we accept losing.

## Style

- English is the canonical language.
- American spelling.
- Prefer "the agent" or "Kiki" to "AI" when referring to Kiki's agent.
- Use "user" for the human, never "operator" or "owner".
- Avoid marketing words (smart, seamless, magical, intelligent). State what the system does.

## Reviewers

A document moves to `status: stable` only after:

- The linter passes.
- At least one reviewer with maintainer role approves.
- Cross-references from other stable docs are checked.
- For RFCs: the discussion period has elapsed.
- The subsystem the document describes has working code that exercises the contract.

## License

All documentation is licensed under the same license as Kiki OS. By contributing, you agree to that license.
