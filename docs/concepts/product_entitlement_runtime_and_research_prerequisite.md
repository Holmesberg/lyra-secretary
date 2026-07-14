---
authority: concept-note
may_authorize_code: false
pricing_authority: none
runtime_authority: none
experiment_authority: none
schema_authority: none
status: prerequisite concept pending founder review
product_name: LyraOS
created: 2026-07-11
---

# Product Entitlement, Runtime Funding, Runtime Connection, And Research Assignment

This document prevents independent state machines from collapsing into one
`is_pro`, `ai_enabled`, or founder-account-backed flag.

It authorizes no pricing change, runtime connection, account linking, schema,
experiment, user-facing AI behavior, or marketing claim.

## Core Invariant

LyraOS must remain genuinely useful without any connected reasoning runtime.

The deterministic product loop must preserve:

```text
capture
-> clarify
-> pressure visibility
-> execution
-> correction
-> manual recovery
-> basic reflection
```

A future reasoning runtime may improve semantic assistance, hypothesis breadth,
context synthesis, recovery-option quality, or longitudinal interpretation. It
must not become necessary for task truth, timer reliability, basic planning,
basic recovery, correction, data ownership, export, deletion, exposure
accuracy, provenance correctness, consent, or basic privacy controls.

The complete repository-wide candidate catalogue, free-tier distillation path,
method-selection ladder, and explicit no-AI zones are documented in
`docs/concepts/ai_capability_completion_map.md`. That companion is
non-authorizing and does not decide packaging or price.

Advanced ledger visualizations may become paid. Correct exposure recording,
provenance, consent, deletion, and safety may not become premium features.

## Independent State Machines

### ProductEntitlement

Examples:

- `free`
- `pro`
- `research_preview`
- `research_preview_pro`
- `institution`

This controls product packaging and access, not evidence authority or runtime
truth.

`research_preview_pro` is a temporary cohort entitlement. It can expose the
same product packaging a future Pro plan may contain, but it is not a pricing
commitment, not a marketing claim, and not proof that reasoning-runtime access
belongs inside Pro forever.

### RuntimeFunding

Examples:

- `none`
- `founder_sponsored`
- `cohort_sponsored`
- `user_connected`
- `institution_sponsored`
- `platform_billed`

This describes who supplies or sponsors reasoning-runtime capacity. It does not
grant product entitlement, research enrollment, publication authority, or
permission to show AI-generated text.

For pre-alpha and the university wedge, `founder_sponsored` or
`cohort_sponsored` may describe a temporary bridge where LyraOS routes approved
research-preview work through a founder-managed adapter profile. That bridge is
operational custody only. It must not become product identity, permanent
architecture, public copy, or a hidden assumption that "Pro equals founder
runtime."

### RuntimeConnection

Examples:

- `none`
- `connected`
- `quota_exhausted`
- `expired`
- `revoked`
- `incompatible`
- `capability_changed`

This describes whether a user has an active external reasoning-runtime
connection. It does not imply paid LyraOS access, research enrollment, or
permission to show AI-generated text.

Runtime connection is intentionally separate from runtime funding. A user can
have no personal connection and still be eligible for a cohort-sponsored shadow
or visible preview, if a later approved protocol permits it.

### ResearchAssignment

Examples:

- `not_enrolled`
- `deterministic_baseline`
- `shadow_ai`
- `visible_ai_preview`
- `control`
- `withdrawn`
- `completed`

This controls research protocol state. It does not imply product entitlement,
runtime availability, or commercial eligibility.

## Example Combinations

A user may be:

- LyraOS free + connected runtime + not enrolled in research;
- research preview + no runtime funding + deterministic baseline arm;
- research-preview Pro + cohort-sponsored runtime + shadow AI assignment;
- research-preview Pro + cohort-sponsored runtime + visible AI preview;
- LyraOS pro + connected runtime + quota exhausted;
- institution user + shadow AI assignment + runtime unavailable;
- ordinary product user + no research assignment + deterministic-only product.

No implementation may collapse these combinations into a single flag.

## Research-Preview Pro Doctrine

Research-preview Pro exists to let a trusted cohort evaluate the full product
shape before LyraOS knows the final pricing, runtime-funding, or institution
model.

It may include:

- deterministic Pro-like workflow surfaces;
- higher product limits, if later authorized;
- cohort-sponsored shadow reasoning;
- cohort-sponsored visible reasoning preview, after separate approval;
- research instrumentation and exposure-complete proof.

It may not imply:

- that AI is a permanent Pro feature;
- that every Pro user receives founder-sponsored runtime;
- that the founder-managed adapter profile is the system's AI;
- that future users will skip their own connection or institution sponsorship;
- that research-preview findings are commercial product claims.

The phrase to preserve is:

```text
research-preview Pro with cohort-sponsored reasoning runtime
```

The phrases to avoid are:

```text
Ali's account powers LyraOS
Founder runtime is LyraOS AI
Pro means AI is always included
```

## Temporary Runtime Custody Boundary

Before user-connected or institution-sponsored runtime exists, a later approved
experiment may use a founder-managed adapter profile as temporary
cohort-sponsored custody.

That bridge requires these conceptual audit fields before implementation:

- `product_entitlement`: for example, `research_preview_pro`;
- `runtime_funding`: `founder_sponsored` or `cohort_sponsored`;
- `runtime_custodian`: founder-managed adapter profile;
- `runtime_connection`: active, unavailable, quota exhausted, expired, or
  revoked;
- `research_assignment`: deterministic baseline, shadow AI, visible AI preview,
  control, withdrawn, or completed;
- `subject_user`: the LyraOS user whose EvidencePacket is being processed;
- `consent_scope`: shadow only, visible preview, exportable, or withdrawn;
- `credential_boundary`: adapter-owned credentials, never LyraOS secrets;
- `isolation_mode`: per-subject context isolation and no cross-user memory;
- `migration_target`: `user_connected`, `institution_sponsored`, or
  `platform_billed`.

The founder-managed bridge must be easy to remove. It is a funding/custody
mode under `ReasoningRuntimeContract`, not a new product dependency.

## Runtime Epoch And Plan Transitions

Research-sensitive runtime changes must create explicit conceptual epochs
before any future implementation:

- runtime provider or adapter changed;
- model route or model version changed;
- authentication mode changed;
- plan capability changed;
- quota state changed;
- prompt/template family changed;
- reasoning configuration changed;
- policy version changed;
- major adapter version changed;
- user connected a different provider account.

Commercial paths may later allow explicit graceful fallback after approval.
Research-sensitive paths must fail closed or record a protocol deviation. No
silent runtime substitution is allowed.

## University Wedge Sequence

Stage U0: research readiness.

Stage U1: deterministic formative cohort, 20-30 users. Entitlement may be
`research_preview_pro`, runtime funding is `none`, and assignment is
`deterministic_baseline`. Purpose: break ontology assumptions, discover
usability failures, validate Pressure Map semantics, observe correction
behavior, identify missing states, and measure retention and workflow utility.
This is not an adaptive experiment.

Stage U2: shadow AI. Entitlement may remain `research_preview_pro`, runtime
funding may become `founder_sponsored` or `cohort_sponsored`, and assignment is
`shadow_ai`. Standardized EvidencePackets may be sent to an approved runtime,
but users do not see hypotheses. Measure heuristic-only hypotheses, AI-only
additions, agreement, disagreement, hallucinations, later user corrections, and
later observational support.

Stage U3: controlled visible augmentation. Entitlement may remain
`research_preview_pro`, runtime funding remains cohort-controlled, and
assignment becomes `visible_ai_preview`. Only after shadow evidence supports
it. Record exact exposure and downstream effects.

Stage U4: commercial beta. Only here begin testing paid conversion, plan
differentiation, runtime-connection demand, willingness to pay, institution
sponsorship, and retention by entitlement class.

This sequence prevents AI novelty from hiding basic product failures.

| Stage | Product entitlement | Runtime funding | Research assignment | User-visible AI |
| --- | --- | --- | --- | --- |
| U1 | `research_preview_pro` | `none` | `deterministic_baseline` | no |
| U2 | `research_preview_pro` | `founder_sponsored` or `cohort_sponsored` | `shadow_ai` | no |
| U3 | `research_preview_pro` | `founder_sponsored` or `cohort_sponsored` | `visible_ai_preview` | yes, if separately approved |
| U4 | `free`, `pro`, or `institution` | `user_connected`, `institution_sponsored`, or later approved billing | commercial or research-specific | depends on plan/protocol |

## Required Future Decisions

Before any implementation:

- pricing and access policy;
- research-preview Pro inclusion and limits;
- runtime funding and sponsorship policy;
- runtime adapter and auth feasibility;
- founder-managed bridge consent and sunset policy;
- consent and withdrawal UX;
- quota exhaustion behavior;
- revocation and disconnect semantics;
- research assignment authority;
- protocol-deviation handling;
- retention, export, and deletion behavior;
- user-facing disclosure;
- kill switch and pause authority.
