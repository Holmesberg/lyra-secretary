# Academic Execution Substrate

**Status:** Product-research doctrine note.
**Created:** 2026-05-16.
**Purpose:** Capture the Baseet collaboration insight, the academic execution
integration boundary, and the evidence rules for passive academic activity.
**Governance:** Subordinate to `MANIFESTO.md`, especially "Manifesto
Governance Rule", "Substrate Kill Criterion", and "Academic Execution
Substrate Governance".

This document does not authorize hidden tracking, autonomous scheduling,
copyrighted content ingestion, product merger, or stronger behavioral claims.
It defines the architecture needed for LyraOS to remain a provider-agnostic
execution inference engine while integrating with academic/content systems.
During the architecture freeze it also does not authorize new provider
adapters, passive tracking, runtime AI synthesis, new user-facing insights,
behavior-transition equations, schema migrations, or automatic interventions.
Implementation-sounding examples below are future-gated examples unless a
current authority document explicitly promotes them.

Implementation note: Academic Pressure Map surfaces must follow
`docs/academic_pressure_map_contract.md`. That contract freezes trust-state
copy, validity-threat cross-links, research-integrity checks, and the rule that
passive activity is weak evidence unless the user accepted or confirmed an
intention.

Manifesto linkage: academic pressure, provider adapters, passive activity, and
Baseet/Moodle integration are potential validity-threat surfaces. They must be
read through `MANIFESTO.md` before any feature is allowed to affect Cortex,
Exposure Ledger, clean-data profiles, adaptive scheduling, or stronger research
claims.

---

## 1. Conversation Summary

The collaboration idea started as:

```text
Baseet or LMS provides academic structure
  -> Lyra processes lectures, tutorials, labs, deadlines, and calendar context
  -> Lyra creates an execution plan
  -> user studies and Lyra calibrates over time
```

The key product feedback from the Baseet creator was:

```text
If the student has to jump between two separate apps, the flow probably dies.
People barely connect one LMS calendar even with step-by-step instructions.
Do not ask users to operate a Baseet -> Lyra -> Baseet -> Lyra loop.
```

This is correct product feedback. It does not invalidate LyraOS research. It
invalidates a high-friction two-app workflow.

The refined conclusion:

```text
The research substrate should not be the user-facing burden.
It should sit underneath an immediately useful academic execution workflow.
```

## 2. Product Identity Boundary

LyraOS should not merge into Baseet, and Baseet should not become a required
runtime dependency.

The stable product boundary is:

```text
External systems provide structure.
Lyra provides execution inference.
```

Current strategic framing:

```text
Lyra is the execution-reality middleware above planning systems,
not a replacement planner.
```

The user should not need to rebuild academic or work commitments inside Lyra
for Lyra to become useful. Calendars, LMSs, Baseet, Notion, Jira/Linear, and
similar tools already contain plans and obligations. Lyra's job is to
normalize that structure, expose pressure, and model what happens when
execution collides with it.

Examples:

| Layer | Responsibility |
| --- | --- |
| Baseet | academic content, resources, course memory, AI chat over materials |
| Moodle / LMS | external obligations, assignments, quizzes, deadlines |
| Google Calendar | availability and external time constraints |
| LyraOS | intention, execution, drift, recovery, reflection, recalibration |

Baseet is one possible upstream provider, not the product identity.

Long-term, Lyra should be an execution intelligence layer with adapters to:

- Baseet,
- Moodle,
- Google Calendar,
- Canvas / Blackboard / Google Classroom,
- Notion or other planning systems,
- and future academic or workplace systems.

### EdTech And Learning-Analytics Boundary

Academic integrations place Lyra near learning analytics and educational data
mining, but Lyra must not inherit their strongest institutional overclaims.

Rules:

- LMS activity is not learning.
- Assignment completion is not mastery.
- Resource views are not comprehension.
- Attendance is not engagement.
- Deadline pressure is not academic risk by itself.
- Study execution is not proof of learning outcome.

Academic provider data may support workload topology, obligation discovery,
and pressure visibility. It must not become competence scoring, student-risk
classification, or institutional surveillance. If a future partner wants
teacher/admin views, that is a new governance surface, not an extension of the
student execution substrate.

