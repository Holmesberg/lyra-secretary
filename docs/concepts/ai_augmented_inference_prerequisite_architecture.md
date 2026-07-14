# AI-Augmented Inference Prerequisite Architecture

---
authority: concept-note
may_authorize_code: false
runtime_owner: none
status: prerequisite architecture pending founder review
product_name: LyraOS
rebrand_authority: none
schema_authority: none
public_api_authority: none
required_review_sequence:
  - GPT-5.6 architectural synthesis
  - founder decision
approval_status: not_approved
approved_by: null
approval_decision_id: null
approved_scope: none
draft_review_date: 2026-07-11
---

## Hard Stop

This document is a foundation survey, not permission to build the adaptive
system.

After producing or reviewing this document:

- do not add a direct model-provider client or API-key path;
- do not wire any ReasoningRuntimeContract adapter into product runtime;
- do not add prompts, schemas, task-dependency fields, or adaptive policies;
- do not modify ClaimCompiler, clean-data admission, or runtime thresholds;
- do not implement intervention selection, randomization, online learning,
  automatic recovery, passive sensing, or causal claims;
- do not restore a direct NIM, Ollama, OpenAI API-key, local-model, or other
  model-provider path during this prerequisite phase;
- do not begin an adaptive implementation seam without a separately approved
  experiment and implementation plan.

## 1. Thesis

LyraOS is both an execution/recovery product and a behavioral measurement
instrument. Those roles are not opposites. A useful planning suggestion,
re-entry cue, or reminder may intentionally influence behavior. The validity
failure is not influence itself; it is influence that is unlogged,
irreconstructible, misattributed, or promoted into a stronger claim than the
evidence supports.

The prerequisite architecture is therefore:

```text
authoritative observations
-> deterministic derived features
-> versioned heuristic hypotheses
-> optional ReasoningRuntimeContract hypothesis augmentation
-> evidence adjudication
-> OutputClaimCompiler and surface policy
-> registered user-facing surface
-> browser-proven exposure and outcome
```

It explicitly rejects:

```text
AI replaces heuristics
-> one fluent explanation appears
-> explanation becomes product truth
```

Product usefulness may advance before scientific claim authority. Scientific
claim authority may advance only after provenance, exposure, missingness,
construct validity, and study design support it.

## 2. Current Repository Reality

The current implementation is a braided deterministic loop, not one correlated
adaptive chain.

| Stage | Current owner and evidence | Current capability | Prerequisite gap |
| --- | --- | --- | --- |
| Brain Dump | `backend/app/api/v1/endpoints/brain_dump.py`, `backend/app/services/brain_dump_parser.py`, `frontend/lib/hooks/use-brain-dump-flow.ts` | Write-free parse, editable preview, explicit partial commit, existing-deadline binding, idempotency guards | Pulse and onboarding do not have capability parity; batch semantics are partial-success despite single-transaction wording; origin is not durable through later execution |
| Provider import | Provider normalizers plus canonical deadline services | Moodle/iCal structure can become provider-scoped obligations; provider status stays lower authority | Imported structure is not execution truth; no adaptive use is authorized; provider-to-pressure-to-execution correlation is incomplete |
| Pressure Map | `backend/app/services/academic_pressure.py`, `frontend/components/pulse/PulseAcademicPressureMap.tsx` | Read-only pressure projection, uncertainty ranges, coverage questions, create/split preview and explicit task creation | Coverage questions have no correction command; several recovery options are labels only; normal recovery emission is safety-gated; combined-load calculation may double-count planned academic blocks |
| Execution | `backend/app/services/stopwatch_manager.py`, `backend/app/services/active_stopwatch_store.py` | Start, pause, resume, switch, stop, stale resolution, DB plus Redis active-state recovery | Multi-commit finalization can leave partial truth; Pulse and Today use different pause and stop-result semantics; long-lived failure points lack characterization |
| Existing intervention-like surfaces | Output registry, creation nudge, pause/resume prediction, reminders, deterministic deadline suggestion | Deterministic suggestions and alerts with partial lifecycle support | Client-only re-entry/system-insight/recovery surfaces are unregistered; route-specific ACK behavior differs |
| Recovery | `PulseReentryQueue`, stale-session resolution, missed-plan actions | Resume, resolve stale, mark done, drop, open | Documented keep/shrink/reschedule/irrelevant choices are not direct actions; recovery states are overloaded; `blocked` and prerequisite-incomplete are not representable |
| Exposure Ledger | `output_surfaces.py`, `exposure_ledger.py`, exposure models | Decision, suppression, render rows, policy horizons, UNKNOWN fail-closed logic | Server code can write a render row before browser acknowledgement; decision, delivery, browser render, outcome, and resulting mutation are not always correlated |
| Cortex | `cortex.py`, `cortex_clean_profiles.py` | Read-only event/diagnostic projection and clean-profile helpers | Not a runtime evidence bus; clean filters remain duplicated elsewhere; Admission/Coverage Gate remains deferred |
| ClaimCompiler | `claim_compiler.py`, analytics packaging | Bounded deterministic compilation for selected synthesis paths | Most ordinary insight generators do not route through one claim path; no AI authority exists |

