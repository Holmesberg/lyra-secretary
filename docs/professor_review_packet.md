# LyraOS Professor Review Packet

**Status:** Current external-review orientation.
**Created:** 2026-05-15.
**Audience:** Faculty/research review of the product-research architecture.

This packet summarizes what LyraOS currently is, what it is not, and which
documents are authoritative. It is intended to prevent historical notes,
operator dogfood, and future research directions from being read as shipped or
validated claims.

---

## 1. Current Framing

LyraOS is a behavioral measurement instrument with a productivity interface.

The shipped product helps users plan tasks, execute them with timers, recover
from missed plans, and view bounded insight surfaces. The research layer reads
those traces through explicit provenance, clean-data, exposure, and uncertainty
contracts.

The core intelligence substrate is rule-governed, probabilistic, inspectable,
longitudinal, and epistemically constrained. AI components support enrichment,
operator work, or interface assistance; they are not the source of behavioral
truth.

---

## 2. Current Shipped Surface

Current user-facing surfaces include:

- Google sign-in
- brain-dump onboarding
- task planning and quick capture
- timer start, pause, resume, stop, and switch
- overdue recovery
- calendar and deadline views
- Moodle deadline import and submission detection
- read-only Google Calendar context
- Pulse dashboard
- Insights page and primary synthesis card
- pause and resume prediction surfaces
- archetype survey/proximity, framed as probabilistic prior/proximity
- settings, export/deletion, and feedback

Operator-only surfaces include:

- admin dashboard
- JARVIS
- OpenClaw
- operator notifications
- topology verification
- exposure diagnostics and policy logs
- Notion outbound sync/retry plumbing

---

## 3. Not Shipped / Not Authorized

The current system does not authorize:

- autonomous rescheduling
- hidden calendar mutation
- validated adaptive scheduling
- confidence-backed behavioral recommendations
- identity or personality labels
- learning from exposed/intervened behavior without exposure modeling
- new required user inputs for research enrichment
- treating AI output as observed behavioral truth
- treating operator/JARVIS/OpenClaw traces as Lyra product research data

---

## 4. Research Doctrine

The central research question is:

```text
Are humans wrong about their own execution capacity in structured,
modelable ways?
```

Current doctrine:

- observed product traces remain distinct from derived metrics and inferred
  hypotheses
- Cortex recomputes derived metrics at read time
- clean-data profiles gate what can be used for learning or research claims
- exposure state must be known before baseline interpretation
- `UNKNOWN` exposure fails closed
- surfaced nudges, predictions, reflections, and insights can contaminate later
  behavior
- archetypes are cold-start priors, not identity labels
- user attention is scarce scientific capital
- missingness can be signal, but it is not observed truth

---

## 5. Ethics, Privacy, And Consent Boundary

LyraOS is pre-alpha product research and operator dogfood with a small alpha
cohort. Unless a separate institutional protocol is approved, it should not be
represented as an IRB-approved human-subjects study.

Data categories can include:

- identity/account metadata from Google sign-in
- tasks, planned times, deadlines, categories, and descriptions
- timer sessions, pauses, starts, stops, and recovery actions
- readiness/reflection/scope fields where already in the task flow
- integration metadata and imported context for connected services
- exposure/render/acknowledgement logs for behavior-shaping surfaces
- feedback and account deletion/export records

Third-party/runtime dependencies can include Cloudflare, Supabase, Google,
Moodle, Notion integration plumbing, and optional hosted AI paths for
operator/enrichment workflows. Public privacy/terms copy should be reviewed
before any broader release.

---

## 6. Current Limitations

Important limitations before interpreting the system as research evidence:

- pre-alpha cohort is small
- much evidence is operator dogfood or early alpha behavior
- some historical docs preserve older names and proposed designs
- privacy/legal copy still needs production-grade review
- Google refresh tokens and Moodle iCal URLs remain plaintext debt
- exposure coverage is v0 and partially adapter-based
- adaptive scheduling is documented as a future direction, not a shipped claim
- archetype priors are heuristic cold-start mechanisms, not validated
  psychological types
- historical documents may contain older absolute novelty language that should
  be read as lab-note framing unless restated in active governance docs

---

## 7. Authoritative Reading Order

Recommended order for review:

1. `MANIFESTO.md`
2. `docs/behavioral_instrumentation_doctrine.md`
3. `docs/cortex_product_research_contract_v0.md`
4. `docs/cortex_contract_v0.md`
5. `archive/appstore/summary_of_app.md`
6. `docs/adaptive_scheduling_progressive_inference.md`
7. `docs/deployment_architecture.md`
8. `docs/openclaw_orchestration_contract_v0.md`

Historical/design-only docs are useful for provenance, but they should not be
treated as current authority when they conflict with the list above.

---

## 8. One-Sentence Summary

LyraOS is a low-friction planning and execution product whose deeper purpose is
to preserve a clean behavioral trace, interpret it through explicit
measurement-validity contracts, and earn stronger guidance only when evidence,
identity, topology, exposure, and uncertainty all hold together.
