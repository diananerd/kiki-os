---
id: curated-prompts
title: Curated Prompts
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - principles
  - harness-patterns
  - arbiter-classifier
  - evaluation
last_updated: 2026-04-29
---
# Curated Prompts

## Purpose

Specify how Kiki manages the small set of *system* prompts
that drive specialized model calls: the arbiter classifier,
the compaction summarizer, the search query refiner, the
memory-consent narrator, the tool-result minifier, etc.
These are versioned, reviewed, and treated as code.

User-authored prompts (skills, persona) are user data and
not the subject of this guide. This is about the prompts
*we* ship and own.

## Why versioning matters

Prompts encode behavior. A typo in a prompt can:

- Make the arbiter over-deny or under-deny
- Cause the compaction summarizer to drop key facts
- Trigger latent injection vulnerabilities

Treating prompts as immutable strings in a binary leaves
no review surface and no rollback. Treating them as code
gives:

- Code review on changes
- Eval gating (see `EVALUATION.md`)
- Rollback via the same mechanisms as any code change
- Easier debugging when behavior changes

## Layout

Curated prompts live under `/usr/share/kiki/prompts/`:

```
prompts/
├── arbiter/
│   ├── stage1-small.txt           v1.3.0
│   ├── stage2-large.txt           v1.2.0
│   └── README.md
├── compaction/
│   ├── summarizer.txt
│   └── tier4-archivist.txt
├── memory/
│   ├── consent-narrator.txt
│   ├── episodic-summarizer.txt
│   └── identity-extractor.txt
├── search/
│   ├── query-refiner.txt
│   └── result-ranker.txt
├── tool-result/
│   ├── shell-output-minifier.txt
│   └── webpage-extractor.txt
└── system/
    ├── agent-loop.txt              the main system prompt
    └── voice-loop.txt              voice-specific
```

Each file:

- Is plain text (or markdown for templates)
- Has a header comment with id, version, owner,
  last-updated
- Is the literal prompt sent to the model (no template
  surprises)

## Template expansion

Some prompts have placeholder fields filled at runtime:

```
{{user.name}}             user's preferred name
{{time.now}}               current local time
{{capabilities.list}}      tools available in this context
{{task.description}}       current task latch
```

Placeholders are documented in the file header. The
template engine is minimal (no Turing-complete
substitution); fields are typed and validated.

## Versioning

Each prompt has a semver in its header:

```
# kiki-prompt: arbiter/stage1-small
# version: 1.3.0
# owner: agentd
# last-updated: 2026-04-29
# eval-suite: tests/eval/arbiter
```

- Patch: typo fixes, clarifications without behavior
  change
- Minor: added clauses or new placeholder fields, but
  prior behavior preserved
- Major: semantic change (the arbiter is more strict / the
  compaction loses fewer facts / etc.)

Major changes require a PR with eval results showing the
intended behavior change and no unintended regressions.

## The audit trail

Every model call records the prompt id and version:

```
audit.entry {
  category: "model_call",
  prompt: "arbiter/stage1-small@1.3.0",
  model: "llama-prompt-guard-2-86m",
  ...
}
```

This makes it possible to investigate: "the arbiter let
this through; which prompt version was active?"

## The agent loop system prompt

The most important and most carefully managed:

`prompts/system/agent-loop.txt`

It contains:

- Identity & values (who Kiki is)
- The user latch (filled at runtime)
- Tool surface list (filled at runtime)
- Loop discipline (how to think about cycles, when to
  stop)
- Safety constraints (hardcoded restrictions reminded)
- Style (concise, structured, no preambles)

Changes to this prompt go through the full eval suite.
This is where many "small" wording changes have outsized
impact on quality.

## The arbiter prompts

`prompts/arbiter/stage1-small.txt`:

A short, fast classifier. Input minimization:

- Tool name + args (typed)
- A redacted summary of context (no full conversation)
- The user's intent expressed as a typed structure (not
  free text)

Output: a classification token (Allow / Deny / Uncertain /
Sanitize).

`prompts/arbiter/stage2-large.txt`:

Used only when stage 1 says Uncertain. Sees more context
but still less than the planner. Output: same enum + a
structured rationale stored in the audit log.

Both prompts are short and stable. Changes ship rarely.

## The compaction prompts

`prompts/compaction/summarizer.txt`:

A small model that summarizes a window of turns. The
prompt explicitly says:

- Preserve entities, decisions, unresolved questions
- Drop conversational filler
- Keep verbatim quotes the user explicitly asked for
- Do not invent

`prompts/compaction/tier4-archivist.txt`:

For folding tier-3 into tier-4. Even more aggressive
summarization with the same constraints.

Failures here cause silent quality regression; the eval
suite catches them with synthetic dialogues.

## The memory prompts

- `consent-narrator.txt`: explains what's about to be
  written to identity memory in user-readable form, for
  the consent flow
- `episodic-summarizer.txt`: per-session summary for the
  episodic store
- `identity-extractor.txt`: from a user message,
  extract candidate identity facts (still subject to the
  consent flow)

## The search prompts

- `query-refiner.txt`: turns a user's question into a
  search query
- `result-ranker.txt`: ranks search results by relevance
  to the original question

These are domain-agnostic templates; tools that need
domain-specific search write their own.

## The tool-result prompts

- `shell-output-minifier.txt`: takes a long shell output,
  returns a structured summary + tail
- `webpage-extractor.txt`: takes raw HTML/text and returns
  a structured representation

These run *as part of* a tool, not the planner. The
planner sees the minified output.

## Style guide for curated prompts

- **Direct.** Write what the model should do; don't beg.
- **Specific.** "Return one of: Allow, Deny, Uncertain"
  beats "decide carefully."
- **Structured output where possible.** A schema is
  cheaper than natural language to parse.
- **No "you are an AI" preambles.** Wasted tokens.
- **No "do not break character" guards.** They don't work
  and they signal we know we have a problem.
- **Short.** Fewer tokens = less latency, lower cost,
  less drift.

## Anti-patterns

- **Inline prompts in Rust strings.** Hard to review,
  hard to version. Keep them in files.
- **Prompts that depend on model-specific quirks.** When
  the model changes, the quirk is gone; the prompt
  breaks.
- **Untested prompt edits.** A 4-word change can shift
  arbiter classification rates by percent.
- **Sneaking new placeholders without doc.** Future
  callers fail to fill them; the model sees `{{empty}}`.

## Localization

System prompts are written in English; the model handles
multilingual conversation. User-visible templates (e.g.,
mailbox messages from the consent flow) are translated
separately and not curated as model prompts.

## Distribution

Prompts ship in the bootc base image, read-only at
runtime. Updates flow with sysext or full image bumps.
Local edits in `/etc/kiki/prompts/` override system
prompts for development; production images do not allow
this.

## Failure modes

| Failure                          | Response                       |
|----------------------------------|--------------------------------|
| Prompt file missing              | refuse to start; bootc rolls   |
|                                  | back                           |
| Placeholder not filled           | rendering fails; log; refuse   |
|                                  | the call                       |
| Template syntax error            | refuse; CI catches in normal   |
|                                  | path                           |
| Eval regression after edit       | block PR; require              |
|                                  | justification                  |

## References

- `00-foundations/PRINCIPLES.md`
- `03-runtime/AGENT-LOOP.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `03-runtime/INFERENCE-ROUTER.md`
- `04-memory/CONSENT-FLOW.md`
- `11-agentic-engineering/HARNESS-PATTERNS.md`
- `11-agentic-engineering/EVALUATION.md`
- `11-agentic-engineering/CONTEXT-ENGINEERING.md`
