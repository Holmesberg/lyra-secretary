# Cross-Domain Breakthrough Audit

**Date:** 2026-05-20  
**Status:** literature-compression audit, not research validation.  
**Purpose:** Map LyraOS's current findings and doctrine against prior art in
HCI, personal informatics, mixed-initiative systems, JITAIs, control systems,
and human-AI uncertainty. This document counts architecture-level
breakthroughs, separates rediscovery from likely novelty, and names reading
gaps before more implementation.

This audit does not authorize new user-facing claims, new adaptive authority,
or stronger research language. It is a compression layer for the operator.

---

## 1. Bottom Line

LyraOS has made **15 breakthrough-grade moves** so far:

- **13 are already meaningfully documented** in `MANIFESTO.md`,
  `README.md`, `docs/behavioral_instrumentation_doctrine.md`,
  `docs/product_research_assumption_register.md`, provider/academic
  contracts, and `docs/parked_ideas.md`.
- **2 were under-documented before this audit:**
  1. the AI synthesis layer as a downstream evidence-translation surface, and
  2. the literature-compression loop as an operator methodology.

The strongest correction from this pass:

```text
The bottleneck is no longer idea generation.
The bottleneck is mapping intuition -> prior art -> Lyra primitive.
```

Lyra is not failing because its ideas are too speculative. It is at risk
because many correct intuitions are being rediscovered manually instead of
compressed through existing HCI, control, and behavioral-intervention
literature.

---

## 2. Breakthrough Register

| ID | Breakthrough | Current doc coverage | Cross-domain anchor | Status |
| --- | --- | --- | --- | --- |
| B1 | Execution-reality middleware substrate: external systems hold structure; Lyra models execution reality. | Strong: `README.md`, `MANIFESTO.md`, `behavioral_instrumentation_doctrine.md` | Suchman's situated action; CSCW articulation work; personal informatics integration/action stages | Core thesis |
| B2 | Exposure contamination doctrine: the system changes the behavior it measures. | Strong: `MANIFESTO.md`, Cortex contracts, tightened docs | JITAI/MRT intervention design; causal contamination in feedback systems | Core governance |
| B3 | Passive activity is not truth. | Strong: academic/provider docs, assumption register | Personal informatics bias, lived informatics, sensor-data sensemaking limits | Core measurement |
| B4 | Pressure map as immediate value before personalization. | Strong: academic pressure docs, assumption register | Personal informatics reflection/action gap; workload topology/situated planning | Product wedge |
| B5 | Product utility and research validity can be separated. | Strong: README, manifesto, assumption register | JITAI staged evaluation; mixed-initiative authority boundaries | Scaling guardrail |
| B6 | Action-first/execution physics framing. | Strong: behavioral doctrine | Situated action; control systems; dynamic behavior modeling | Ontology |
| B7 | Cortex/read-time canonicalization and clean-data profiles. | Strong: Cortex docs, tightened docs | Measurement validity; provenance-aware PI; uncertainty-aware XAI | Infrastructure |
| B8 | Contradictory signals matter more than isolated self-report. | Partial: H1/VT-22 docs, assumption register | Reflection vs rumination; metacognitive cue-utilization; personal data analysis gap | Keep, sharpen |
| B9 | VT-22 readiness inversion: high readiness may predict scope-inflation risk, not capacity. | Strong in manifesto, weaker in product docs | Planning fallacy limits; goal-setting; scope/ambition mediation | Emergent hypothesis |
| B10 | Cascade failure as sequence instability, not just retrospective insight. | Strong: manifesto and analytics; parked intervention exists | JITAI decision points; micro-randomized trials; control-system circuit breakers | Product priority candidate |
| B11 | Dirty provider data is expected, not exceptional. | Strong: provider contract and assumption register | Lived informatics; sensor data interpretation; PI bias | Adapter doctrine |
| B12 | Governance must precede adaptive authority. | Strong: manifesto and assumption register | Human-AI guidelines, trust calibration, mixed-initiative UI | Constitutional layer |
| B13 | Nonjudgmental execution language is load-bearing. | Partial/strong: assumption register, behavioral doctrine | Non-judgmental personal informatics; reflection vs rumination | Needs copy tests |
| B14 | AI synthesis belongs downstream of math/statistics, not inside truth authority. | Weak before this audit: only "synthesize cautiously" and "operator-only synthesis" existed | Vital Insight 2024; human-AI uncertainty communication; evidence-based sensemaking | Parked for later |
| B15 | Literature compression lag is an operator bottleneck. | Weak before this audit: only scattered notes about rediscovery | HCI design-space mapping; theory-to-system translation | New method rule |

