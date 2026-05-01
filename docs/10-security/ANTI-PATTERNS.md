---
id: anti-patterns
title: Anti-Patterns
type: GUIDE
status: draft
version: 0.0.0
depends_on:
  - paradigm
  - principles
  - threat-model
  - capability-taxonomy
depended_on_by: []
last_updated: 2026-04-29
---
# Anti-Patterns

This document enumerates patterns Kiki OS rejects by structure, with the reason and the structural defense. Use this as a reference when reviewing proposals.

## The lethal trifecta

**Pattern.** A tool that simultaneously: accesses private data, ingests untrusted content, and communicates externally. Without specific defenses, prompt injection in the untrusted content can cause exfiltration of private data via the external comm.

**Defense.** CaMeL pattern (`10-security/CAMEL-PATTERN.md`): split planner / quarantined parser. Tools declare `risk_class: trifecta` to opt in. The execution engine in `policyd` applies the pattern.

## Cross-agent privilege escalation

**Pattern.** A compromised agent (e.g., GitHub Copilot) writes to a config file (e.g., `~/.mcp.json` or `CLAUDE.md`). The next agent (Claude Code) loads the config, picks up an attacker-controlled MCP server, executes malicious code. Kill chain.

**Defense.** Per-agent config namespacing. Kiki places agent configs in `/var/lib/kiki/users/<u>/agents/<id>/config/` with strict per-agent ownership. Cross-agent config writes require a capability the gate denies by default. `policyd` audits any cross-agent config access.

## Sandbox escape via composition

**Pattern.** An agent is denied a specific tool call (e.g., `chmod +x`). The agent retries via another tool (`bash` directly), or composes operations (download → chmod → execute). Each individual call passes the gate; the composition exceeds intent.

**Defense.** Treat permission denial as **terminal**, not feedback. When `policyd` denies a tool call, the agent receives `{ blocked: true, terminal: true }` and the result of the tool itself is not delivered. Semantic similarity detection: subsequent tool calls similar in intent to a recently-denied one are also denied or escalated to human prompt. Detail in `03-runtime/CAPABILITY-GATE.md`.

## Tool catalog enumeration

**Pattern.** All installed tools are enumerated in the system prompt. Above ~10 tools, agents lose 2–6× efficiency. At 50+ tools, the catalog itself eats 5–7% of context before the user message.

**Defense.** Tool catalog cap: agent sees only ~8–10 core tools + a `tools.search(query)` meta-tool. Lazy schema injection: full schemas loaded on demand. `toolregistry` exposes search; the agent narrows.

## Cache thrashing

**Pattern.** Feature flags or system prompts mutate within a session. The LLM provider's prefix cache invalidates. Cost spikes; latency increases.

**Defense.** Sticky cache discipline. `inferenced` declares a sentinel boundary between cacheable system prompt and dynamic suffix. Tool catalog ordered deterministically. 14 cache-invalidating fields tracked. Hit rate observable in agentui.

## Implicit trust on installed software

**Pattern.** An app installed once is implicitly trusted forever. Updates apply silently. A maintainer's compromise lets attackers ship to all users.

**Defense.** Per-update cosign verification. Key rotation surfaces a prompt to the user. Sigstore witness submission opt-in for non-repudiation. `policyd` records every verification outcome in the audit log.

## Apps controlling layout globally

**Pattern.** An app declares "I am full-screen" or "hide the status bar" or "modal-blocking on top of everything." Apps fight for user attention; the user cannot control the global layout.

**Defense.** Apps emit `BlockSpec` declaring intent (size hint, content). `agentui` decides where blocks appear. Apps cannot direct global layout. The compositor (cage) does not allow apps to influence layout outside their assigned area.

## App-to-app direct communication

**Pattern.** Apps connect to each other directly via IPC or shared memory, exchange data without the agent or capability gate as mediator.

**Defense.** Architectural isolation: each app in its own container with its own network namespace. No shared memory. The only channel an app has is its Cap'n Proto socket to `agentd`. App-to-app data flow goes through the agent, mediated by the capability gate.

## Free-form drag-and-drop between apps

**Pattern.** User drags a file from one app to another. The OS facilitates direct transfer, including capabilities the user did not explicitly grant.

**Defense.** No drag-and-drop between apps as a first-class concept. Selection is published to `focusbus`; the agent reads selection state and routes intent. The user says "send this to X"; the agent calls X's tool with the selection. Mediated.

## User-facing package manager

**Pattern.** apt/dnf/pacman exposed to the user. Linux conventions creep in. Users `sudo apt install` something that breaks the appliance shape.

**Defense.** No user-facing package manager. apt/dnf are not in the user surface. `agentctl` is the only management tool, and it is OCI-native (no parallel apt/dnf track). See `14-rfcs/0005-no-package-manager-user-facing.md`.

## Forking upstream packages

