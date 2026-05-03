# Copilot Handoff Prompt

Use this as a full-repo handoff brief. Read the entire repository end to end before proposing or changing anything.

You are taking over Lyra Secretary mid-transition. Your job is to understand the project deeply, reconcile docs with code, identify the true current phase, and then redesign the plan for what must happen next.

## What To Do First

1. Read the philosophy documents, planning documents, architecture docs, audit docs, and any phase or manifesto files.
2. Read the backend and frontend code that implements the current behavior.
3. Cross-check the docs against the code and note where they agree, where they drift, and where the docs are stale.
4. Identify the exact plan that is currently running now, not the one that used to be running.
5. Produce a new plan based on the repo’s actual present state.

## What You Must Understand

This repo is not a generic productivity app. It is being shaped as a behavioral inference engine with productivity as the interaction surface.

Important themes to absorb:

- Lyra’s philosophy
- The measurement contract
- The trust contract
- The calibration doctrine
- The distinction between operator-only discovery and non-operator user-facing inference
- The difference between sensing signal and metabolizing signal
- The anti-hallucination stance in JARVIS
- The phase transition from sensor-heavy / cortex-light to sensor-rich / cortex-deep

## Repo-Wide Reading List

Read all relevant docs, not just the obvious ones. At minimum, inspect:

- `CLAUDE.md`
- `MANIFESTO.md`
- `README.md`
- `docs/building_phases.md`
- `docs/complexity_stress_test_2026_05_01.md`
- `docs/calibration_contract.md`
- `docs/data_utilization_inventory_2026_05_02.md`
- `docs/jarvis_hypothesis_log.md`
- `docs/voided_at_audit_verification.md`
- `docs/design_patterns/structural_investigation_rule.md`
- `docs/design_patterns/rules_vs_agency.md`
- `docs/do_not_add.md`
- `docs/phase_6_architecture_backlog.md`
- `docs/architecture.md`
- `docs/methodology.md`
- `docs/project_history.md`
- `docs/dogfood_findings_living.md`
- `docs/insight_mechanisms_post_retention.md`
- `docs/feedback_loops_closure_plan.md`
- any other doc that looks like a phase note, audit, plan, or decision log

Then cross-check the code:

- backend app structure
- API routes
- services
- database models
- migrations
- tests
- frontend surfaces
- JARVIS tools and agent prompt
- any reflection, calibration, or analytics code

## The Current Plan You Must Recognize

There is a live May 2 system transition plan in this repo. Your task is to determine its current true state from the docs and code, then update the plan from there.

At a minimum, understand:

- Phase 0 calibration doctrine
- Phase 1 data utilization inventory and sign-off
- Phase 2 JARVIS operator-only discovery
- Phase 3 inference engine only after the discovery log has real promoted/rejected evidence
- Phase 4 reflection surfaces and latency constraints
- Phase 5 dark-column retirement
- Phase 6 lightweight telemetry only for top implicit signals

Do not assume the pasted plan is fully correct. Verify it against the repository.

## What To Verify

You must determine:

1. What philosophy the operator is actually pursuing.
2. Which plan is the active one right now.
3. Which phase the repo is truly in.
4. Which docs are authoritative and which are stale.
5. Which code already exists for the plan.
6. Which parts of the plan are missing, partially implemented, or contradicted by code.
7. What the next highest-value work actually is.

## How To Report Back

When you finish, write a clear end-to-end summary that includes:

- the project philosophy in plain terms
- the active plan and current phase
- what docs are authoritative
- what docs are stale or contradictory
- what code already implements the plan
- what is missing
- what the revised next plan should be

Be direct. If the repo contradicts the plan, say so. If the plan is under-specified, fix it. If the next step should not be code yet, say that plainly.

## Operating Style

- Read before acting.
- Cross-check docs against code.
- Prefer the repo’s actual current state over any pasted narrative.
- Keep the operator’s trust contract intact.
- Do not invent data, claims, or progress.
- If something is only a hypothesis, label it as such.
- If a surface or signal is not actually computed in code, do not assume it exists.

## Output I Want

I want a redesigned plan that answers:

- what should be done now
- why that is the right next move
- what is explicitly out of scope
- what the next phase gate is
- what evidence would let the plan advance

Use the repository itself as the source of truth.