## 3. No Two-App Loop

Do not require the user to bounce between products:

```text
Baseet -> Lyra -> Baseet -> Lyra
```

That flow has too much operational friction.

The acceptable integration shapes are:

### Option A: Embedded Lyra Surface Inside Baseet

Baseet remains the academic hub. Lyra-powered execution actions appear inside
Baseet:

- "Turn this week into a study plan"
- "Start focus block"
- "Done / partial / skipped"
- "Reschedule"
- "Review later"
- "Show execution summary"

This is strongest for adoption because Baseet already owns academic context.

### Option B: Baseet Data Inside Lyra

Lyra imports Baseet academic structure once, then the student uses Lyra as the
execution app.

This works only if Lyra is compelling enough to become the daily execution
surface.

The near-term collaboration experiment should not start with API-key
architecture. It should start with one feature prototype:

```text
Baseet shows "turn this week into a study plan".
Lyra logic converts deadlines/resources/free time into an editable execution plan.
Use a sample JSON/course-week export before building full integration.
```

## 4. The Research Is Not Lost

The research direction survives if Lyra becomes the hidden measurement layer
inside a low-friction execution flow.

Bad framing:

```text
Users adopt Lyra because they want behavioral instrumentation.
```

Better framing:

```text
Users use an academic planning/execution feature because it helps now.
Lyra collects valid execution traces through that flow.
The research substrate compounds underneath.
```

This means Day-0 value can come from approximate pressure visibility before
strong personalization exists. A map that is semi-accurate, provenance-labeled,
and correctable is product value as long as it does not claim precision it has
not earned.

The user-facing promise is immediate clarity:

```text
Turn academic chaos into an executable plan.
```

The internal research loop remains:

```text
intention -> execution -> drift -> reflection -> recalibration
```

## 5. Passive Academic Activity

If Lyra is embedded in an academic environment, the system can observe richer
study activity without requiring the user to manually start a stopwatch for
every resource.

Examples of academic activity events:

| Signal | Meaning |
| --- | --- |
| resource opened | user was exposed to the resource |
| page remained active | resource stayed visible |
| scroll depth | user navigated material |
| video play/pause/seek | video was consumed or revisited |
| repeated rewinds | possible difficulty or review |
| problem opened | user entered a practice surface |
| answer submitted | stronger execution evidence |
| tab inactive | possible attention loss |
| long idle gap | possible pause or abandonment |
| user confirms done | self-reported completion |
| quiz/submission result | external outcome evidence |

Critical invariant:

```text
academic activity is not learning.
academic activity is not completion.
academic activity is not understanding.
```

It is evidence, not truth.

## 6. Evidence Classes

Passive activity must not be forced into planning calibration.

| Evidence class | Has intention? | Has execution? | Primary use |
| --- | --- | --- | --- |
| Imported academic obligation | external | no | pressure map |
| Passive academic activity | no or weak | partial | activity trace / engagement evidence |
| Planned Lyra block | yes | yes if executed | planning calibration |
| User-confirmed plan from pressure | yes | later yes | calibration and adaptive estimates |
| Abandoned/inactive session | maybe | partial/unknown | missingness / friction analysis |

The rule:

```text
Passive academic activity != planned execution trace.
```

Use passive activity for:

- resource effort distribution,
- activity/session candidates,
- fragmentation indicators,
- abandonment candidates,
- weak engagement evidence,
- and prompts for user confirmation.

Use planned blocks for:

- planned-vs-actual duration delta,
- planning calibration,
- execution multiplier,
- clean adaptive scheduling evidence,
- and stronger personal recalibration.

## 7. Stopwatch Role

The stopwatch should not disappear. It should be demoted from the only
instrument to one instrument among several.

Before:

```text
task created -> stopwatch start -> stopwatch stop -> execution trace
```

After academic embedding:

```text
manual timer
+ resource interaction
+ video activity
+ scroll/activity topology
+ done/partial/skipped confirmation
+ reflection
+ deadline pressure
= richer execution evidence
```

The stopwatch remains important for:

- offline studying,
- notebook work,
- external materials,
- deep work outside Baseet/LMS,
- and explicit planned execution blocks.

## 8. Intention Requirement

Planning calibration requires intention.