Count rule: these are not "feature ideas." They are structural moves that
changed multiple downstream decisions.

---

## 3. Expanded Domain Map

### Core Load-Bearing Domains

| Domain | What Lyra is doing inside it | Prior-art anchors | Current documentation status | Main risk |
| --- | --- | --- | --- | --- |
| HCI / personal informatics | Reducing tracking friction, making execution traces legible, and moving users from collection to reflection/action. | Li/Dey/Forlizzi; Rooksby; Epstein; Baumer; Cho; Toebosch. | Strong, but terminology still thin. | Reflection becomes rumination or judgment. |
| Behavioral science / measurement | Testing intention-action gaps, planning fallacy, self-report limits, measurement reactivity, and intervention timing. | Buehler; Newby-Clark; Nelson/Hayes; Klasnja; Nahum-Shani. | Strong. | Treating low-n operator patterns as validated laws. |
| Control systems / cybernetics | Modeling execution as state, feedback, disturbance, correction, and instability propagation. | Wiener; Ashby; Conant/Ashby; Hekler; Carver/Scheier. | Partial. | Decorative "execution physics" language without state/control definitions. |
| Data / measurement science | Preserving provenance, clean-data admission, validity boundaries, and uncertainty propagation. | Messick; Kane; Wang/Strong; W3C PROV; Buneman. | Strong. | Clean data becomes a vibe instead of an explicit inference-specific profile. |
| Software systems architecture | Using adapters, event traces, read-time projections, temporal ordering, and runtime topology as measurement infrastructure. | Parnas; Lamport; event sourcing; stream processing; provenance databases. | Strong. | Product shortcuts bypassing the measurement substrate. |
| AI / human-AI systems | Keeping AI downstream of deterministic evidence; preserving uncertainty and user correction. | Horvitz; Parasuraman/Riley; Lee/See; Amershi; Liao; Vital Insight. | Partial-to-strong. | Fluent synthesis collapses uncertainty into narrative authority. |

### Important Adjacent Domains

| Domain | Why it matters | Missing terminology to add when relevant |
| --- | --- | --- |
| Cognitive ergonomics | Lyra is directly manipulating workload visibility, interruption timing, task switching, and cognitive offloading. | mental workload, interruption cost, task switching, cognitive offloading, NASA-TLX, ecological momentary assessment. |
| CSCW / organizational systems | Provider adapters and academic/workplace integrations become coordination infrastructure, not just personal tracking. | articulation work, boundary objects, awareness, handoffs, infrastructuring, breakdown repair. |
| EdTech / learning analytics | Academic Pressure Map sits near LMS analytics and student-risk dashboards. | self-regulated learning, learning analytics, educational data mining, mastery vs engagement, institutional ethics. |
| Neurotechnology / BCI | Future BCI claims depend on noisy state inference and closed-loop authority. | passive BCI, neuroadaptive systems, signal nonstationarity, neuroergonomics, mental privacy. |
| Privacy / security engineering | Behavioral traces are high-risk even when not formally health data. | contextual integrity, de-identification risk, purpose limitation, scoped consent, anti-surveillance architecture. |
| Philosophy of science / epistemology | The system makes claims from traces and must preserve falsifiability. | construct validity, Goodhart/Campbell/Lucas, proxy validity, theory-ladenness, epistemic humility. |

### Peripheral / Future-Relevant Domains

