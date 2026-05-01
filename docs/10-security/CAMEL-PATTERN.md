---
id: camel-pattern
title: CaMeL Pattern (Trifecta Tools)
type: DESIGN
status: draft
version: 0.0.0
depends_on:
  - threat-model
  - capability-gate
depended_on_by:
  - prompt-injection-defense
last_updated: 2026-04-30
---
# CaMeL Pattern (Trifecta Tools)

## Problem

A class of agentic tools has the "lethal trifecta" property: they touch private data, untrusted content, and external communication simultaneously. Examples:

- A tool that fetches a webpage (untrusted content), reads the user's email (private data), and sends a summary to Slack (external comms).
- A tool that imports a document (untrusted), updates the user's calendar (private), and emails a confirmation (external).

Without specific defenses, prompt injection in the untrusted content can hijack the agent: instructions in the webpage can manipulate the agent into exfiltrating private data via the external comm path.

The standard agent loop, even with strong capability gating, is not sufficient because the agent's reasoning itself becomes the injection vector.

## Constraints

- Defense must work even if the agent's reasoning is influenced by the untrusted content.
- Defense must not require the agent to "be smart enough" to detect injection.
- Tools must declare their risk class so the gate can apply the pattern.
- The pattern must compose with the existing capability gate and arbiter classifier.

## Decision

For tools declared `risk_class: trifecta`, Kiki applies the **CaMeL pattern** (Capabilities for Mission-critical Execution with LLMs, DeepMind/ETH 2025):

```
USER REQUEST
    ↓
PRIVILEGED PLANNER (LLM)
   sees only the user request
   produces a plan as code (typed operations)
   never sees untrusted content
    ↓
PLAN (typed, structured)
    ↓
EXECUTION ENGINE
   for each operation:
     if operation involves untrusted content:
        invoke QUARANTINED PARSER
     execute as a sequence of typed calls
    ↓
QUARANTINED PARSER (LLM)
   parses untrusted content into typed fields
   CANNOT call tools
   CANNOT make decisions
   only extracts structured data
    ↓
TYPED FIELDS
    ↓
TOOL CALLS (with capability gate as usual)
```

The privileged planner LLM sees only what the user said. It writes a plan in a typed DSL: "fetch this URL → parse it → write fields a, b, c to memory". The parser LLM is given the untrusted content and a schema; it returns typed fields. It is sandboxed: it cannot make decisions or invoke tools. Capabilities ride with values; policies enforce data flow integrity.

This separates planning (sees user, can call tools) from parsing (sees content, cannot call tools).

## Rationale

### Why two LLMs

- The planner is influenced only by the user. Its plan cannot be derailed by untrusted content because it never sees the content.
- The parser is influenced by the untrusted content but cannot act on it. The worst the parser can do is extract weird fields, which the typed schema constrains.
- The execution engine is deterministic. It applies the gate to each typed operation.

### Why not just trust the agent?

Production data shows that prompt injection succeeds against single-LLM agentic systems at non-trivial rates (AgentDojo: 30–60% ASR depending on defenses). CaMeL achieves 77% utility with provable security on AgentDojo.

The cost: two LLM calls per trifecta operation (plan + parse) instead of one. We accept this cost for tools that touch the trifecta.

### When does CaMeL apply

A tool has `risk_class: trifecta` when its Profile declares it. Profile authors are responsible for honest declaration. Examples:

- A web-fetcher that returns content into the agent's context: yes.
- An email reader that returns email bodies: depends on whether the agent will summarize-and-send-elsewhere, often yes.
- A simple calendar event creator: typically no (no untrusted content).

`risk_class` defaults to `standard`. Maintainers explicitly mark trifecta tools.

## Implementation

The execution engine is part of `policyd`:

```rust
pub fn execute_trifecta(plan: TypedPlan, untrusted_inputs: HashMap<Slot, UntrustedContent>) -> Result<Outcome> {
    let mut typed_fields = HashMap::new();
    for op in plan.ops {
        match op {
            Op::Parse { content_ref, schema, output_slot } => {
                let content = untrusted_inputs[content_ref];
                let typed = call_quarantined_parser(content, schema)?;
                typed_fields.insert(output_slot, typed);
            }
            Op::Call { tool, args_from_slots, capability } => {
                gate.check(tool, capability)?;
                let args = resolve_args(args_from_slots, &typed_fields);
                tool_dispatch(tool, args)?;
            }
            // ...
        }
    }
}
```

The planner produces `TypedPlan`. The parser is a separate model invocation with `tools=[]`.

## Consequences

### Positive

- Trifecta tools are auditable: every typed operation is logged.
- Prompt injection in untrusted content cannot escape the parser sandbox.
- Provable data-flow integrity for high-stakes tools.
- Composes with the existing capability gate and arbiter classifier.

### Negative

- 2x LLM cost for trifecta operations.
- Extra latency: typically +200–500ms per operation.
- Requires Profile authors to identify and declare trifecta risk class accurately.
- The DSL for the typed plan is a new surface to specify and version.

## Alternatives considered

- **Trust the single agent + arbiter classifier alone.** Rejected because production data shows prompt injection succeeds at non-trivial rates against single-LLM systems even with classifier gating.
- **Disallow trifecta tools entirely.** Rejected because such tools are useful (web search, email summarization, etc.) and users would seek them anyway.
- **Run the parser as a non-LLM rule-based extractor.** Rejected because the input space is too varied; rules are brittle.

## References

- `01-architecture/THREAT-MODEL.md` (A7 — Agent manipulator)
- `03-runtime/CAPABILITY-GATE.md`
- `03-runtime/ARBITER-CLASSIFIER.md`
- `06-sdk/PROFILE-OCI-FORMAT.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
- `14-rfcs/0038-camel-trifecta-isolation.md`
- arXiv 2503.18813 (CaMeL paper, DeepMind/ETH)
## Graph links

[[THREAT-MODEL]]  [[CAPABILITY-GATE]]