**Pattern.** We need a fix in the upstream kernel or systemd. We fork it and maintain our own version. Maintenance burden grows; security backporting becomes our problem.

**Defense.** No forking. Fixes go upstream. If upstream rejects or delays, we document the gap and consider alternative paths (different upstream, different approach), not a fork.

## Treating MCP as a trust boundary

**Pattern.** MCP servers' identity claims are trusted. Tool descriptions in MCP are taken as authoritative. Capability decisions delegated to MCP.

**Defense.** MCP is wire format only. Trust comes from cosign signatures on the OCI artifact carrying the MCP server. `toolregistry` validates signatures, applies the capability gate, audits invocations. MCP is the protocol; trust is layered above.

## Confused-deputy via agent prose

**Pattern.** The arbiter classifier (or any gate-side LLM) sees the agent's reasoning prose. Prompt injection in the user's request causes the agent to write prose that convinces the gate.

**Defense.** Input minimization. The arbiter classifier sees only `(user_prompt, tool_call_descriptor)`. The agent's prose is never input to the gate. Detail in `03-runtime/ARBITER-CLASSIFIER.md`.

## Multi-agent by default

**Pattern.** Tasks are decomposed into multiple agents reflexively. Cost amplifies (Anthropic published 4× tokens for single-agent, 15× for multi-agent). Marginal benefit shrinks above 45% baseline single-agent accuracy.

**Defense.** Single-agent is the default. Multi-agent requires the `agent.multi_agent` capability and a Profile declaring `breadth_first: true`. agentd alerts the user when multi-agent token usage exceeds 5× the single-agent baseline.

## Coordinator with tool access

**Pattern.** A Coordinator agent both orchestrates subagents AND executes tools. The coordinator becomes an attack surface: prompt injection in any subagent's output can manipulate the coordinator's tool calls.

**Defense.** Coordinator and Worker pattern with strict separation. Coordinator can only spawn workers and read summaries. Workers (one per subtask) execute tools. Worker journals are sidechain JSONL — never merged into Coordinator's context.

## Subagents inheriting parent capabilities

**Pattern.** A subagent inherits all parent capabilities. A manipulated subagent has full parent access.

**Defense.** Capability scoping. The parent declares a subset of its capabilities for the subagent. Workers receive ≤ parent's capabilities. Even a fully compromised subagent cannot exceed its scope.

## Identity files modified outside consent flow

**Pattern.** A buggy app or compromised model writes directly to SOUL.md or USER.md. Agent identity drifts; the user has no awareness.

**Defense.** Identity files are write-only-via-consent-flow. Filesystem permissions deny direct writes. A built-in `BeforeMemoryWrite(identity)` hook denies bypass. The runtime invariants are enforced regardless of identity content.

## Sensitive content in audit log payloads

**Pattern.** The audit log embeds full content of sensitive operations. Sharing audit logs for diagnostics leaks user data.

**Defense.** Audit log payloads contain references (file path, memory ID) for Sensitive content; the content is not embedded. HighlySensitive content has even references redacted.

## OS image with writable root

**Pattern.** `/usr` is writable. Updates apply by copying files. The deployed system can drift from any signed image.

**Defense.** `/usr` is read-only and dm-verity-protected. Any write fails with EROFS. Updates deploy a new image atomically. There is no per-package update path for the base.

## Agent operating apps via screen pixels

**Pattern.** The agent uses a "computer use" approach, taking screenshots and clicking. Brittle, slow, hard to audit.

**Defense.** Apps expose tools via Cap'n Proto. The agent operates apps semantically through tool calls. Apps emit blocks declaratively; the agent doesn't simulate user input.

## Implicit cross-workspace data flow

**Pattern.** Workspaces share memory by default. Sensitive content from one workspace leaks into another.

**Defense.** Workspaces are isolated by default. Memory namespaces are per-user with workspace tags; cross-workspace queries require explicit parameters. Profile declares scope (per-workspace, shared-singleton). The agent in one workspace cannot read another workspace's working memory without the user's explicit handoff.

## Hardcoded restrictions weakened by configuration

**Pattern.** A configuration flag disables a hardcoded restriction. "Power user mode" turns off safeguards.

**Defense.** Hardcoded restrictions are enforced in code, not configuration. There is no flag to disable them. Users wanting different behavior can fork the OS — explicitly stated in the documentation.

## References

- `00-foundations/PARADIGM.md`
- `00-foundations/PRINCIPLES.md`
- `00-foundations/DESIGN-PHILOSOPHY.md`
- `01-architecture/THREAT-MODEL.md`
- `10-security/CAPABILITY-TAXONOMY.md`
- `10-security/HARDCODED-RESTRICTIONS.md`
- `10-security/CAMEL-PATTERN.md`
- `11-agentic-engineering/HARNESS-PATTERNS.md`
- `11-agentic-engineering/PROMPT-INJECTION-DEFENSE.md`
