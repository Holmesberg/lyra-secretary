# Repository Instructions for Lyra Secretary

Use these instructions when working in this repository.

## Start Here

Read [`docs/README.md`](../docs/README.md) first. It maps active authority,
contracts, verification runbooks, historical docs, and parked ideas.

The current freeze-closure authority chain starts with:

- [`docs/AUTHORITY.md`](../docs/AUTHORITY.md)
- [`docs/current_transition_state.md`](../docs/current_transition_state.md)
- [`docs/single_authority_contract.md`](../docs/single_authority_contract.md)
- [`docs/operator_dashboard_contract.md`](../docs/operator_dashboard_contract.md)
- [`docs/runbooks/post_wave_dogfood_loop.md`](../docs/runbooks/post_wave_dogfood_loop.md)
- [`docs/registries/refactor_stabilization_ledger.md`](../docs/registries/refactor_stabilization_ledger.md)

`docs/archive/AGENT_HANDOFF.md` is historical onboarding context only. It is
not current implementation authority.

## Current Frame

The active work is freeze-closure and safe refactor:

```text
measurement forensics -> operator truth -> regression gates -> small safe seams
```

The objective of every wave is to reduce uncertainty before reducing
complexity. Complexity reduction is only performed when supported by
independent evidence, reversible seams, and mechanically enforced authority
boundaries.

Refactor without losing a single documented feature. Before changing a feature,
name the document or test that proves it exists. If a documented feature lacks
coverage, add characterization proof before refactoring it.

## Standing Freeze Rules

Freeze remains active. Do not add any of the following without explicit user
approval and a new plan:

- runtime AI synthesis;
- OpenClaw-to-product GPT wiring;
- new user-facing insight types;
- behavior-transition equations;
- causal pressure-return claims;
- productivity, focus, motivation, or avoidance scores;
- passive tracking;
- new provider adapters;
- schema migrations;
- new public behavioral claims;
- brand/domain/runtime-host migration.

Exposure doctrine is global: queue insertion is not exposure, delivery is not
exposure, browser render creates render truth, and dismissal, acknowledgement,
action, expiry, suppression, or `lost_unrendered` create terminal outcome
truth. Pending disappearance is not render proof.

Account roles are fixed:

- `LYRA_COOKIE_ALINASSERSABRY` is the operator account and must remain
  read-only.
- `LYRA_COOKIE_HOLMESBERG` is the mutable dogfood account and requires unique
  synthetic prefixes plus cleanup or void proof.

## Autonomy And Stop Gates

Codex may continue inside one declared seam across implementation, checks,
browser verification, CI watch, issue updates, and ledger updates.

Stop and ask before:

- merge, branch rollover, rebase, PR retarget, force-push after review, branch
  deletion, release, public deploy, or public restart;
- public mutable hosted dogfood;
- schema migration;
- production data repair, purge, irreversible deletion, or invasive row
  forensics;
- changing mutation, exposure, provider, claim, or clean-data authority owner;
- weakening operator/readiness/exposure denominators;
- accepting a known failing invariant as good enough;
- deleting or disabling a documented or user-facing feature;
- domain/rebrand/runtime-host migration;
- AI/OpenClaw runtime wiring;
- provider credential mutation beyond disposable/test accounts;
- mixed seams exceeding 8 files, about 300 code LOC, or unclear ownership;
- a seam requiring more than 2 CI fix/retry cycles without fresh
  classification;
- three consecutive cosmetic-only seams.

Adjacent fixes are allowed only when they block proof of the declared seam.
Adjacent discoveries that do not block the seam become issues and stay out of
scope.

## Seam Preflight

Before editing, declare:

- seam name;
- authority class;
- touched surfaces;
- documented behaviors touched;
- file, doc, or test proving those behaviors exist;
- expected user-visible behavior change;
- expected data/write behavior change;
- required proof;
- negative proof requirement, if any;
- stop condition;
- rollback path.

If a seam mixes product, verifier, topology, docs, CI/CD, or measurement
authority, explain why the mix is unavoidable before continuing.

## Git And Verification Hygiene

Start each seam from clean `git status`. Stage explicit paths only. Do not
commit `tmp/`, screenshots, logs, local databases, `.env` files, build output,
dependency folders, or generated cache artifacts unless explicitly asked.

Separate product, verifier, wrapper/ops, tests, and docs commits where
practical. Ledger may be in the same commit only for docs-only seams; otherwise
prefer a separate ledger commit.

For behavior-affecting seams:

- compare implementation against docs before editing;
- add or name characterization tests;
- run targeted tests plus `git diff --check`;
- run frontend build/typecheck for frontend seams;
- run backend targeted/full tests for backend/write seams;
- run operator read-only proof after mutable passes;
- run Holmesberg mutable proof when user-facing behavior changes;
- prove synthetic cleanup or record residue as a blocker;
- push and collect CI proof on the exact full SHA.

Evidence beats screenshots. Screenshots explain failures; proof comes from
backend state, exported evidence, operator invariants, and browser behavior.
Verifier bugs are first-class bugs and must be classified before assuming the
product is broken.

## Public Artifact Safety

Local verification must not mutate hosted-public frontend artifacts.
Hosted-public builds use isolated public artifacts. If artifact isolation is
not proven while hosted-public frontend is running, local frontend build/dev
verification must fail closed or stop for explicit approval.

Public deploy or restart requires explicit user approval. Restart scripts must
not report success if served build IDs mismatch the expected commit; classify
mismatch as deployment lag or deployment failure.
