---
id: procedural-memory
title: Procedural Memory
type: SPEC
status: draft
version: 0.0.0
implements: [procedural-memory]
depends_on:
  - memory-architecture
  - capability-gate
depended_on_by:
  - agent-bundle
  - dreaming
  - pruning
  - retrieval
  - skill-format
last_updated: 2026-04-30
---
# Procedural Memory

## Purpose

Specify the layer that holds learned how-to recipes — small, executable patterns the agent (and the user) build up over time: "when the user asks for the news, fetch from these sources and summarize in 3 bullets," "to make coffee, ..." Procedural memory is the user's installed *skills* in the Claude-Code sense: human-authored or system-discovered, version-controlled, retrievable.

## Why a separate layer

A how-to recipe is not a fact about the world; it is a parameterized routine. Mixing it with semantic facts confuses retrieval and update semantics. Treating it as a first-class layer also lets users edit recipes by hand — they are TOML+Markdown files in a directory.

## Storage

```
/var/lib/kiki/users/<uid>/memory/procedural/
├── recipes/
│   ├── morning-news.md
│   ├── make-coffee.md
│   └── plan-trip.md
├── index.sqlite          # sqlite-vec sidecar
└── .git/                 # version-controlled
```

The recipe files are the source of truth. `index.sqlite` is a derived index for vector retrieval (using `sqlite-vec`).

## Recipe format

A recipe is a Markdown file with TOML frontmatter:

```markdown
---
id: morning-news
title: Morning News Brief
description: |
  When the user asks for "the news" or wakes up,
  fetch headlines from preferred sources and summarize.
triggers:
  - intent: news.morning
  - phrase: "what's the news"
  - phrase: "morning briefing"
inputs:
  preferred_sources: list
  max_items: int
outputs:
  bullets: list
capabilities_required:
  - network.outbound.host:https://api.newssource.example
  - tool:summarizer
embedding: bge-m3@1.5.0
last_updated: 2026-04-29
---

# Morning News Brief

## Steps

1. Fetch headlines from each `preferred_source`.
2. De-duplicate across sources by article title similarity.
3. Rank by recency and source weight.
4. Take top `max_items`.
5. Summarize each in 1-2 sentences.
6. Return as bullets.

## Notes

- Skip paywalled articles.
- Prefer original-language sources for the user's region.
```

The frontmatter is machine-readable; the body is for the model and for users editing.

## Retrieval

Procedural memory is searched at agent loop start when a user message arrives. Patterns:

- **Trigger match**: explicit `triggers` (intents, phrases) match the user input
- **Semantic similarity**: bge-m3 embedding of the user input vs. embeddings of each recipe
- **Capability filter**: only recipes whose required capabilities are granted in the current context

Top matches are loaded into working memory's `tools` section as activated recipes.

## Authoring

Recipes can be authored by:

- The user (Markdown editor; place a file under `recipes/`)
- The agent itself (after consolidation; see `DREAMING.md`)
- An app (recipe shipped with the app's manifest; installed under `apps/<app>/recipes/`)

User-authored recipes always take precedence over system-suggested ones with the same id.

## Versioning

The directory is a git repo. Every change is a commit:

```
feat(recipes): add weekend-meal-plan
fix(recipes): morning-news source fallback
```

git history gives provenance, rollback, and diffability.

## Capability scoping

Recipes declare `capabilities_required`. At activation, the gate verifies the current actor has those capabilities; recipes whose capabilities are missing are filtered out (or, if the user can grant them, surfaced as "this recipe needs X capability").

## sqlite-vec sidecar

```
table: recipes
  id           TEXT PRIMARY KEY
  embedding    BLOB        # 1024-d float32, compressed
  title        TEXT
  description  TEXT
  trigger_keys TEXT        # joined for filtering

vec0 virtual table:
  recipes_embedding(embedding FLOAT[1024])
```

sqlite-vec gives us ANN search without an extra service. The sidecar is regenerated when a recipe file changes (file watcher).

## Discovery from conversations

Dreaming consolidation can detect recurring patterns ("user always asks X then Y") and *propose* a recipe. The proposal goes to the user for review (it's not auto-installed; recipes are like skills, the user owns them). See `DREAMING.md`.

## Per-app recipes

Apps may ship recipes in their bundle:

```
/var/lib/kiki/apps/<app>/recipes/
```

These are read-only (managed by the app). The user can fork them to their own directory.

## Capabilities

```
agent.memory.read.procedural
agent.memory.write.procedural
agent.recipes.author              # higher: writing user-level recipes
agent.recipes.install             # installing recipes from apps
```

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Recipe parse error               | log; skip that recipe;         |
|                                  | surface to user                |
| Required capability missing      | filter out; suggest grant if   |
|                                  | applicable                     |
| Index out of sync                | rebuild from files             |
| git repo corrupt                 | restore from snapshot          |

## Performance

- Trigger match (lexical): <2ms
- Semantic top-K: <10ms
- Recipe file load + parse: <5ms

## Acceptance criteria

- [ ] Recipes in `recipes/` are loaded and indexed
- [ ] Trigger and semantic retrieval both work
- [ ] git history captures changes
- [ ] User can edit a recipe and see it reflected
- [ ] App-shipped recipes coexist with user-authored

## References

- `04-memory/MEMORY-ARCHITECTURE.md`
- `04-memory/RETRIEVAL.md`
- `04-memory/DREAMING.md`
- `06-sdk/SKILL-FORMAT.md`
- `10-security/CAPABILITY-TAXONOMY.md`
