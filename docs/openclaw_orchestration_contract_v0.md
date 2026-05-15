# OpenClaw Orchestration Contract v0

**Status:** Active operator-runtime contract.

**Purpose:** Define how OpenClaw is wired as the multi-agent orchestration
runtime for LyraOS operator work. This is not a product feature, a user-facing
surface, or a research signal.

This contract documents runtime governance only. It does not authorize new
Lyra schema, predictors, user prompts, exposure/adaptation inference, or
psychological claims.

---

## 1. Boundary

OpenClaw is an operator-only execution environment for LyraOS.

It may:

- decompose operator tasks
- run implementation agents
- run adversarial review agents
- preserve disagreement and uncertainty
- summarize local memory and provenance

It must not:

- become a non-operator product surface
- treat agent output as behavioral data
- create Lyra research labels
- replace Cortex clean-data profiles
- silently merge disagreement into consensus

The Lyra product/research boundary remains governed by
`docs/cortex_product_research_contract_v0.md`.

---

## 2. Transport And Auth Boundary
*Added: May 15, 2026.*

OpenClaw does not have independent authority to bypass LyraOS runtime identity,
request scoping, topology, or exposure rules.

Any OpenClaw-to-Lyra HTTP path that reads or mutates user data must use a
contracted authenticated path, such as a bearer/JWT user session or a future
operator service-token flow with explicit audit logging. Runtime HTTP requests
must not rely on `X-User-Id`; that header is test-only and is rejected as an
identity authority outside test contexts.

Direct Docker-network addresses such as `http://backend:8000` may describe
network reachability, not authorization. Any skill, runbook, or orchestration
that still presents direct backend calls as sufficient for task control is
legacy until it includes the real auth and topology contract.

---

## 3. Runtime Layers

| Layer | Runtime model | Role | Constraint |
| --- | --- | --- | --- |
| Execution | `openai-codex/gpt-5.5` | Implementation, code, system design execution | Does not perform epistemic validation |
| Structural adversary | `openai-codex/gpt-5.5` | Runtime feasibility, dependency, and implementation critique | Does not validate psychological truth |
| Exploration | `google/gemini-2.5-flash` | Hypothesis expansion, alternatives, missing perspectives | Must preserve uncertainty |
| Epistemic adversary | `google/gemini-2.5-flash` | Hidden assumptions, causal errors, narrative bias | Must report confidence and alternatives |
| Synthesis/adjudication | `nvidia/moonshotai/kimi-k2.6` | Final synthesis, compression, arbitration, structured output | Only layer allowed to arbitrate conflicts |
| Memory | local model preferred, Gemini fallback | Summarization and incremental state persistence | Must preserve provenance labels |

Kimi remains the OpenClaw default because the primary synthesis/adjudication
layer owns final compression. Codex is wired as a role-specific implementation
and structural-adversary model, not as the default arbiter.

Agent IDs and model IDs are separate namespaces. The canonical Codex-backed
execution agent is `lyra-implementation`; the canonical Codex-backed structural
review agent is `structural-adversary`. A `codex` agent ID may exist only as a
compatibility spawn target for tools that incorrectly use the model nickname as
an agent ID.

---

## 4. Required Pipeline

Every OpenClaw orchestration request should follow this sequence:

1. Intent parse: classify the task as `execution`, `research`, `hybrid`, or
   `synthesis`.
2. Task decomposition: split into atomic subtasks and dependencies.
3. Routing: Codex for execution, Gemini for exploration, Kimi for synthesis.
4. Parallel execution: agents work independently when dependencies allow it.
5. Structural adversary pass: Codex returns `PASS` or `FAIL`, structural
   failures, and correction suggestions.
6. Epistemic adversary pass: Gemini or Kimi returns confidence, challenged
   assumptions, alternative hypotheses, and uncertainty flags.
7. Conflict graph: contradictions are labeled `low`, `medium`, or `high`.
8. Arbitration: Kimi either resolves with justification or preserves unresolved
   interpretations.
9. Final synthesis: Kimi produces the structured result.

If any layer cannot run, the output must be marked partial and the missing
dependency must be explicit.

---

## 5. Invariants

- No silent merging of conflicting outputs.
- No hidden assumption propagation.
- No collapsing uncertainty into a single answer.
- No inference without marked confidence.
- Disagreement must be represented explicitly.
- Data labels must be one of `OBSERVED`, `DERIVED`, `INFERRED`, or `UNKNOWN`.
- `INFERRED` must never be converted into `OBSERVED`.
- `UNKNOWN` must remain explicit.

---

## 6. Required Output Sections

Every orchestration result must contain:

1. `FINAL RESULT`
2. `STRUCTURAL VALIDATION REPORT`
3. `EPISTEMIC VALIDATION REPORT`
4. `CONFLICT LOG`
5. `UNCERTAINTY MAP`
6. `NEXT ACTION SUGGESTION`

No section may be omitted. If no conflict exists, the conflict log must say so.

---

## 7. Implementation Status

As of 2026-05-09, the external OpenClaw runtime is running OpenClaw `2026.5.7`
and is wired with:

- default synthesis model: `nvidia/moonshotai/kimi-k2.6`
- Codex OAuth implementation model: `openai-codex/gpt-5.5`
- exploration model: `google/gemini-2.5-flash`
- role agents:
  - `lyra-implementation`
  - `structural-adversary`
  - `exploration-agent`
  - `epistemic-adversary`
  - `memory-agent`
  - `codex` (compatibility alias; prefer `lyra-implementation` for canonical
    execution routing)

Verification state:

- `openai-codex/gpt-5.5` is available through OpenAI Codex OAuth, not an API
  key.
- `agentId="codex"` is allowed as a compatibility spawn target after the
  2026-05-09 runtime patch.
- Kimi one-shot inference is verified through the gateway.
- Codex one-shot inference is verified through local OpenClaw execution.
- Codex cold-call latency exceeded the gateway one-shot helper's 120-second
  timeout during verification. This is a runtime latency constraint, not a
  failed authentication state.

The external OpenClaw runtime also contains a local copy of this contract at:

```text
/home/node/.openclaw/workspace/LYRA_ORCHESTRATION_CONTRACT.md
```

---

## 8. Manifesto Relationship

This contract refines the operator-only tooling boundary already stated in
`MANIFESTO.md`. It does not change Lyra's research variables, user-facing
claims, clean-data profiles, or product/research boundary.