| Domain | Why to study it | Default stance |
| --- | --- | --- |
| Computational social science | Cohorts will eventually require panel data, multilevel models, heterogeneity, survivorship bias, and causal inference. | Future-gated; do not overfit small alpha data. |
| Digital phenotyping | Passive behavioral traces overlap with clinical/passive-sensing fields and their ethical failures. | Negative/guardrail reference unless explicit successor governance exists. |
| Persuasive technology | Lyra uses influence but must avoid captology/dark-pattern failure modes. | Study mostly to reject manipulative loops and preserve autonomy. |
| Systems neuroscience | Useful for dynamical-systems intuition and future neuroadaptive work. | Indirect; do not neurologize normal execution behavior. |

### Five High-Value Intersections

| Intersection | Lyra translation | Divergence |
| --- | --- | --- |
| HCI x behavioral science x control theory | Interfaces that observe and shape execution dynamics through feedback loops. | Lyra logs exposure and treats interventions as experimental surfaces, not neutral UI. |
| Measurement science x AI x epistemology | Deterministic evidence packets first; AI only translates uncertainty and competing hypotheses. | Most AI products collapse ambiguity; Lyra should preserve it. |
| EdTech x execution modeling | Academic systems provide obligations; Lyra models whether students can execute against them. | Lyra must not infer learning, mastery, or student risk from activity alone. |
| AI alignment x behavioral systems | Adaptive systems model human behavior longitudinally while preserving agency. | Alignment means honesty/contact with reality, not obedience or engagement. |
| Personal informatics x systems dynamics | Drift, pressure, recovery, interruption, and cascades become dynamic state transitions. | Lyra treats lapses/missingness as topology, not mere data failure. |

## 4. What Is Actually New

The individual components are mostly not new:

- planning fallacy,
- self-tracking friction,
- feedback contamination,
- mixed-initiative authority,
- JITAIs,
- personal informatics reflection,
- control-style adaptive loops,
- uncertainty-aware explanation,
- nonjudgmental self-tracking interfaces,
- and AI-supported sensemaking

all have prior art.

The likely novelty is the **composition**:

```text
execution-reality middleware
  + accepted-intention gating
  + exposure-aware clean-data profiles
  + pressure topology
  + sequence/cascade analytics
  + low-authority nonjudgmental UX
  + future downstream AI synthesis
```

That combination is meaningfully different from a normal productivity app,
but it should be presented as an integrated product/research architecture, not
as if each concept was invented here.

---

## 5. Current Data Against Doctrine

Current operator/cohort data is too small and contaminated to validate broad
claims. It is still useful as a direction-of-travel check.

| Finding | Current lean | Interpretation |
| --- | --- | --- |
| H1 signed self-report shift -> duration delta | Leaning falsification / demotion | The near-zero operator signal suggests discrepancy should not drive active automation. Keep as a diagnostic thermometer until user-value is tested. |
| Cascade propagation | Leaning validation as a product-relevant sequence signal | If `P(skip N+1 | skip N)` remains high after controls, first skip is a state-transition alert, not just an analytics insight. |
| Readiness inversion / VT-22 | Leaning emergent, not validated | High readiness may forecast scope-boundary loosening or outlier risk, not "more capacity." |
| Academic vs study distinction | Product-valid, research-unvalidated | The distinction is useful operationally: academic = external obligations/deadlines/classes; study = self-study execution. |
| Provider data as structure | Valid doctrine, unvalidated utility | Provider data is valuable context but must stay lower-authority until accepted intention/execution exists. |
| AI synthesis layer | Feasible but later | Strong conceptual fit, but should wait until deterministic evidence packets and exposure handling are mature. |

The main product implication remains:

```text
The first skip may be the highest-leverage intervention point.
```

The existing parked idea, "Cascade morning-skip intervention (VT-32
candidate)," already captures a morning-anchor version. The broader surface
should eventually be reframed as **Cascade Intercept / Sequence Disruption
Circuit Breaker**, with morning skip as one subtype.

---

## 6. Literature Mapping

### Personal Informatics And Self-Tracking

**Li, Dey, and Forlizzi (CHI 2010)** define personal informatics as stages:
preparation, collection, integration, reflection, and action. Their key
warning is that barriers cascade to later stages, and systems need a balance
of automation and user control.

Lyra mapping:

- brain dump/provider import = preparation + collection support,
- Cortex = integration,
- pressure map/insights = reflection,
- reschedule/recovery/cascade intercept = action.

