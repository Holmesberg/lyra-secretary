# Strategic Decisions — April 24, 2026

**Decision locked:** no native-platform investment (iOS/Android submission, hosting migration, Capacitor wrap, paid developer accounts, lawyer/privacy-policy spend) until the week-6-8 post-novelty retention checkpoint (Jun 18-25) returns green. Today ships two no-regret content edits that reduce immediate compliance exposure without committing to any future strategy.

---

## Context

Two threads converged today into one strategic question:

1. **The consent-layer conversation** (built on a prior session's 4-tier consent design, see `strategic_decisions_april_22.md` for the reference to that session) surfaced that the regulatory pain for peer-reviewed publication is large — IRB, Article 89 safeguards, lawyer-reviewed privacy policy, paid dev accounts. Several weeks of work plus $2-5k.

2. **The operator reframed the research goal**: falsification-for-internal-evidence, not publication. Paper 1 is not the target; knowing whether the mechanism works is.

That reframing collapses the exotic research-specific regulatory surface entirely. The remaining question: what does it take to push Lyra to iOS + Android as a product?

Answering that surfaced two gaps in the existing plan:

- The **May 21 retention-answer date** in `MANIFESTO.md §Shipping Philosophy` and `building_phases.md:24-26` is the *week-3* novelty window, not the product-market-fit answer. Per `dogfood_findings_living.md:190`, week-3 retention can be a QS-literature-documented novelty false positive. The real post-novelty checkpoint is **Jun 18-25 (week 6-8)**.

- The **three inference-claim surfaces** that define Lyra's distinctiveness — readiness→performance prediction (H1 thesis), pause prediction (VT-17), archetype-modulated bias_factor (Rule 13) — are the same three features that create the highest regulatory friction. Strip them → generic productivity app. Keep them → Article 9 / Apple 5.1 exposure. This decision cannot be made before retention validates; investing in compliance work for features that don't retain is the diminishing-returns trap.

---

## Decision — stage-gated sequence

### Stage 0 — Apr 24 → May 1 (now, alpha pre-launch)
Land the two no-regret edits described below. **Investment ceiling: $0.**

### Stage 1 — May 1 → May 21 (alpha proper, week-3 preliminary signal)
Cairo WOM continues from the existing 5-user cohort (u3-u7 per `strategic_decisions_april_22.md §1`). Tier 1 retention surfaces ship per `building_phases.md §Phase 4.5 Tier 1`. **Investment ceiling: $0.**

Week-3 retention is treated as preliminary signal, not decision gate.

### Stage 2 — May 21 → Jun 25 (week-6-8 post-novelty checkpoint)

Three forks:

- **GREEN** (≥40% of week-1 cohort still active at week 6-8): Stage 3 activates.
- **YELLOW** (week 3 green, week 6 declining): hedonic adaptation. Test middle-phase retention mechanisms per `dogfood_findings_living.md:192` before native work. **Do not build native.**
- **RED** (week 3 fails or week 6 collapses): pivot. Native investment saved.

**Investment ceiling through this stage: ~$100** (incremental hosting cost if the operator decides to move off laptop tunnel for reliability during alpha; still no dev accounts, no lawyer, no Capacitor).

### Stage 3 — Jun 25 → early Oct (only if Stage 2 green)
The 6-9 week native-submission plan activates:

- Phase 0 — copy + content layer (privacy policy, ToS, consent revisions, subprocessor list): Jun 25 – Jul 5
- Phase 1 — backend hosting migration (FastAPI off laptop to Fly.io/Railway; managed Redis): Jul 5 – Jul 19
- Phase 2 — Capacitor wrap + native push (APNs/FCM via plugin; device-token storage): Jul 19 – Aug 9
- Phase 3 — compliance surfaces (age gate, data export endpoint, Settings consent revocation UI): Aug 9 – Aug 16
- Phase 4 — store submission + rejection loop (dev accounts, Privacy Nutrition Label / Data Safety forms, screenshots, demo account): Aug 16 – early Sep
- **Go-live target: late Sep / early Oct**, aligning with the October BCI-integration decision noted in `dogfood_findings_living.md:271`.

---

## The two no-regret edits landing today

### Edit 1 — Rename `mental_fatigue` UI label → `Low focus`

- `frontend/components/active-timer-banner.tsx:16` — display label for pause-reason select
- `frontend/components/landing/live-data-strip.tsx:28,90` — landing-page chart label + caption
- **Backend enum value stays `mental_fatigue`.** Display label only changes. Internal analysis, pause_event rows, pause-prediction training data, VT-6 distinguishing analyses all unaffected.

**Why:** "Mental fatigue" in user-facing copy is the shortest path to an Article 9 / Apple 5.1 mental-state-inference-claim finding. The term appears nowhere in any scientific instrument — it's a UI label the operator chose. Changing it is cosmetic; keeping it is a tripwire for any future reviewer (store, regulator, or academic).

**How to apply:** Labels only. If the user sees it, rename it. If the analysis reads it, leave it.

### Edit 2 — Rewrite consent-modal copy to drop "research" framing

- `frontend/components/consent-modal.tsx` — both the description paragraph and the optional-checkbox label
- Optional checkbox **stays** (still writes `user.research_consent_at`, preserving the retention-on-deletion architecture at `models.py:333-334` + the delete flow at `endpoints/users.py:454+`), but the label reframes as product-analytics consent, not research consent.

**Why:** Publication is off the table for this cohort. Collecting data under a "research" framing while not actually publishing creates a retroactive consent-scope problem if the operator ever *does* want to publish later. Product-analytics framing matches actual intent and keeps the door open: re-consent-for-publication is a clean conversation if the operator's mind changes, whereas re-consent-to-narrow-down-from-research-to-product is not.

**How to apply:** Don't rename the `research_consent_at` column (needless churn) — just never describe it as "research" to the user again. Existing users who checked the box stay consented to the new product-analytics framing (no regression; the scope narrowed, not expanded).

### Deferred — dropping `description` field persistence

The prior session flagged `description` as "dark storage" (no backend analytics reads). Closer inspection today: `frontend/components/new-task-modal.tsx:706-716` parses description at edit-time to show "*N items, ~X min each based on your estimate*" when users type bullet lists. Dropping persistence would silently lose returning users' bullet lists on task re-view and kill the per-item estimate for already-saved tasks. **Not no-regret.**

Revisit when VT-22 Rule 12 mediation activates (empirically, when per-bucket n ≥ 30). The decision then is either (a) on-device scope_density extraction (keep the UI feature; stop persisting raw text; store only the item-count integer) or (b) explicit consent for VT-22-specific text collection. Both are bigger than today's scope.

---

## The archetype compliance fork — parked, not decided today

Archetype assignment is the single highest-risk-AND-highest-value compliance decision in the codebase:

- The 29-question MEQ-5 + BFI-10 C + BSCS + GP-Short battery (`archetype_service.py:202-217`) is clinical-grade personality phenotyping. It uses validated psychology instruments to classify users into one of five archetypes (disciplined_lark, disciplined_owl, lark_low_discipline, procrastinator, diffuse_average).
- GDPR Article 9 (sensitive category), Article 22 (automated decision-making, because the archetype modulates bias_factor via the Rule 13 shrinkage blend), Apple 5.1 health-research clause.
- Load-bearing: without archetypes, cold-start has no prior bias_factor. First ≈30 sessions are noise.

Three mitigation options, each with real cost:

- **Explicit Article 9 + Article 22 consent.** Heavy UX surface that adds friction at exactly the moment the Apr 22 OAuth refactor was designed to remove friction from. Compliant, but expensive on sign-up conversion.
- **Reframe as "preferences" survey** dropping the validated instruments. Loses the scientific validity claim, which is the reason to use those instruments in the first place.
- **Drop archetypes entirely.** Kills cold-start personalization; weakens differentiation; the archetype-reveal UI (`archetype-insights-card.tsx`) becomes dead code.

Decision deferred until Stage 2 returns green. At that point the real tradeoff is between (a) and (c); option (b) is probably dominated by (a) under Article 22's "meaningful information about the logic involved" requirement — if you have to disclose the logic, you might as well use the validated logic.

---

## Diminishing-returns math

If native investment happens **before** Stage 2 green:

- ~6-9 weeks of focused work
- ~$200-500/mo recurring (hosting, monitoring)
- ~$124 one-time (Apple + Google dev accounts)
- ~$500-2000 one-time (lawyer-reviewed or Termly-generated privacy policy)
- **Total: ~$2-5k cash + 200-300 hours of attention**
- If retention dies at week 6-8 → all sunk on a mechanism that didn't retain.

If **deferred** to Stage 3:

- Same total work, five weeks later.
- Spent against a validated mechanism, not a hypothetical.
- Every native feature gets specced against retention-proven UX rather than guessed UX.

The Apr 22 calendar-OAuth refactor cost ~1 day of work to undo a misplaced bet (scope decision made at the wrong moment — calendar consent at sign-in when no external user had value yet to give consent against). A native-app misplaced bet costs 6-9 weeks. Same lesson; ten weeks earlier is worth it.

---

## Calendar

- **May 21** — preliminary week-3 retention signal. Interpret, don't decide.
- **Jun 18-25** — week-6-8 post-novelty checkpoint. **This is the fork gate.** Add an explicit reminder; this date currently lives only in `dogfood_findings_living.md:190`.
- **Jul 5** — Stage 3 Phase 0 begins (only if Stage 2 green).
- **Early Oct** — native go-live target (conditional on every preceding gate).

---

## What this decision does NOT do

- Does not decide the archetype-compliance question. Parked until Stage 2 outcome.
- Does not commit to publication or non-publication. Falsification-for-internal-evidence is this cohort's intent; a preprint/arXiv route remains a low-cost fallback if the operator changes direction later.
- Does not block small compliance improvements during Stages 0-2 that are cheap and reversible (refining consent-modal copy further, fixing subprocessor disclosure in the privacy stub if/when it gets a real draft).
- Does not freeze Tier 1 retention-surface work. Tier 1 ships per the existing plan because it is the instrument being measured.

---

## Cross-references

- `MANIFESTO.md §Shipping Philosophy — Retention Mechanism First` (Apr 14, 2026)
- `MANIFESTO.md §Anonymized Retention Policy` (Apr 14, 2026)
- `docs/building_phases.md §Phase 4.5 Tier structure`
- `docs/dogfood_findings_living.md:190` — post-novelty week-6-8 metric (this is the load-bearing citation for the whole sequence)
- `docs/dogfood_findings_living.md:192` — middle-phase retention mechanism candidates (used in Stage 2 YELLOW fork)
- `docs/dogfood_findings_living.md:271` — alpha launch + BCI October timeline
- `docs/strategic_decisions_april_22.md §1` — calendar OAuth refactor as the sequencing precedent the Apr 22 data and reasoning validates
