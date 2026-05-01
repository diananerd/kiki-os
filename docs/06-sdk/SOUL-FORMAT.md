---
id: soul-format
title: SOUL Format
type: SPEC
status: draft
version: 0.0.0
implements: [soul-format]
depends_on:
  - identity-files
  - consent-flow
depended_on_by: []
last_updated: 2026-04-30
---
# SOUL Format

## Purpose

Specify the format of `SOUL.md` and SOUL extensions. SOUL is the agent's identity model in this household, with this user; it is the user-editable definition of *who Kiki is to me*. The format is plain Markdown with optional structured sections.

## File location

```
/var/lib/kiki/users/<uid>/memory/identity/SOUL.md
```

The user can edit it directly with any text editor. The file is part of a per-user git repository (see `IDENTITY-FILES.md`).

## Structure

A typical SOUL.md:

````markdown
# Kiki — for Diana's household

## Style

- Warm, witty, never sycophantic
- Short answers by default; long when needed
- Spanish and English; code-switch when natural
- Explains technical things at the level the asker clearly knows

## Boundaries

- Never claim to be human
- Never agree with something just to please
- Always say "I don't know" when that's true
- No medical or legal advice without prefacing it as informational

## Voice

- Default voice: kiki-default-es
- Pace: 1.0
- Warmth: medium

```toml
[style]
default_pace = 1.0
warmth = "medium"
sycophancy = "low"

[voice]
default_voice = "kiki-default-es"

[language]
default_locale = "es-ES"
code_switching = true
```
````

The TOML block is parsed for typed fields; the prose informs the model.

## Extensions

A SOUL extension is a separate Markdown file under:

```
identity/SOUL.d/
├── 10-household.md
├── 20-work.md
└── 99-experimental.md
```

Files are concatenated in alphabetical order to form the effective SOUL. This pattern lets profiles or apps contribute SOUL fragments without overwriting the user's primary file.

A SOUL extension declares its source:

```markdown
---
source: kiki:profiles/secops-engagement@1.0
description: Adds rules for engagement-mode behavior
---
```

The user can disable an extension by removing the file or marking it disabled in the SOUL.md frontmatter.

## What SOUL is for

- Communication style
- Boundaries (what Kiki should refuse or hedge)
- Voice and prosody defaults
- Language preferences
- Persona (warmth, humor)

What SOUL is NOT for:

- Who the user is — that's IDENTITY.md
- Settings (DND, theme) — that's USER.md
- Capabilities — those are managed by the gate, not by SOUL

## Token budget

SOUL goes into the working memory's identity section (~1k tokens). Long SOULs get truncated with a warning. Best practice: keep it tight.

## Editing flow

- **In-app editor**: a guided UX
- **Direct text edit**: file watcher reloads
- **Voice**: "Kiki, change your style to ..." → consent flow

System-initiated edits go through the consent flow (per `IDENTITY-FILES.md`).

## Reset

The user can reset SOUL to the default for their profile:

```
kiki memory soul reset
```

Archives current; creates fresh.

## Sharing

A user can export their SOUL as a Markdown file for sharing or backup:

```
kiki memory soul export > soul-backup.md
```

Importing requires consent flow (the user is committing to those style choices).

## Versioning

The git repo provides history; no separate semver. Extensions carry version metadata in their frontmatter for the source profile.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| TOML block parse error           | log; ignore that block;        |
|                                  | prose still loaded             |
| File missing                     | use profile default            |
| Extension declares unknown       | log; skip extension            |
| field                            |                                |

## Acceptance criteria

- [ ] SOUL.md loads into working memory
- [ ] Extensions concatenate in order
- [ ] TOML fields parse and apply
- [ ] Edits via voice run through consent
- [ ] Reset archives prior file
- [ ] Export/import work

## References

- `04-memory/IDENTITY-FILES.md`
- `04-memory/CONSENT-FLOW.md`
- `04-memory/WORKING-MEMORY.md`
- `06-sdk/SKILL-FORMAT.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