Compression: Lyra has been intuitively reinventing this pipeline. Future docs
should map new features onto these stages before implementation.

**Epstein et al. (UbiComp 2015)** extend this with lived informatics: tracking
is embedded in everyday life, lapses, switching, and changing goals.

Lyra mapping:

- stale sessions, skipped tasks, dirty provider rows, and missingness are not
  edge cases. They are normal lived-informatics phenomena.

**Mols et al. (2017) personal informatics critical review** cautions that the
self-improvement hypothesis has limited empirical support and needs stronger
evidence.

Lyra mapping:

- never claim "tracking improves people" without controlled evidence.
- "mirror" is a product hypothesis, not a proven effect.

### Reflection, Rumination, And Nonjudgmental Interfaces

**Cho et al. (CHI 2022)** found commercial personal informatics apps often
under-support reflection relative to theory.

Lyra mapping:

- pressure maps must not stop at "look, data." They need action paths,
  correction paths, and confidence/provenance.

**Eikey et al. (2021)** distinguish reflection from rumination. Personal data
can trap users in self-blame when gaps between desired and actual state become
identity-laden.

Lyra mapping:

- low-authority language is not cosmetic. It is protection against rumination.

**Toebosch, Berger, and Lallemand (DIS 2024)** explicitly name
non-judgmental interfaces in personal informatics.

Lyra mapping:

- "execution drift" language is aligned with this newer HCI design space.
- copy tests should measure whether users experience clarity or judgment.

**Bentvelzen, Niess, and Wozniak (IMWUT 2023)** show derived metrics transfer
interpretive agency from user to tracker; medium abstraction and context can
support reflection better than context-free scores.

Lyra mapping:

- pressure load and execution multipliers should be rendered as contextual,
  editable estimates, not naked scores.
- the end-time correction fix is aligned with this: people reason in time
  landmarks, not raw minute arithmetic.

### Situated Action And Work Coordination

**Suchman (1987/2007)** argues plans are resources for situated action, not
literal blueprints.

Lyra mapping:

- "every plan is a hypothesis" is basically the product form of this.
- Lyra should model where plans meet circumstances, not assume failure is
  deviation from a perfect plan.

**CSCW articulation work** frames the work of making sure work can happen.

Lyra mapping:

- pressure maps, provider normalization, and recovery windows are articulation
  support, not merely scheduling.

### JITAIs, Micro-Randomized Trials, And Control Systems

**Nahum-Shani et al. (2018)** define JITAIs around decision points, tailoring
variables, intervention options, proximal outcomes, and decision rules.

Lyra mapping:

- cascade intercept needs a formal decision point: first skip / sequence
  rupture.
- tailoring variables: time of day, next anchor distance, task category,
  existing pressure, recent sleep if available.
- intervention options: decompression buffer, reduce scope, clear window,
  proceed as planned.
- proximal outcome: next-task start/completion, next 2-6h skip rate.

**Micro-randomized trials** are the natural evaluation design for small,
repeated, just-in-time interventions.

Lyra mapping:

- do not just ship cascade alerts. Randomize suppression or variant timing once
  enough data exists.

**Control systems engineering for behavioral interventions** supports the
idea of modeling dynamic, idiosyncratic responses rather than only static
between-person traits.

Lyra mapping:

- "execution physics" is directionally coherent, but Lyra should not use
  control-system language unless it defines plant, state, control input,
  disturbance, objective, and stability/over-control risks.

### Mixed-Initiative And Human-AI Systems

**Horvitz (1999)** frames mixed-initiative interaction as each agent
contributing what it is best suited for at the right time.

Lyra mapping:

- user owns goals and values;
- deterministic analytics own trace math;
- AI may synthesize evidence later;
- Lyra may suggest small reversible actions only when authority is earned.

**Amershi et al. (CHI 2019)** human-AI guidelines emphasize showing what the
system can do, how well it can do it, supporting dismissal/correction, and
learning cautiously over time.

Lyra mapping:

- this is almost exactly the authority ladder plus provenance/exposure.

**Vital Insight (2024)** is the closest anchor for the proposed AI synthesis
layer: visualization plus LLM-supported sensemaking over multimodal personal
tracking data, with experts iterating between direct representations and
AI-supported inferences.

