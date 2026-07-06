# Repository Instructions for Lyra Secretary

Use these instructions when working in this repository.

## Full brief for new agents

**Start here:** [`docs/AGENT_HANDOFF.md`](../docs/AGENT_HANDOFF.md) — comprehensive transition context, dual planning tracks, phase gates, file map, verification commands, and a checklist. This file is the short standing instruction set.

**Hard gates (do not skip):** [`MANIFESTO.md`](../MANIFESTO.md), [`docs/cortex_contract_v0.md`](../docs/cortex_contract_v0.md), [`docs/cortex_product_research_contract_v0.md`](../docs/cortex_product_research_contract_v0.md), and [`docs/deployment_architecture.md`](../docs/deployment_architecture.md).

## What This Repo Is

Lyra Secretary is not a generic productivity app. It is a behavioral inference system with productivity as the interaction surface. The project is currently in the May 2 transition from a sensor-heavy design toward a cortex-deep design.

The important idea is simple: the repo already collects a lot of signal. The next work is about metabolizing that signal correctly, not inventing new complexity.

## Read First

Before making changes, read:

- `docs/AGENT_HANDOFF.md` (handoff + gates)
- `MANIFESTO.md`
- `docs/building_phases.md`
- `docs/calibration_contract.md`
- `docs/cortex_contract_v0.md`
- `docs/openclaw_orchestration_contract_v0.md`
- `docs/data_utilization_inventory_2026_05_02.md`
- `docs/jarvis_hypothesis_log.md`
- `docs/complexity_stress_test_2026_05_01.md`
- `docs/design_patterns/structural_investigation_rule.md`
- `docs/design_patterns/rules_vs_agency.md`
- `docs/do_not_add.md`
- `docs/project_history.md`
- `docs/dogfood_findings_living.md`

Then cross-check those docs against the backend and frontend code.

## Current Plan

The active plan is the 2026-05-02 system transition:

1. Calibration doctrine
2. Data utilization inventory and sign-off
3. JARVIS operator-only discovery
4. Inference engine only after real promoted/rejected hypotheses exist
5. Reflection surfaces with latency constraints
6. Dark-column retirement
7. Lightweight telemetry only for the highest-value implicit signals

Do not assume an older phase doc is current if the May 2 docs or code say otherwise. Product roadmap lives in `docs/building_phases.md`; reconcile both — see `docs/AGENT_HANDOFF.md` §2.

## Ground Rules

- Prefer the repository’s actual state over any pasted narrative.
- `MANIFESTO.md` is the highest-priority governance document. Any change that
  touches research doctrine, ontology, measurement semantics, pre-registered
  analysis rules, product/research boundary, or long-term architecture must
  either update `MANIFESTO.md` or explicitly document why no manifesto update is
  needed.
- Do not invent data, signals, or phase progress.
- If a signal is not computed in code, say so.
- If a doc is stale, note the drift instead of silently following it.
- Before touching Cortex, behavioral metrics, clean-data filters, or
  inference-adjacent analytics, obey `docs/cortex_contract_v0.md`.
- Before changing the user interaction surface for research reasons, obey
  `docs/cortex_product_research_contract_v0.md`.
- Always document changes that touch measurement, inference, clean-data
  profiles, provenance, topology, or user-facing claims.
- Never infer missing semantics; mark `unknown`.
- Preserve `unknown`; never silently convert it into neutral, bounded, zero,
  average, clean, or no-exposure.
- Keep observed, derived, and latent layers separate.
- Keep operator-only discovery separate from non-operator user-facing inference.
- Cortex is read-only and must not mutate ORM, Redis, external sync, or
  notification state.
- Derived metrics must be functions of raw observables unless the Cortex
  contract names the transformation.
- Do not continue broad structural refactors before characterization tests,
  dependency DAG checks, centralized clean-data profiles, unknown-propagation
  tests, evaluation-version checks, and read-only Cortex checks exist.
- Do not add required user inputs for research convenience. New user-burden
  variables require explicit contract amendment with identifiability gain,
  retention risk, clean-data impact, burden offset, and sunset criteria.
- Optimize for information gain per unit user friction; passive/internal signal
  expansion is preferred over expanding the user input surface.
- Prepare completed repository changes as structured commit buckets, then ask
  the operator for explicit confirmation before any commit, push, pull, merge,
  rebase, stash, or branch switch.
- Stage explicit paths only. Never bundle unrelated dirty-worktree files.
- Keep docs either active in `docs/` or intentionally archived under
  `archive/`; do not create ambiguous documentation sediment.