If the user never accepted or created a planned block, Lyra can measure
activity duration, but not full intention-vs-execution drift.

Therefore:

```text
No accepted plan -> no strong planning delta.
```

Passive sessions may become "academic activity traces" or "session
candidates." They should not enter the `planning_calibration` clean-data
profile unless the user confirms or accepts an intended block.

This preserves the core Lyra invariant:

```text
External structure gives pressure.
User intention gives calibration.
Observed execution gives drift.
```

## 9. Embedded Activity UX

Avoid the phrase:

```text
Lyra is always watching.
```

Use:

```text
Lyra is observing this study session.
```

Or:

```text
Lyra turns study activity into execution feedback.
```

Required UX controls:

- visible tracking status,
- pause tracking,
- mark as not studying,
- discard session,
- edit session,
- private mode,
- clear explanation of what is tracked,
- and explicit consent before activity telemetry is used.

If students feel watched, the product fails.

If students feel supported, the product works.

## 10. Activity-Derived Session Candidates

The clean first passive-instrumentation prototype is:

```text
lecture/resource page instrumentation
```

Track:

- page open,
- active time,
- scroll depth,
- video play/pause/seek if available,
- inactive gaps,
- same-slide dwell,
- user marks done / partial / review later / discard.

Then show:

```text
You spent 42 active minutes on Lecture 4.
There were 5 inactive gaps.
You reached 80% scroll depth.
Mark this as: done / partial / review later / discard.
```

This validates passive instrumentation without pretending activity equals
learning.

## 11. Pause And Abandonment Detection

Duration and interaction topology can support session-candidate state changes:

- same slide/page for too long -> possible pause candidate,
- inactive tab beyond threshold -> possible pause or abandonment,
- resource left open overnight -> abandoned/unknown candidate,
- long idle after video pause -> possible interruption,
- repeated short active bursts -> fragmentation candidate.

But these are candidates, not truth.

Good copy:

```text
This study block has had several inactive gaps. Should Lyra keep tracking it
as active study?
```

Bad copy:

```text
You lost focus.
```

## 12. AI Role In Academic Execution

AI becomes more useful in this architecture, but it still must not own truth.

AI may help with:

- summarizing academic structure,
- classifying rough complexity,
- extracting candidate coverage hints,
- explaining why a pressure point exists,
- generating low-confidence plan drafts,
- and synthesizing activity patterns in natural language.

AI must not own:

- completion truth,
- execution truth,
- clean-data status,
- confidence authority,
- user identity,
- final scheduling authority,
- or whether a passive session enters calibration.

The deterministic/probabilistic substrate owns those.

## 13. Exposure Contamination

Embedded academic instrumentation increases exposure risk because Lyra can now
intervene while the user is studying.

Intervention examples:

- pause prompt,
- resume prompt,
- strategy suggestion,
- "switch to exam problems" suggestion,
- "this looks fragmented" mirror,
- "move study earlier" suggestion,
- motivational feedback,
- comparative feedback.

Every intervention must be registered, logged, and exposure-classified before
any downstream behavior is treated as baseline.

Suggested contamination classes:

| Class | Example | Contamination strength |
| --- | --- | --- |
| passive observation | page opened, video played | none/low |
| reflective mirror | "you spent 38 min here" | low-medium |
| strategy suggestion | "try exam problems first" | high |
| schedule suggestion | "move this earlier" | high |
| adaptive redirect | "stop lecture, do summary" | very high |
| motivational feedback | "keep up momentum" | medium/high |
| comparative feedback | "faster than other students" | very high |

Comparative feedback should be avoided in V1. It introduces social comparison,
pressure, and strong behavior distortion.

## 14. Required Exposure Record

Any academic execution intervention must log:

- surface id,
- truth class,
- signal targets,
- evidence snapshot,
- copy shown,
- timing,
- user response,
- downstream target window,
- and contamination horizon.

Example:

```json
{
  "surface_id": "academic.session.fragmentation_mirror",
  "truth_class": "interpretation",
  "signal_targets": ["attention_fragmentation", "study_strategy"],
  "evidence_snapshot": {
    "resource_id": "lecture_04",
    "idle_gaps": 5,
    "rewinds": 7,
    "active_minutes": 42,
    "deadline_days": 3
  },
  "copy": "This lecture session looks fragmented. Want to pause the block or switch to a shorter recovery task?",
  "user_response": "paused",
  "contamination_horizon": "academic_strategy_7d"
}
```