Lyra mapping:

- keep AI downstream of deterministic evidence packets.
- AI should preserve competing hypotheses rather than collapse them.

**Recent uncertainty/XAI work (2024-2026)** reinforces that uncertainty must be
communicated and calibrated, but LLM uncertainty expression is still an active
research area.

Lyra mapping:

- AI synthesis must never invent confidence.
- confidence comes from analytics packets, not prose fluency.

---

## 7. Archived Lineage Recovered

The archive scan matters because several "new" ideas were already parked in
older language. The goal is not to resurrect everything, but to recover the
valuable lineage before it disappears.

| Recovered idea | Where it was already present | Current action |
| --- | --- | --- |
| Execution substrate before middleware language | `archive/hackathon_video_script_v1.md`; `archive/docs_history/complexity_stress_test_2026_05_01.md`; `docs/archive/legacy/history/LyraOS_evolution.md` | Treat as lineage for the current execution-reality middleware framing. |
| Exposure Ledger as causal firewall | `archive/prompts/lyraos_complexity_check_prompt.md`; `archive/appstore/summary_of_app.md` | Keep in current Cortex/product-research doctrine; do not leave only in archive. |
| Cascade interrupt prevention | `archive/FEATURES.md` captured first-skip/cascade metrics and skip-confirm warnings. | Reframe as Cascade Intercept / Sequence Disruption Circuit Breaker, not only morning-skip VT-32. |
| JARVIS/operator synthesis | `archive/docs_history/data_utilization_inventory_2026_05_02.md` and `docs/parked_ideas.md` | Keep as hypothesis discovery and operator-only synthesis until evidence packets mature. |
| Control-system policy update after error | `docs/parked_ideas.md` | Preserve the policy-update intuition, but avoid latent "internal faction" truth claims. |

Archive warnings:

- Older "dashboard" cascade surfaces are superseded; cascade math survives.
- Older LLM-as-planner/agent ambitions must not leak into non-operator
  product without exposure and authority gates.
- Any archived "first system" or "nobody measured" language is historical
  enthusiasm, not current external-review wording.

---

## 8. Failure Patterns To Track

| Failure pattern | Domain source | Lyra protection |
| --- | --- | --- |
| Proxy becomes truth | Learning analytics, digital phenotyping, measurement validity | Activity is evidence, not learning/focus/effort/identity. |
| Metric corruption | Goodhart/Campbell/Lucas, persuasive systems | Keep metrics descriptive; avoid engagement/compliance targets. |
| Exposure contamination | Self-monitoring reactivity, JITAIs, causal inference | Exposure ledger, no clean baseline learning without exposure context. |
| Context collapse | Privacy/contextual integrity | Keep academic, productivity, health, identity, and institutional claims separated. |
| De-anonymization fantasy | Privacy/security | Treat sparse behavioral traces as potentially identifying even after redaction. |
| Paternalistic EdTech | Learning analytics ethics | No teacher/admin risk scoring from student execution traces without new governance. |
| Neuroadaptive overreach | Passive BCI/neuroethics | BCI remains future-gated, complementary, and never truth authority. |
| Fluent AI certainty | Human-AI/XAI | AI synthesis must cite evidence packets, alternatives, and confidence provenance. |
| Rumination loop | Personal informatics reflection research | Nonjudgmental copy plus repair paths, not identity labels or shame. |

---

## 9. Terminology Mapping

| Lyra term | Adjacent literature term |
| --- | --- |
| execution-reality layer | joint cognitive system, ecological interface, personal informatics substrate |
| plan as hypothesis | situated action, implementation intention, self-regulated learning plan |
| execution drift | control error, prediction error, plan-action gap |
| exposure ledger | intervention provenance, treatment exposure, audit trail, measurement reactivity log |
| clean-data profile | validity filter, exclusion rule, construct-validity boundary |
| pressure map | learning analytics dashboard, workload model, decision-support display |
| missingness as signal | informative missingness, avoidance trace, nonresponse behavior |
| earned adaptation authority | calibrated automation, human-in-the-loop control, uncertain objective alignment |
| no identity labels | anti-essentialist classification, posterior not persona, classification caution |
| AI role boundary | non-authoritative model assistance, decision support, provenance-constrained inference |