- Archived database SQL migrations named `migration_NNN...` belong in
  `archive/migrations/`. Do not move Alembic Python version scripts there;
  active Alembic revisions remain in `backend/alembic/versions/`.
- Respect the calibration contract: comparative context before input, confidence tiers, low-confidence retreat, warm tone, and no unnecessary latency.
- Respect the structural investigation rule before touching measurement, data flow, or research-relevant fields.

## Git Hygiene Enforcement

These rules are mandatory for every implementation iteration. Do not rely on
chat context or memory.

Before coding:

- Run `git status --short --branch`.
- Identify the branch and whether the worktree is clean.
- Name the intended task scope and the files/directories likely to change.
- If unrelated dirty files exist, leave them alone and report them separately.

Branch cadence:

- A new wave cycle gets a new branch. Example: a bug-closure cycle covering
  Waves 1-9 should use one coherent cycle branch.
- Do not create a new branch for every wave, subwave, browser-verification
  pass, CI fix, documentation update, or review correction inside the same
  cycle.
- Create a separate branch only when starting a new wave cycle or a truly
  separate failure domain/release train, such as urgent ops recovery while a
  product wave is in progress.
- Same-cycle contract failures, CI fixes, verification notes, and cleanup stay
  on the same branch until that cycle checkpoint is merged.

Before any commit or push:

- Run `./scripts/git_hygiene_summary.ps1 -ForPush -Paths <task-scoped paths>`.
- Stage explicit paths only.
- Do not stage or commit `tmp/`, screenshots, logs, local databases, `.env`
  files, build output, dependency folders, or generated cache artifacts unless
  the operator explicitly asks for those artifacts to be versioned.
- Run targeted tests for every touched area.
- Run broader CI-equivalent tests when the touched surface is shared,
  measurement-related, topology-related, or user-facing.
- For product-facing changes, run browser verification and save screenshots
  under repo-local `tmp/` only. Keep those screenshots local unless explicitly
  asked to version them.

After any push:

- Check the PR checks in GitHub.
- On wave branches without automatic CI, manually dispatch the CI workflow or
  record `no_workflow_ran`/`no_matching_run_for_head` with
  `scripts/collect_github_ci_cd_proof.ps1`.
- Capture the full pushed head SHA with `(git rev-parse HEAD).Trim()` and pass
  that full value to `collect_github_ci_cd_proof.ps1 -HeadSha`. Do not pass the
  seven-character display SHA; GitHub Actions reports full `headSha` values and
  short SHAs can create false `no_matching_run_for_head` proof artifacts.
- Treat `no_pr` as an explicit CI/CD state, not as proof failure by itself.
- Report actual CI status; do not infer success from local tests.
- If CI fails, inspect the failing job log and fix the contract failure before
  proceeding.

Before merge:

- Run `./scripts/git_hygiene_summary.ps1 -ForMerge -BaseRef origin/main`.
- Confirm the PR is mergeable, CI is green, and browser/user verification is
  complete where required.
- Confirm no accidental local artifacts are present in the PR diff.
- Confirm Alembic revision ordering if migrations changed.
- Do not merge a large wave-cycle branch while starting the next cycle on the
  same branch; merge the coherent checkpoint first, then branch the next cycle.

Every final implementation report must include:

```text
Git hygiene:
- branch:
- worktree:
- committed files:
- tests:
- browser verification:
- CI:
- artifacts intentionally kept:
- artifacts left local only:
- merge risk:
```

## Backend Rules

- Follow `services/task_manager.py` and `services/state_machine.py` for task lifecycle changes.
- Keep multi-user isolation tests updated for any write-path change.
- Use the existing JARVIS tools and prompt structure; do not broaden them casually.
- If you touch inference or reflection behavior, verify against `docs/calibration_contract.md`.
- Keep writes centralized and invariant-preserving.

## Frontend Rules

- Reuse existing surfaces when possible.
- Avoid adding new dashboards or extra round trips when a surface can read prefetched data.
- Keep reflection text calm, factual, and confidence-bounded.
- Preserve the current UX direction rather than redesigning around generic patterns.

## What Copilot Should Optimize For

- Understanding the real philosophy of the repo
- Reconciled docs and code
- The current phase and current gate
- A new plan that reflects the repo’s present state
- Small, safe, high-leverage changes

## What Copilot Should Avoid

- Hallucinating behavior from coverage labels alone
- Treating broad signal categories as evidence for specific slices that are not computed
- Rebuilding systems that already exist
- Expanding scope just because the repository is rich in data and docs
- Violating operator-only boundaries