Without this, Lyra risks learning from behavior it caused.

## 15. Collaboration Boundary

If Lyra is embedded inside Baseet, Lyra must retain ownership of the execution
loop:

- generate/edit plan,
- start block or infer session candidate,
- mark done/partial/skipped/unknown,
- reschedule,
- record actual duration,
- collect minimal reflection at natural boundary,
- recalibrate estimates.

If Baseet only asks Lyra to generate a plan, Lyra becomes a scheduler plugin.
That is weak.

If Baseet gives Lyra structured context plus execution outcomes, Lyra remains
the substrate.

That is strong.

## 16. Strong Final Architecture

```text
Baseet / Moodle / Calendar / Manual Import
        ->
Academic Structure Adapter
        ->
Lyra Pressure + Plan Layer
        ->
Execution Surface / Session Candidates
        ->
Observed Traces + User Confirmation
        ->
Cortex Projections
        ->
Exposure-Aware Synthesis
        ->
Bounded Strategy Suggestions
        ->
Measured Outcomes
        ->
Adaptive Confidence
```

AI is allowed at the edges:

- structure extraction,
- complexity classification,
- copy/synthesis generation.

The middle remains evidence-bound.

## 17. Non-Negotiable Rule

```text
External systems provide structure.
Lyra requires user intention for calibration.
Passive activity informs effort and engagement, not planning accuracy.
```

This resolves the product loop:

- no product merger,
- no Baseet dependency lock-in,
- no fake stopwatch inference,
- no fake delta,
- no AI slop,
- no collapse of academic activity into learning truth.

With execution outcomes, Lyra becomes evidence-based adaptive execution
intelligence.

Without execution outcomes, Lyra is only a planning heuristic.

## 18. Institutional Wedge Is Not Product Identity

The academic-provider direction can feel disappointing because it makes Lyra
look more B2B or institutional than the original personal cognitive instrument.

That emotional reaction is important. It protects the soul of the project.

The key distinction:

```text
The first scalable wedge may be institutional.
The product identity must remain execution intelligence.
```

Institutional systems provide:

- structure,
- cohorts,
- repeated environments,
- obligations,
- distribution,
- and enough context for the substrate to bootstrap.

But Lyra should not become:

- an LMS,
- a content aggregator,
- an academic portal,
- a dashboard company,
- or generic study-planner middleware.

The institutional layer is operational fuel. It is not identity.

## 19. Integrated Layer, Not Integrator

The earlier mental model was:

```text
Lyra integrates everything.
```

The stronger model is:

```text
Lyra is the execution-intelligence layer that other systems can embed.
```

That shift matters.

Lyra does not need to own:

- content,
- files,
- lectures,
- LMS infrastructure,
- course aggregation,
- or academic truth.

Lyra owns:

- intention,
- execution,
- drift,
- recovery,
- reflection,
- recalibration,
- exposure-aware synthesis,
- and adaptive confidence.

This makes the architecture cleaner and more provider-independent.

If Baseet disappears, Moodle changes, or a new academic system appears, Lyra
still survives because the substrate is execution intelligence, not
aggregation.

## 20. Strategic Category

Lyra is not merely infrastructure.

Infrastructure usually means:

- storage,
- transport,
- APIs,
- middleware,
- or generic plumbing.

Lyra is closer to:

```text
adaptive execution interpretation beneath structured environments
```

or:

```text
the layer that turns structure into adaptive execution intelligence
```

Possible upstream systems:

| Upstream system | Lyra layer |
| --- | --- |
| Baseet | academic execution |
| Moodle | study pressure and assignment execution |
| Google Calendar | availability-aware planning |
| Notion | execution calibration over planned work |
| Jira / Linear | engineering workload drift |
| Corporate LMS | training execution |
| ADHD planner apps | adaptive reflection and recovery |

The moat is not dashboards or AI summaries. Those commoditize quickly.

The moat is:

- longitudinal execution traces,
- adaptive calibration,
- exposure-aware synthesis,
- drift modeling,
- local correction factors,
- and the discipline to avoid fake intelligence.

## 21. Distribution Without Losing The Soul

The provider-embedded shape solves a real distribution problem.

Instead of asking millions of users to manually instrument themselves from
scratch, Lyra plugs into environments where execution already happens.

That does not kill the original reflective system. It may preserve it better.

The original personal layer survives through:

- execution awareness,
- behavioral legibility,
- drift reflection,
- adaptive calibration,
- recovery affordances,
- and synthesis from the user's own traces.

The rule:

```text
Do not let institutional wedge become institutional identity.
```

The sacred center remains:

```text
execution intelligence,
behavioral calibration,
reflective synthesis,
adaptive evidence.
```

Not:

```text
LMS integration.
```

## 22. Adaptive Scheduler Survival

The adaptive scheduler vision survives more realistically in this architecture.

It becomes grounded in:

- real environments,
- real obligations,
- real workload topology,
- real availability constraints,
- and eventually real execution traces.

That is stronger than:

```text
AI invents plans in a vacuum.
```

The conceptual breakthrough:

```text
environment structure != execution intelligence
```

Once separated, the project becomes:

- cleaner,
- more scalable,
- more portable,
- and more strategically coherent.

Lyra did not become a generic integrator.

Lyra became the adaptive execution substrate.

## 23. Beyond Academia

Academia is the first clean wedge because it has visible structure:

- lectures,
- tutorials,
- labs,
- assignments,
- quizzes,
- exams,
- deadlines,
- and study blocks.

But the substrate is not academic-specific.

The general pattern is:

```text
obligation / intent
  -> execution attempt
  -> actual time / interruption / completion
  -> drift
  -> recalibration
```

That pattern appears in many environments:

- academic work,
- engineering work,
- project management,
- corporate training,
- clinical or operational workflows,
- creative production,
- and personal planning.

The academic version is:

```text
quiz / lecture / assignment
  -> planned study block
  -> study execution
  -> partial/done/skipped/unknown
  -> estimate drift
  -> recalibrated academic planning
```

The organizational version is:

```text
project commitment / ticket / meeting / training module
  -> planned work block
  -> work execution
  -> interruption / handoff / completion
  -> estimate drift
  -> recalibrated team or individual planning
```

## 24. Organizational Execution Intelligence

In organizations, Lyra could help teams understand work time more honestly.

The valuable questions are not:

```text
Which employees are slacking?
```

The valuable questions are:

```text
Where are our estimates systematically wrong?
Where is workload compression happening?
Which meetings destroy execution blocks?
Where do handoffs create drift?
Which project types exceed planned capacity?
Where does planned work fail before execution?
```

The unit of analysis should often be:

- team,
- workflow,
- project type,
- meeting topology,
- handoff pattern,
- planning process,
- or organizational system.

Not individual blame.

This makes the organizational version of Lyra an execution reality layer, not
a productivity surveillance layer.

## 25. Anti-Bossware Boundary

The organizational version is powerful and therefore dangerous.

Hard rule:

```text
Lyra helps workers and teams understand work reality.
Lyra must not become bossware.
```

Forbidden product shapes:

- rank employees by focus time,
- expose raw individual activity streams to managers by default,
- infer laziness or motivation,
- use idle time as misconduct evidence,
- create hidden productivity scores,
- punish people for missing planned estimates,
- monitor private work without clear consent,
- or convert execution traces into individual surveillance dashboards.

Allowed product shapes:

- aggregate estimate drift by project type,
- show meeting-load effects on execution capacity,
- identify workload compression at team level,
- show process bottlenecks,
- help individuals recalibrate their own plans,
- help teams plan more realistically,
- surface capacity mismatch without blame,
- and preserve worker-controlled personal views.

The organizational version must be designed around:

- consent,
- visibility,
- aggregation,
- worker trust,
- privacy-preserving defaults,
- role-based access,
- and anti-surveillance constraints.

## 26. Organizational Evidence Boundary

The same evidence hierarchy applies.