---

## 10. Documentation Gaps Found

| Gap | Current state | Recommended home |
| --- | --- | --- |
| Literature compression loop | Not explicitly documented before this audit. | This doc; later short section in `docs/research_mapping.md`. |
| AI synthesis layer boundary | Mentioned only as "synthesize cautiously" / operator synthesis. | Keep later; add to parked ideas or future architecture only when implementation is near. |
| Cascade intercept as broad product priority | Morning-skip subtype exists in `docs/parked_ideas.md`; archive has stronger first-skip/cascade interrupt lineage. | `docs/parked_ideas.md` when revisited; do not implement yet. |
| Nonjudgmental interface prior art | Low-authority doctrine exists, but DIS 2024 paper is not cited. | `docs/research_mapping.md`. |
| Reflection vs rumination | Psychological safety doctrine exists, but rumination risk is not named. | `docs/product_research_assumption_register.md` or copy review docs. |
| Control-system terminology guard | "Execution physics" is strong, but formal control terms are not yet bounded. | `docs/behavioral_instrumentation_doctrine.md` if control terms enter product/research prose. |
| EdTech/learning analytics boundary | Academic substrate exists but learning/mastery/institutional-risk vocabulary is thin. | `docs/archive/legacy/provider_academic/academic_execution_substrate.md`. |
| Digital phenotyping/passive sensing boundary | Provider/passive doctrine exists but the neighboring risk domain is not named. | `docs/archive/legacy/provider_academic/provider_adapter_contract.md`. |

---

## 11. Reading Pipeline Rule

Every new high-level Lyra idea should be captured in this format before it
mutates schema, product copy, or research doctrine:

```text
Idea:
Likely domain:
Known equivalent concept:
Closest papers/sources:
What is actually new in Lyra:
What must not be overclaimed:
Implementation consequence:
Kill/demotion criterion:
```

This prevents:

- overengineering,
- rediscovering solved ideas,
- treating borrowed concepts as novelty,
- and letting beautiful internal language outrun prior art.

---

## 12. Source Set Consulted

Core sources used in this audit:

- Li, Dey, and Forlizzi, "A Stage-Based Model of Personal Informatics Systems,"
  CHI 2010: https://www.ianli.com/publications/2010-ianli-chi-stage-based-model.pdf
- Rooksby et al., "Personal Tracking as Lived Informatics," CHI 2014:
  https://doi.org/10.1145/2556288.2557039
- Epstein, Ping, Fogarty, and Munson, "A Lived Informatics Model of Personal
  Informatics," UbiComp 2015: https://homes.cs.washington.edu/~jfogarty/publications/ubicomp2015.pdf
- Baumer, "Reflective Informatics," CHI 2015:
  https://doi.org/10.1145/2702123.2702234
- Mols et al., "Personal Informatics, Self-Insight, and Behavior Change: A
  Critical Review of Current Literature," HCI 2017:
  https://www.tandfonline.com/doi/full/10.1080/07370024.2016.1276456
- Cho et al., "Reflection in Theory and Reflection in Practice," CHI 2022:
  https://stephen.voida.com/uploads/Publications/Publications/cho-chi22.pdf
- Eikey et al., "Beyond self-reflection: introducing the concept of rumination
  in personal informatics," Personal and Ubiquitous Computing 2021:
  https://link.springer.com/article/10.1007/s00779-021-01573-w
- Toebosch, Berger, and Lallemand, "Non-judgmental Interfaces: A New Design
  Space for Personal Informatics," DIS 2024:
  https://orbilu.uni.lu/handle/10993/63699
- Bentvelzen, Niess, and Wozniak, "Designing Reflective Derived Metrics for
  Fitness Trackers," IMWUT 2023:
  https://research.chalmers.se/en/publication/534349
- Suchman, "Plans and Situated Actions," 1987/2007:
  https://course.ccs.neu.edu/cs5100f12/resources/reading/suchman-situatedactions.pdf
