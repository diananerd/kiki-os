# Kiki OS — Agent Team Instructions

Kiki OS is an open research OS for agentic computing (Agentic UX/HCI). The repo is `build-in-public`; correctness matters more than speed.

## Repo layout

```
docs/          — documentation corpus (DESIGNs, GUIDEs, ADRs, RFCs, INDEX files)
docs/specs/    — all SPEC documents (131 files, flat, all type: SPEC)
.claude/       — agent team config (hooks, agent roles, settings)
```

## Document types

- **SPEC** — operational contract with acceptance criteria. Lives in `docs/specs/`.
- **DESIGN** — decision + rationale. Lives in the chapter directory.
- **ADR** — architectural decision record. Lives in `docs/14-rfcs/`.
- **GUIDE** — orientation. INDEX files, README, CONVENTIONS, CONTRIBUTING.

## Cross-references

Frontmatter `depends_on` / `depended_on_by` use stable kebab-case **IDs**, never file paths.  
Prose references inside INDEX files use relative paths: `../specs/FILENAME.md` for SPECs, `FILENAME.md` for files in the same directory.

## Agent team norms

- Each teammate owns a clearly scoped set of files. No two teammates edit the same file concurrently.
- Mark a task `in_progress` before starting work on it; mark `completed` only after verifying the output.
- Do not declare a task complete without reading and verifying the affected files.
- Commit at each unit of completed work with a descriptive message.
- Scope creep is forbidden: do exactly what the task says, nothing more.
- When in doubt about scope, ask the lead — do not expand unilaterally.

## Conventions

- Frontmatter is required on every doc. See `docs/CONVENTIONS.md`.
- All `status:` values are `draft` until a subsystem is implemented and tested.
- Filenames: `UPPERCASE-WITH-DASHES.md`.

## What NOT to do

- Do not move files without updating all cross-references.
- Do not change `id:` frontmatter fields (they are stable forever).
- Do not create files outside `docs/` or `docs/specs/` without explicit instruction.