| Evidence class | Academic example | Organizational example | Interpretation |
| --- | --- | --- | --- |
| External obligation | quiz deadline | project deadline / sprint commitment | pressure source |
| Structured work item | lecture/tutorial | ticket/module/document | workload structure |
| Calendar constraint | class/event | meeting/event | availability constraint |
| Planned block | study session | focus block / work session | intention |
| Passive activity | lecture page open | ticket/doc active | weak activity evidence |
| Timer/session trace | study timer | focus/work timer | execution evidence |
| Outcome | done/partial/skipped | done/blocked/handoff/unknown | completion truth candidate |
| Drift | estimate vs actual | estimate vs actual | calibration signal |

Critical rule:

```text
Passive workplace activity is not work quality.
Passive workplace activity is not employee value.
Passive workplace activity is not misconduct evidence.
```

It may support:

- session reconstruction,
- interruption detection,
- meeting/workload analysis,
- and estimate calibration.

It must not become a hidden measure of human worth.

## 27. General Thesis

LyraOS is a provider-agnostic execution intelligence substrate.

Academic systems are one wedge.

Organizations are another.

The core is:

```text
intention vs execution under real constraints
```

Not:

```text
school planning
```

And not:

```text
employee monitoring
```

The product should scale by integrating with environments where work already
happens, while preserving the same research discipline:

- explicit provenance,
- uncertainty,
- exposure accounting,
- user correction,
- clean-data profiles,
- and a hard refusal to collapse behavior into identity or blame.

## 28. Category Emergence

The Baseet discussion clarified that LyraOS is not primarily:

- a student planner,
- an AI study assistant,
- a productivity app,
- or a content aggregator.

The stronger category is:

```text
execution intelligence under real-world constraints
```

Even sharper:

```text
Lyra does not optimize productivity.
Lyra models execution reality.
```

This is why the architecture kept evolving toward:

- provenance,
- exposure tracking,
- confidence,
- contamination handling,
- uncertainty,
- clean-data profiles,
- and falsifiability.

Without those constraints, a system that interprets human execution can become
AI surveillance slop very quickly.

Lyra's seriousness comes from resisting that collapse.

## 29. Universal Substrate

The substrate generalizes because many environments share the same execution
shape:

```text
intention
  -> execution
  -> interruption
  -> drift
  -> recalibration
```

Examples:

| Environment | Constraint structure |
| --- | --- |
| University | quizzes, exams, lectures, assignments |
| Software teams | tickets, deadlines, meetings, deploy windows |
| Consulting | client deliverables, calls, review cycles |
| Research labs | experiments, papers, protocols |
| Hospitals | shifts, handoffs, procedures |
| Manufacturing | operations, tasks, throughput constraints |
| Customer support | queues, escalations, response targets |

Each upstream system provides different structure, but Lyra's invariant remains
the same:

```text
planned work vs real work under constraints
```

## 30. Adapters To Structured Environments

Integrations should be understood as adapters to structured environments.

| System | Provides |
| --- | --- |
| Baseet / Moodle | academic obligations and resources |
| Jira / Linear | engineering obligations |
| Outlook / Google Calendar | time constraints |
| GitHub | execution artifacts |
| Notion | planning structure |
| Teams / Slack | interruption topology |

Lyra sits beneath these systems as the execution-reality layer.

It should not become dependent on any one provider.

## 31. Abstraction Collapse And Deeper Invariants

The project became clearer by shedding weaker abstractions.

| Old abstraction | Deeper invariant |
| --- | --- |
| productivity app | execution intelligence |
| content aggregation | workload topology |
| manual timers | execution evidence |
| Baseet competitor | provider-agnostic substrate |
| adaptive scheduling | execution-reality modeling |
| academia product | constrained-environment execution system |

This is not a loss of identity. It is the product becoming more precise.

The emotional arc matters:

```text
beautiful idea
  -> constraint collision
  -> disappointment
  -> weaker abstraction breaks
  -> deeper invariant emerges
  -> architecture becomes stronger
```

That is a healthy systems-discovery pattern.

## 32. Final Category Statement

LyraOS is a provider-agnostic execution-reality inference substrate.

It sits beneath structured environments, observes intention and execution
under constraints, preserves uncertainty and exposure provenance, and helps
people or teams recalibrate plans against reality without collapsing behavior
into identity, blame, or surveillance.

That is the category.

## 33. Provider-Specific Personalization Without Core Leakage