- Dourish, "What We Talk About When We Talk About Context," Personal and
  Ubiquitous Computing 2004: https://isr.uci.edu/node/1094.html
- Ackerman, "The Intellectual Challenge of CSCW: The Gap Between Social
  Requirements and Technical Feasibility," HCI 2000:
  https://www.tandfonline.com/doi/abs/10.1207/S15327051HCI1523_5
- Nelson and Hayes, "Theoretical Explanations for Reactivity in
  Self-Monitoring," 1981: https://doi.org/10.1177/014544558151001
- Klasnja et al., "Microrandomized Trials," Health Psychology 2015:
  https://doi.org/10.1037/hea0000305
- Wiener, "Cybernetics," MIT Press OA:
  https://direct.mit.edu/books/oa-monograph/4581/Cybernetics-or-Control-and-Communication-in-the
- Ashby, "An Introduction to Cybernetics":
  https://ashby.info/Ashby-Introduction-to-Cybernetics.pdf
- Hekler et al., "Tutorial for Using Control Systems Engineering to Optimize
  Adaptive Mobile Health Interventions," JMIR 2018:
  https://doi.org/10.2196/jmir.8622
- Messick, "Validity of Psychological Assessment," 1995:
  https://doi.org/10.1037/0003-066X.50.9.741
- Kane, "Validating the Interpretations and Uses of Test Scores," 2013:
  https://doi.org/10.1111/jedm.12000
- W3C PROV overview: https://www.w3.org/TR/prov-overview/
- Horvitz, "Principles of Mixed-Initiative User Interfaces," CHI 1999:
  https://erichorvitz.com/chi99horvitz.pdf
- Parasuraman and Riley, "Humans and Automation," 1997:
  https://doi.org/10.1518/001872097778543886
- Lee and See, "Trust in Automation," 2004:
  https://doi.org/10.1518/hfes.46.1.50_30392
- Amershi et al., "Guidelines for Human-AI Interaction," CHI 2019:
  https://haoyuma20492350.github.io/data/papers_pdf/AmershiSaleema2019Gfhi.pdf
- Liao et al., "Question-driven Design Process for Explainable AI User
  Experiences," 2020: https://arxiv.org/abs/2001.02478
- Nahum-Shani et al., "Just-in-Time Adaptive Interventions in Mobile Health,"
  Annals of Behavioral Medicine 2018:
  https://academic.oup.com/abm/article/52/6/446/4733473
- Collins et al., "The Micro-Randomized Trial for Developing Digital
  Interventions," 2020:
  https://arxiv.org/abs/2005.05880
- Conroy et al., "Personalized models of physical activity responses to text
  message micro-interventions," Psychology of Sport and Exercise 2019:
  https://www.sciencedirect.com/science/article/pii/S1469029218300633
- Li et al., "Vital Insight: Assisting Experts' Sensemaking Process of
  Multi-modal Personal Tracking Data Using Visualization and LLM," 2024:
  https://arxiv.org/abs/2410.14879
- Xu and Smit, "Using a complexity science approach to evaluate the
  effectiveness of JITAIs," 2023:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10373115/
- "Digital Twins for Just-in-Time Adaptive Interventions," JMIR 2026:
  https://www.jmir.org/2026/1/e72830
- Onnela and Rauch, "Harnessing Smartphone-Based Digital Phenotyping," 2016:
  https://www.nature.com/articles/npp20167
- Nissenbaum, "Privacy as Contextual Integrity," 2004:
  https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/
- Narayanan and Shmatikov, "Robust De-anonymization of Large Sparse Datasets,"
  2008:
  https://collaborate.princeton.edu/en/publications/robust-de-anonymization-of-large-sparse-datasets/
- Slade and Prinsloo, "Learning Analytics: Ethical Issues and Dilemmas," 2013:
  https://journals.sagepub.com/doi/10.1177/0002764213479366
- Gray et al., "The Dark (Patterns) Side of UX Design," CHI 2018:
  https://darkpatterns.uxp2.com/publication/chi18/
- Zander and Kothe, "Towards Passive Brain-Computer Interfaces," 2011:
  https://www.zanderlabs.com/resources/towards-passive-brain-computer-interfaces
