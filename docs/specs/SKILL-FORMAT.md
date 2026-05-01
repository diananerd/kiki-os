---
id: skill-format
title: Skill Format
type: SPEC
status: draft
version: 0.0.0
implements: [skill-format]
depends_on:
  - procedural-memory
  - capability-taxonomy
depended_on_by:
  - publishing
last_updated: 2026-04-30
---
# Skill Format

## Purpose

Specify the file format for skills — Markdown documents with YAML/TOML frontmatter that act as procedural recipes the agent can invoke. Skills are user-authored or shipped by apps; they live in procedural memory.

## File layout

```
/var/lib/kiki/users/<uid>/memory/procedural/recipes/<name>.md
/var/lib/kiki/apps/<id>/recipes/<name>.md
```

User recipes take precedence over app recipes with the same id.

## Format

````markdown
---
id: morning-news
title: Morning News Brief
description: |
  When the user asks for "the news" or wakes up,
  fetch top headlines from preferred sources and summarize.
triggers:
  - intent: news.morning
  - phrase: "what's the news"
  - phrase: "give me a briefing"
inputs:
  preferred_sources:
    type: list
    default: ["nytimes.com", "elpais.com"]
  max_items:
    type: int
    default: 5
outputs:
  bullets:
    type: list
capabilities_required:
  - network.outbound.host:https://api.nytimes.com
  - network.outbound.host:https://elpais.com
  - tool:summarizer
embedding: bge-m3@1.5.0
last_updated: 2026-04-30
version: 1.2.0
authors:
  - "Diana"
license: "MIT"
---

# Morning News Brief

## Steps

1. Fetch headlines from each `preferred_sources` URL.
2. De-duplicate by title similarity (cosine > 0.85).
3. Rank by recency and source weight.
4. Take top `max_items`.
5. Summarize each in 1-2 sentences.
6. Return as bullets.

## Notes

- Skip paywalled articles.
- Prefer original-language sources for the user's region.
- If a source returns 5xx, fall back to the next one.
````

The frontmatter is machine-readable; the body is for the model and for users.

## Triggers

A skill activates when one of its triggers matches:

- **intent**: a structured intent identifier
- **phrase**: a literal or near-literal user phrase
- **schedule**: a cron-like time
- **event**: a system or app event (e.g., "calendar reminder fires")

Multiple triggers fire the same skill; the most specific wins.

## Inputs / outputs

Typed schema (`type: int | string | list | enum | ...`). Defaults are used if the user doesn't specify; the agent infers from context.

## Capabilities

Skills declare what they need; the agent verifies at activation. Missing capabilities filter the skill out (or prompt to grant).

## Body

The body is a Markdown document the model reads. Best practices:

- Numbered steps
- Clear notes
- No code in steps; refer to tools by name
- Mention the tools used and how to compose them

## Versioning

Semver in frontmatter. The procedural index uses version + last_updated for staleness checks.

## Discovery

Skills are searchable via:

- Trigger match (lexical)
- Vector similarity over description (bge-m3)
- Category browsing in the launcher

## Editing

- Direct file edit (the recipes/ directory is git-versioned)
- Voice: "Kiki, modify the morning-news recipe to ..."
- Settings UI for guided edits

## Sharing

Skills can be exported as Markdown files:

```
kiki recipe export morning-news > morning-news.md
kiki recipe import < morning-news.md
```

Importing runs the validation pipeline; capabilities must be available or grants requested.

## Authoring guidance

- Keep skills small; one purpose
- Prefer composing tools over hardcoding URLs
- Make parameters explicit
- Test with a few sample inputs (use `kiki recipe test`)

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Frontmatter parse error          | skip skill; log                |
| Required capability missing      | filter out; surface grant CTA  |
| Trigger conflict                 | most specific wins             |
| Output schema violated           | runtime error; agent surfaces  |

## Acceptance criteria

- [ ] Frontmatter validates against schema
- [ ] Triggers (phrase/intent/schedule/event) fire correctly
- [ ] Capabilities verified at activation
- [ ] Versioning + git history captured
- [ ] Export/import round-trips

## References

- `04-memory/PROCEDURAL-MEMORY.md`
- `04-memory/RETRIEVAL.md`
- `06-sdk/PUBLISHING.md`
- `10-security/CAPABILITY-TAXONOMY.md`