## 3. Current AI Boundary

The repository already contains two different AI stories. They must remain
separate.

### 3.1 Direct model enrichment retired

The direct `llm_enrichment.py`, `llm_parser.py`, and `nvidia_nim_client.py`
runtime, its scheduler job, provider configuration, and NIM/Ollama fallbacks
were removed on 2026-07-11. Deterministic deadline suggestions remain active
and user-confirmed. Historical task `llm_*` fields remain only because removing
them requires a separately approved schema migration.

The removed path lacked a complete durable record of model, prompt,
configuration, heuristic-only candidate set, AI-only additions, rendered
wording, and user exposure. `llm_priority` had no canonical mutation target;
`llm_sub_items` had no product consumer; model-implying fallback copy was
non-actionable and not impression-logged.

This was legacy task enrichment. It was not behavioral synthesis, the future
adaptive host, or an authority source. The founder decision on 2026-07-11 was
implemented by removing the active NIM/Ollama runtime while preserving bounded
historical compatibility.

The completed runtime retirement preserved these constraints:

1. characterize current deterministic parser behavior and any user-visible
   enrichment chip behavior;
2. disable and remove scheduler registration and provider calls;
3. remove direct NIM/Ollama/OpenAI API-key configuration, environment
   documentation, clients, and secrets from the active runtime surface;
4. preserve the deterministic deadline-suggestion workflow hidden inside the
   former enrichment UI until a later naming/storage cleanup can prove parity;
5. preserve existing `llm_*` rows as historical provenance until a separately
   approved schema migration can archive or remove the columns safely;
6. keep user export/delete coverage for retained historical rows;
7. replace provider-specific tests with negative gates proving no direct
   model-provider or API-key path can return.

The retirement does not authorize ReasoningRuntimeContract/OpenClawAdapter wiring. It creates a clean
future boundary; it does not fill it.

### 3.2 Future reasoning boundary

`docs/AUTHORITY.md`, `docs/single_authority_contract.md`,
`docs/claim_compiler_and_synthesis_boundary.md`, and the active freeze hold
now treat the future reasoning layer as an adapter boundary rather than a
direct product dependency:

```text
LyraOS
-> ReasoningRuntimeContract
-> OpenClawAdapter
```

`ReasoningRuntimeContract` is the product-facing abstraction. It defines
runtime identity, capability discovery, model identity, authentication mode,
quota state, invocation contract, session isolation, structured output,
provenance, revocation, failure behavior, and fallback policy.

`OpenClawAdapter` is the first candidate adapter. Its eventual target
authentication mode is each user's own ChatGPT/Codex subscription through
adapter-managed OAuth, not OpenAI Platform billing or a LyraOS API key.

If separately authorized later, the allowed direction is:

```text
Cortex clean profile
-> EvidenceAdmissionGate
-> EvidencePacket
-> ReasoningRuntimeContract
-> OpenClawAdapter using a per-user ChatGPT/Codex OAuth profile
-> structured draft
-> OutputClaimCompiler and SurfacePolicy
-> browser-rendered registered surface
```

The reasoning runtime may draft competing hypotheses, contradictions,
missing-variable questions, or wording. It may never own observed truth,
confidence, clean-data admission, publication, exposure truth, or mutation.

Current prerequisite phase: no direct provider API client, no API-key storage,
no local-model runtime, and no fallback implementation may return.

Future architecture: provider and authentication strategies remain unresolved.
Any additional runtime adapter requires separate founder approval, security
review, provenance compatibility review, and implementation plan.

### 3.3 Per-user reasoning-runtime connection boundary

The desired future product flow is:

```text
user authenticates to LyraOS
-> user explicitly chooses Connect ChatGPT
-> LyraOS starts a ReasoningRuntimeContract connection flow
-> OpenClawAdapter owns the Codex OAuth or device-code flow
-> OpenClawAdapter stores the OAuth credential in a user-isolated agent/profile
-> LyraOS stores only the connection reference and lifecycle state
-> authorized EvidencePacket is sent through the ReasoningRuntimeContract
-> structured draft returns through OutputClaimCompiler and SurfacePolicy
```

This does **not** mean zero network communication with OpenAI. It means zero
direct model-provider integration, API key, or OpenAI Platform billing path in
LyraOS. The adapter owns provider transport, credentials, retries, and quota
under the user's supported entitlement and plan-dependent limits.

Prerequisites before any implementation:

- verify the adapter's supported OAuth/device-code flow can be invoked safely
  from a LyraOS connection UX without collecting ChatGPT passwords;
- in the user-connected path, one LyraOS user maps to one isolated adapter auth
  profile; no shared founder subscription and no cross-user credential order or
  fallback;
- OAuth tokens, refresh tokens, and provider cookies remain adapter-owned,
  encrypted at rest, redacted from logs/exports, and inaccessible to prompts;
- LyraOS persists only opaque connection/profile references, status, capability
  metadata, quota state, and timestamps;
- disconnect removes the LyraOS mapping and instructs the adapter to delete
  local
  credentials; provider-side revocation remains explicit and testable;
- expiration, revocation, quota exhaustion, profile mismatch, or missing
  capability fails closed with no API-key, local-model, or shared-account
  fallback;
- multi-tenant isolation, callback binding, CSRF/state/PKCE, replay resistance,
  session reset, consent, retention, export, and deletion are characterized;
- runtime adapter version, Codex runtime version, model route, auth mode, and profile
  identity are recorded without persisting secret material.

The current operator alert relay is not this product connection layer and does
not authorize it.

Product entitlement, runtime connection, and research assignment are separate
state machines; see
`docs/concepts/product_entitlement_runtime_and_research_prerequisite.md`.

### 3.4 Cohort-sponsored runtime bridge

The eventual user-connected path is not required for founder dogfood or a
trusted university wedge to validate LyraOS product utility.

Before user-connected or institution-sponsored runtime exists, a separately
approved research-preview protocol may use a founder-managed adapter profile as
cohort-sponsored runtime custody. That bridge remains inside:

```text
LyraOS
-> ReasoningRuntimeContract
-> OpenClawAdapter
```

It does not authorize a direct model-provider client, a LyraOS API-key path, a
local-model fallback, or "founder account as product architecture."

The bridge must be recorded as operational metadata:

- `product_entitlement`: `research_preview_pro`;
- `runtime_funding`: `founder_sponsored` or `cohort_sponsored`;
- `runtime_custodian`: founder-managed adapter profile;
- `research_assignment`: `shadow_ai` or `visible_ai_preview`;
- `subject_user`: the LyraOS user whose EvidencePacket is processed;
- `consent_scope`: shadow only, visible preview, exportable, or withdrawn;
- `isolation_mode`: per-subject context isolation with no cross-user memory;
- `migration_target`: `user_connected`, `institution_sponsored`, or a later
  approved funding model.

For the university wedge, this means a trusted participant may test the
Pro-shaped product without bringing a personal ChatGPT subscription. It does
not mean every Pro user gets founder-sponsored AI, and it does not decide the
future commercial entitlement model.

Authentication references checked 2026-07-11:

- [OpenClaw OpenAI provider](https://github.com/openclaw/openclaw/blob/main/docs/providers/openai.md)
  documents ChatGPT/Codex subscription OAuth through the native Codex runtime
  and distinguishes it from API-key billing;
- [OpenClaw authentication](https://docs.openclaw.ai/gateway/authentication)
  documents separate auth profiles and profile pinning;
- [OpenAI billing guidance](https://help.openai.com/en/articles/8156019-is-api-usage-included-in-chatgpt-subscriptions-even-if-i-have-a-paid-chatgpt-account)
  confirms ChatGPT subscriptions and OpenAI Platform API billing are separate.

These sources support one possible adapter direction, not the safety or product
validity of embedding the flow in LyraOS. That requires the prerequisite
security and tenancy proofs above.

## 4. Seven-Layer Prerequisite Stack

### Layer 1: Authoritative evidence

Tasks, deadlines, accepted plans, stopwatch sessions, pause events, provider
facts, corrections, explicit confirmations, exposure events, and outcomes.
Provider rows and AI annotations remain provenance-bearing candidates, not
execution truth.

### Layer 2: Deterministic features

Estimate error, initiation delay, lateness, schedule density, transition
topology, pause duration, execution duration, visible coverage gaps,
missingness, and exposure state. Every feature needs one definition, unit,
sign convention, clean profile, version, and known failure mode.

### Layer 3: Versioned heuristic hypotheses

Rules and thresholds remain inspectable baselines even when imperfect. They
provide longitudinal comparability and make blind spots measurable. Each rule
must expose inputs, threshold rationale, confidence meaning, false-positive
cost, false-negative cost, and exposure sensitivity.

### Layer 4: ReasoningRuntimeContract augmentation

Future AI may add candidates, contradictions, semantic decomposition, or
missing-variable suggestions. It must preserve:

- heuristic-only candidates;
- AI-only additions;
- agreement and disagreement sets;
- supporting, contradicting, and missing evidence;
- model, host, prompt, policy, and schema versions;
- user correction and later evidence;
- the claim-authority ceiling.

Generated chain-of-thought is neither required nor accepted as provenance.
Store structured evidence references and inspectable justification objects.

### Layer 5: Evidence adjudication

Adjudication records support, contradiction, missingness, user correction,
longitudinal repetition, competing exposures, and unresolved alternatives. It
does not force one explanation when the evidence is non-identifying.

### Layer 6: Claim authority

Claim authority uses two independent axes.

EpistemicStatus:

1. operational fact;
2. descriptive summary;
3. soft hypothesis;
4. repeated pattern;
5. statistically supported claim;
6. causal claim;
7. unresolved.

ClaimRiskClass:

1. operational;
2. planning;
3. behavioral;
4. sensitive psychological;
5. medical or clinical;
6. identity-intrusive.

Sensitive behavioral, clinical, medical, identity, motivation, focus,
discipline, avoidance, productivity, and agency claims remain blocked without
construct defense and explicit authority.

### Layer 7: User-facing communication

Operational fact, reflection, planning suggestion, recovery option, reminder,
warning, adaptive candidate, and experiment treatment are different surface
classes. Each needs an interruptiveness class, initiative source, mutation
request, contamination risk, terminal outcomes, and claim ceiling.

## 5. Required Conceptual Contracts

These are documentation contracts only until a later plan authorizes schema or
runtime work.

### `DecisionRecord`

Minimum concepts: `trace_id`, `causation_id`, `correlation_id`, decision point,
availability, eligibility, full option set and version, policy hash,
selection mode, selection probability, no-treatment option, no-decision
reason, suppression reason, tailoring-variable snapshot, refractory state,
burden state, quiet-hours state, and evaluation timestamp.

Availability, eligibility, a reached decision point, no treatment, and no
decision are not interchangeable.

### `ExposureLifecycle`

Required states: reserved, delivery attempted, delivered, render attempted,
browser rendered, partially visible, superseded, acted, dismissed, expired,
suppressed, lost unrendered, and unknown.

Required mechanics: idempotency, event ordering/version, client instance,
late-event handling, exact-or-reconstructible stimulus identity, redaction
policy, terminal reason, and linkage to the resulting mutation.

### `OutcomeWindow`

Minimum concepts: estimand, proximal and distal outcome, outcome source,
baseline window, carryover window, competing exposures, concurrent
interventions, measurement burden, informative missingness, censoring,
late-outcome policy, and analysis eligibility.

### `RecoveryEpisode`

Define interruption, paused, parked, stale, resumed, rescheduled, shrunk,
split, dropped, marked irrelevant, completed elsewhere, auto-closed, and
unresolved. A recovery action is not proof of recovery; the later outcome is a
separate event.

### `HypothesisSet`

Minimum concepts: observation refs, deterministic hypotheses, AI-added
hypotheses, agreement/disagreement, support, contradiction, missing evidence,
exposure contamination, user correction, confidence semantics, host/model and
prompt versions, status, claim ceiling, generation mode, and visibility state.

`generation_mode` values: deterministic, ai_shadow, ai_visible_candidate.

`visibility_status` values: internal_only, eligible_for_policy_review,
user_visible, suppressed.

An AI hypothesis existing internally is not the same as exposing it to a
participant or user.

### `ReasoningRuntimeContract`

Minimum concepts: LyraOS user reference, subject user, product entitlement,
runtime funding, opaque runtime connection/profile reference, adapter identity,
provider family, auth mode, connection status, capability set, plan/quota
state, connected/validated/expired/revoked times, callback state binding,
runtime custodian, credential custodian, storage boundary, disconnect and
provider-revocation status, session-reset requirement, audit reference, failure
mode, fallback policy, migration target, and supported output schemas.

Forbidden fields in LyraOS storage, logs, prompts, evidence packets, and
exports: provider password, OAuth access token, refresh token, session cookie,
device code, authorization code, or reusable provider credential.

### `OpenClawAdapter`

Minimum concepts: LyraOS user reference, opaque OpenClawAdapter agent/profile
reference, provider `openai`, auth mode `codex_oauth`, adapter capability
mapping, profile isolation, credential custody proof, quota mapping,
disconnect/revocation behavior, and audit reference.

This adapter specializes `ReasoningRuntimeContract`; it does not replace it as
the top-level product architecture.

### `ModelInvocationRecord`

Minimum concepts: runtime adapter identity, runtime adapter version, model
family/route, opaque auth-profile reference, auth mode, prompt/template
version, structured input refs, input/output hashes, parsed output, retries,
validation, quota/expiry outcome, privacy class, retention, user confirmation,
and links to later decision, exposure, claim, or mutation IDs. `fallback` must
be `none` in the current prerequisite phase.

### `RuntimeEpoch`

A `RuntimeEpoch` begins whenever any research-relevant runtime property
changes: adapter, provider, model route, model version, authentication mode,
plan capability, quota state, prompt/template family, reasoning configuration,
policy version, or major adapter version.

No silent runtime substitution is allowed in research-sensitive paths.
Commercial paths may later allow explicit graceful fallback, but research paths
must fail closed or record protocol deviation.

### `CapabilitySnapshot`

Minimum concepts: runtime connection reference, adapter identity, model routes,
available modalities, structured-output support, quota state, rate-limit state,
privacy class, data-retention mode, and capability timestamp.

### `RuntimeTransitionEvent`

Minimum concepts: previous epoch, next epoch, reason, source, user visibility,
research sensitivity, protocol deviation status, and affected pending
decisions.

### `ExperimentRegistry`

Minimum concepts: founder N-of-1, feasibility, observational, MRT, or SMART
study mode; protocol and analysis-plan versions; randomization unit and seed
authority; probability support; carryover assumptions; burden ceiling; quiet
hours; safety/friction criteria; pause/disable authority; retention; minimum
sample rule; and promotion authority.

Existing deterministic `1-in-7` control labels and `user_id % 2` arm labels are
not experiments and may not support causal estimates.

### Dependency proposal contract

Separate proposed, user-confirmed, provider-derived, and rejected relations.
AI may suggest a dependency. Only explicit user confirmation or deterministic
authority may establish dependency truth. No task-graph schema is authorized
here.

## 6. Exposure Fidelity And Privacy

The architecture must distinguish:

```text
generated candidate
-> policy-selected candidate
-> delivered payload
-> actually rendered wording
-> user interaction
-> resulting mutation
```

The current doctrine has a tension: research replay benefits from exact
stimulus retention, while Pressure Map privacy deliberately retains redacted
structural summaries. Future AI exposure therefore needs a typed retention
policy, not unrestricted prompt/output storage.

Strong attribution fails closed to `UNKNOWN` when the rendered wording, model,
policy, option set, assignment probability, baseline context, or competing
exposures cannot be reconstructed.

## 7. Baseline, Missingness, And Distribution Shift

Future analysis must distinguish genuine user change from intervention-linked
shift, changed task composition, provider-coverage change, missingness,
measurement reactivity, model drift, policy drift, and unresolved shift.

Ignored prompts, delayed answers, absent reflections, unstarted tasks, and
unconfirmed candidates are observable absences. They are not neutral defaults
and not psychological explanations.

## 8. Literature Translation Boundary

Health and clinical intervention literature may inform experimental structure,
availability, burden, missingness, consent, exposure accounting, causal
identification, and safety governance. It does not authorize diagnosis,
treatment language, medical personalization, clinical claims, or transfer of
effect sizes and decision rules into LyraOS.

| Literature family | What it supports | What it does not support | LyraOS prerequisite |
| --- | --- | --- | --- |
| JITAI design | Decision points, availability, tailoring variables, intervention options including no treatment, proximal outcomes, receptivity and burden | That adaptive prompts are effective in LyraOS | Versioned decision and burden contracts |
| MRT | Repeated randomization and causal excursion effects for proximal outcomes | Calling deterministic control labels an experiment | Option sets, probabilities, availability, estimands, protocol authority |
| SMART/MOST | Empirical construction and optimization of intervention sequences/components | Choosing an adaptive sequence from intuition | Promotion stages and component-level protocols |
| N-of-1/single-case | Founder-level randomized repeated-measure designs | Treating ordinary dogfood as causal evidence | Randomization, autocorrelation, trend, carryover, washout, individual estimands |
| EMA | Momentary measurement can reduce recall distance | Assuming compliance, missingness, or reactivity are harmless | Prompt delivery, latency, response, missingness, and reactivity records |
| Interruption/re-entry | Suspended-goal cues can reduce resumption cost | Inferring motivation or choosing recovery automatically | RecoveryEpisode semantics and user-controlled cues |
| Cognitive offloading | Reminders can improve immediate prospective-memory performance | Assuming dependence-free learning | Tapering/dependence outcomes and no-prompt follow-up |
| Contextual bandits/OPE | Logged probabilities and overlap can support policy evaluation | Learning safely from deterministic logs without support | Keep online learning and OPE promotion forbidden until experiments exist |
| Human-AI/XAI | AI wording and explanations influence judgment; self-explanations can be unfaithful | Treating model rationale as causal provenance | Evidence refs, versioned invocation, exposure logging, user correction |

Core sources include the JITAI design framework, HeartSteps MRT, MRT causal
methods, MOST/SMART, N-of-1 methods, EMA compliance/reactivity reviews, WHO AI
governance, NIST AI RMF, interruption-resumption research, and recent cognitive
offloading findings. The implementation plan must maintain a literature ledger
with support, non-support, population, transportability, null findings, and
claims still forbidden.

## 9. Deterministic Authority Boundary

AI must never own:

- authoritative task, deadline, or provider state;
- timer/session finalization;
- exposure or terminal lifecycle truth;
- randomization authority;
- clean-data admission;
- irreversible mutation;
- ClaimCompiler promotion;
- production repair;
- consent, retention, or kill authority.

## 10. Deliberately Unresolved

This document does not choose the first intervention family, recovery policy,
prompt wording, final model route, whether hypotheses become visible, adaptive
scheduling algorithm, online-learning method, fine-tuning approach, schema,
experimental design, burden thresholds, embedded connection UX, adapter hosting
model, or generalizability beyond founder use.

## 11. Decision Packet

The repository-wide use-case inventory and method-by-method completion ladder
live in `docs/concepts/ai_capability_completion_map.md`. This document owns the
prerequisite architecture and conceptual contracts; the companion map owns the
candidate catalogue. Neither document authorizes code.

Clearly required during prerequisite refactor:

- correct exposure render truth and route parity;
- characterize current transaction and failure boundaries;
- make current deterministic surfaces useful and exposure-complete;
- inventory and version heuristics and thresholds;
- keep direct model-provider retirement mechanically gated while preserving
  historical provenance and export/delete compatibility until migration
  approval;
- define the contracts above without implementing them;
- verify per-user ReasoningRuntimeContract/OpenClawAdapter feasibility and
  credential isolation
  without wiring it into product runtime;
- align public claims with shipped authority;
- prove cleanup, operator read-only behavior, CI, and topology honestly.

Potentially high-value future reasoning-runtime work:

- competing-hypothesis generation;
- semantic task decomposition proposals;
- contradiction and missing-variable detection;
- evidence-packet summarization;
- low-authority recovery-option proposals.

High-risk uses to keep parked:

- behavioral attribution;
- identity or clinical language;
- automatic scheduling or recovery mutation;
- hidden adaptive selection;
- AI-created confidence;
- replacement of deterministic baselines;
- policy learning from deterministic or exposure-incomplete logs.

## Hard Stop Repeated

This document authorizes no runtime AI, ReasoningRuntimeContract/OpenClawAdapter wiring, prompt, schema,
adaptive policy, experiment, threshold change, dependency graph, automatic
recovery, ClaimCompiler change, or public behavioral claim. Move from this
architecture only through explicit founder approval and a new plan.
