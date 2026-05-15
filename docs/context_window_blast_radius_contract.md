# Codex Context Window And Blast Radius Contract

**Status:** Operating contract.
**Created:** 2026-05-13.
**Purpose:** Define how Codex should preserve intent, constrain blast radius,
and re-anchor after context loss while working on LyraOS.

**Manifesto relationship:** this is an operator/Codex execution contract. It is
subordinate to `MANIFESTO.md` and the Cortex product-research contracts. It does
not define product claims, research variables, or user-facing governance.

This contract exists because LyraOS work now spans architecture, runtime
identity, topology, exposure enforcement, browser behavior, and deployment
state. A smart assistant with a limited context window can be useful only if the
system does not depend on perfect conversational memory.

The architecture must defend itself when the operator is tired, distracted,
scaling, or absent.

## Core Principle

Coherent constraints improve execution. Missing context increases blast radius.

When context is partial, Codex must narrow scope, re-read durable sources, and
verify runtime reality before making or pushing changes.

Default stance:

- preserve kernel invariants,
- keep periphery pragmatic,
- reduce ambiguity more than complexity,
- prefer small reversible moves over broad speculative rewrites.

## Kernel Invariants

These rules are not optional during implementation:

- bearer/JWT is the runtime identity authority.
- request scope must resolve before product reads or writes.
- topology must be verified before browser verification is trusted.
- no browser verification means no push.
- output surfaces must be registered before render.
- user-facing emissions must go through the authorized emission path.
- frontend requests never override backend suppression.
- performance work must not skip registry, exposure, render-ack, or identity
  enforcement writes.
- no ports, hostnames, CORS policy, auth semantics, or production wires are
  changed unless the user explicitly asks and the change is verified live.

## Kernel Override Rule

Kernel invariants require an explicit named override. Implicit approval,
fatigue, urgency, or phrases like "just do it anyway" are not enough.

If Codex proposes or is asked to make a change that conflicts with a kernel
invariant, Codex must stop and name:

1. the invariant being overridden,
2. the concrete risk,
3. the smallest override scope,
4. the rollback path,
5. the verification gate.

The operator must then approve the override by name, for example:

```text
Approved override: public CORS origin change for local recovery only.
```

Without a named override, Codex must preserve the invariant or offer an
alternative implementation that does not weaken it.

## Context Re-Anchor Protocol

After compaction, interruption, long pause, or suspected context drift, Codex
must re-anchor before continuing.

Minimum re-anchor:

1. Read the newest user request.
2. Run `git status -sb`.
3. Read the relevant durable plan or execution log.
4. Check the latest commit with `git log -1 --oneline`.
5. Identify whether the current task is docs-only, frontend, backend, topology,
   auth, exposure, or deployment.
6. State the immediate scope before editing.

If the task touches auth, topology, exposure enforcement, output surfaces,
workers, or deployment, Codex must also identify the verification gate before
editing.

## Blast Radius Tiers

Use the smallest tier that satisfies the request.

| Tier | Scope | Examples | Required Gate |
| --- | --- | --- | --- |
| 0 | Docs-only | operating contract, wave log, architecture note | proofread + `git diff` |
| 1 | Single surface or helper | one frontend component, one backend helper | focused test or typecheck |
| 2 | One runtime path | one endpoint, one worker path, one UI tab | focused tests + browser/API smoke |
| 3 | Cross-layer kernel path | identity, topology, exposure emission, registry | focused tests + full affected CI + topology + alt-account smoke |
| 4 | Deployment/public wire | ports, hostnames, Cloudflare, CORS, auth provider URLs | explicit user confirmation + topology + browser smoke before push |

Escalation rule:

- If a fix requires moving up a tier, pause and name why.
- If a bug appears outside the current tier, document it separately unless it is
  blocking the current gate.
- If a failing gate reveals a wider invariant problem, reduce scope to the
  invariant and stop feature work.

## Context Window Failure Modes

Known risks:

- remembering an older plan after the user changed direction,
- continuing after compaction without reading the execution log,
- treating local tests as proof of public runtime behavior,
- bundling unrelated cleanup into a wave,
- broadening a narrow fix into adjacent governance work,
- optimizing performance by bypassing integrity writes,
- assuming `.org`, localhost, backend, and auth all point at the same reality.

Countermeasures:

- newest user request wins.
- durable docs beat chat memory.
- topology verification precedes browser verification.
- browser verification precedes push.
- CI is watched after push.
- unrelated dirty files are left alone.

## Wave Execution Discipline

For implementation waves:

1. Define the wave gate before code.
2. Make the smallest implementation that satisfies the gate.
3. Run focused tests.
4. Run full backend CI-equivalent if backend code changed.
5. Run topology verifier before browser smoke.
6. Browser smoke with alt accounts when user-facing behavior, auth, or routing
   changed.
7. Push only after browser verification.
8. Watch CI until pass or diagnose failure immediately.
9. Record meaningful incidents in the wave execution log.

The default alt-account smoke accounts are:

- `asabryhafez@gmail.com`
- `moriartyholmesberg@gmail.com`

These accounts are verification tools, not authorization shortcuts. Manual and
browser verification must still use the bearer/session path.

## Stop Conditions

Codex should stop and re-anchor instead of continuing when:

- the live public path disagrees with local assumptions,
- `git status` shows unexpected dirty files in the same area,
- auth, topology, CORS, or ports are implicated unexpectedly,
- browser verification fails after tests pass,
- CI fails after push,
- a requested change would weaken a kernel invariant,
- the task cannot be explained as a bounded blast-radius tier.

## Complexity Rule

Kernel complexity may grow only when:

- a recurring integrity failure exists,
- operational discipline proved insufficient,
- the new mechanism reduces ambiguity more than it increases cognitive load.

Preferred progression:

```text
manual discipline
  -> script
  -> CI
  -> runtime enforcement
```

Hard kernel, soft periphery.

Strictness scales with epistemic risk, not developer convenience.