Provider-agnostic does not mean generic user experience.

Lyra can and should personalize features for each host application or upstream
provider. The constraint is where personalization is allowed to live.

The rule:

```text
Provider-specific UX is allowed.
Provider-specific inference core is not.
```

Each provider can expose a native-feeling surface:

| Provider / host | Native-feeling Lyra surface |
| --- | --- |
| Baseet | quiz pressure, lecture progress, tutorial coverage, exam-prep plans |
| Moodle | assignment pressure, submission recovery, deadline topology |
| Google Calendar | availability-aware planning and free-time mismatch |
| Jira / Linear | ticket drift, sprint pressure, blocked-work recovery |
| Notion | project intention drift and weekly plan review |
| Corporate LMS | training completion reality and module-pressure recovery |

Those surfaces may use provider vocabulary, provider icons, provider links,
and provider-specific copy.

But underneath, they must translate into the same substrate primitives:

```text
obligation
intention
execution event
outcome
interruption
exposure
drift
recalibration
```

The clean metaphor:

```text
Adapters translate local dialects.
Core reasons in one language.
Surfaces translate the result back into the local dialect.
```

This gives Lyra two things at once:

- native-feeling integrations that match the host product,
- and a durable inference substrate that does not collapse into provider
  spaghetti.

## 34. Three-Layer Personalization Model

Personalization should be split into three layers.

### Layer 1: Provider-Native Surface Personalization

This layer is allowed to be highly specific.

Examples:

- Baseet can say "Lecture 4" and "Quiz 2".
- Jira can say "ticket estimate" and "blocked by review".
- Moodle can say "assignment due" and "submission detected".
- Calendar can say "free window" and "meeting compression".

This layer optimizes comprehension and adoption.

It answers:

```text
What does this mean in the user's current environment?
```

### Layer 2: Provider-Blind Execution Substrate

This layer must remain stable across providers.

It should not contain branches like:

```text
if provider == "baseet"
if provider == "jira"
if provider == "moodle"
```

Instead, it should reason over normalized facts:

```text
external obligation exists
user accepted an intention
execution started
execution paused
outcome is partial
estimate drift widened
exposure occurred before behavior
```

This layer protects Lyra's research integrity.

It answers:

```text
What happened in execution reality?
```

### Layer 3: Provider-Native Result Translation

After Lyra reasons over the provider-blind substrate, the result may be
translated back into provider-specific language.

Examples:

```text
Baseet:
Quiz 2 prep looks compressed because 4 lectures and 2 tutorials remain.
```

```text
Jira:
This ticket type is drifting beyond planned focus blocks.
```

```text
Calendar:
Your current free windows are smaller than the accepted work plan.
```

The copy can be provider-native. The inference must stay provider-blind.

## 35. Personalization Boundary Examples

Allowed:

- Baseet-specific pressure cards.
- Moodle-specific connection and import UI.
- Jira-specific sprint drift language.
- Notion-specific weekly review prompts.
- Provider-specific icons, labels, links, and empty states.
- Provider-specific raw data normalizers.
- Provider-specific trust-state explanations.

Forbidden:

- Cortex branching on provider names.
- clean-data profiles admitting behavior because a provider said so.
- Exposure Ledger treating Baseet, Moodle, Jira, or Notion as special truth
  authorities.
- adaptive scheduling using provider-specific shortcuts instead of normalized
  intention and execution evidence.
- provider-specific copy implying stronger certainty than the substrate
  supports.

The sharp boundary:

```text
Providers personalize meaning.
Core preserves truth.
```

## 36. Why This Matters

If every app-specific feature leaks into the core, Lyra becomes an integration
mess:

```text
Baseet logic in Cortex
Moodle logic in clean-data profiles
Jira logic in adaptive scheduling
Notion logic in exposure interpretation
```

That path destroys portability and makes the research substrate hard to trust.

If the core becomes too generic at the surface, users lose local meaning:

```text
"external obligation"
"resource activity"
"execution artifact"
```

Those phrases may be correct internally, but they are bad product language.

The right architecture is therefore:

```text
specific at the edge
general in the substrate
specific again at the surface
```

That is how Lyra can support deep app-specific features without losing its
category-level identity.
