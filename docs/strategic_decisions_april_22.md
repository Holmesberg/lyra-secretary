# Strategic Decisions — April 22, 2026

One structural refactor plus a publishing-timing call. Grounded in the
2026-04-21 Google Calendar push (see
`strategic_decisions_april_21.md §6 / §6.1`) and the retention audit
after Spring School week 1.

---

## 1. Identity-Authorization Split — Settings → Integrations panel shipped

**Previous state (2026-04-21):** NextAuth's Google provider requested
`openid email profile + calendar.readonly` at sign-in. Every new
user's first interaction with Lyra was a Google consent screen asking
for calendar access. Two consequences:

1. **Testing-mode wall on every signup.** Because `calendar.readonly`
   is a sensitive scope, Google blocks consent from any account not
   on the OAuth app's test-user list. With only 5 test-user slots
   used so far, any new external user hitting the landing page
   couldn't sign up at all.
2. **Scope decision at the wrong moment.** Users on the landing page
   hadn't yet seen Lyra's value — asking for calendar access at that
   moment is a trust request without context.

**Clarified state (today):** Sign-in asks for identity only —
`openid email profile`, non-sensitive, no OAuth verification
required. Third-party integrations acquire their scopes
**incrementally**, user-triggered, from a new **Settings →
Integrations** panel. Each integration has its own Connect button,
its own consent screen, its own disconnect affordance.

**Data that forced the refactor (2026-04-22 activity audit):**

| Non-operator user | Signed up | Onboarded | Tasks | Returning | GCal connected |
|---|---|---|---|---|---|
| u3 mariamnasser | 04-16 | **No** | 0 | No | No |
| u4 ghadatawfik | 04-16 | 04-18 | 2 | No (mom, guided demo) | No |
| u5 t90seegg2006 | 04-17 | 04-18 | 3 | **Yes** (2 active days) | No |
| u6 medo.tamer | 04-17 | 04-20 | 5 | **Yes** (2 active days) | No |
| u7 meroo0jj | 04-18 | **No** | 0 | No | No |

**Zero of the external users have connected Google Calendar.** Every
one of them consented to `calendar.readonly` at sign-in and then
never used it. The scope was pure drag. Worse: 2/5 never completed
onboarding at all — the sign-in friction is a plausible contributor
to the 29% onboarding-bounce rate.

**Ship decision:** refactor today. The unblock (new users sign up
without a calendar consent screen) is immediate; the long-term
scaffold (unified Integrations panel with per-provider cards) is
reusable for Notion, ICS, Outlook, Gmail, Slack, and any future
OAuth-shaped provider.

**Architectural principles locked in** (see
`docs/integrations_architecture.md`):
- Sign-in scope is identity-only, forever.
- Every integration connects from Settings with its own consent
  moment and its own scope request.
- Refresh tokens stay server-side; client JS never sees them.
- External data stays out of the `task` table unless explicitly
  marked with an `external_source` field (protects H1 test set).
- Every new integration ships with a pre-registered kill criterion
  measured at a specific sample size.

**What changed in code (eight files):**
- `frontend/lib/auth.ts` — scope dropped to identity; removed
  refresh_token capture + `hasGoogleRefreshToken` surface.
- `frontend/app/(app)/layout.tsx` — removed the auto-handshake
  useEffect that forwarded the sign-in refresh_token.
- `frontend/app/api/calendar/setup/route.ts` — **deleted.** No
  longer has a source of tokens to forward.
- `frontend/app/api/integrations/google-calendar/connect/route.ts`
  — NEW, OAuth initiation with signed state (10-min TTL, HS256,
  purpose=`gcal_connect`).
- `frontend/app/api/integrations/google-calendar/callback/route.ts`
  — NEW, validates state, exchanges code, account-match check via
  `id_token.email`, forwards refresh_token to backend.
- `backend/app/api/v1/endpoints/integrations.py` — NEW, `GET
  /v1/integrations` returns per-user status per registered integration.
- `frontend/lib/integrations.ts`, `components/integration-card.tsx`,
  `components/integrations-section.tsx` — NEW, the UI pattern.
- `frontend/app/(app)/settings/page.tsx` — hosts the new section.

**Backward compatibility:** the operator's existing
`google_refresh_token` stays valid. `calendar_sync.py` is untouched.
No database migration. Users who were connected at the old sign-in
time remain connected without re-doing the OAuth flow.

**Manual operator step (required before live deploy):** add the new
redirect URI to the Google Cloud Console OAuth client:
- `https://lyraos.org/api/integrations/google-calendar/callback`
- `http://localhost:3000/api/integrations/google-calendar/callback`

---

## 2. OAuth Verification — deferred until retention signal

**Question raised:** should we submit the app for Google OAuth
verification now to escape Testing-mode?

**Answer: no. Wait for (a) VT-23 clearing its kill threshold, OR (b)
≥10 returning users, whichever comes first.**

**Rationale:**
- **Verification is weeks of back-and-forth.** Google requires a
  privacy policy at the verified domain, a demo video showing each
  scope's usage, homepage + ToS + domain verification, and often
  requests changes. 4–6 weeks of async review cycles during Spring
  School is the wrong investment.
- **VT-23 might kill the calendar feature.** Pre-registered kill:
  at n≥20 connected users, if <15% of past events get marked within
  7 days, the external-attendance signal is too sparse to justify
  ongoing investment. Verifying now risks burning effort on a
  feature we may deprioritize.
- **Incremental OAuth isolates the pain.** With Decision 1 shipped,
  only users who click "Connect Google Calendar" hit the test-user
  wall. Users who don't touch calendar are unaffected. The operator
  adds Testing-mode test users one at a time as real demand lands.
- **Retention signal first, verification effort second.** 2 returning
  external users is not a verification-worthy cohort. When n≥10,
  priorities shift.

**Pre-registered triggers to revisit:**
- VT-23 retention lift ≥1.25× at n≥20 → verify immediately.
- ≥10 users actively want to connect calendar and hit the wall →
  verify immediately.
- Non-calendar sensitive scope needed (Gmail, Drive) → verification
  bundle includes both.

**Deferred prep (low-priority, start in background):**
- Privacy policy at `lyraos.org/privacy` (route already exists;
  content scrub needed for OAuth-verification-ready wording).
- ToS at `lyraos.org/terms` (same).
- Demo video script for `calendar.readonly` scope usage (per
  Google's verification video requirements).
- Domain verification in Google Search Console (one-time).

These cost ~2 hours of prep work and are worth having ready so that
when the trigger fires, verification submission is same-day.

---

## 3. Retention data surfaced for clarity

During the review that triggered Decision 1, the activity audit
clarified the real cohort shape:

- **Operator alts:** u1 (main), u2 (asabryhafez — operator alt), u9
  (moriartyholmesberg — operator alt). Do not count toward external
  adoption.
- **Guided demo:** u4 (ghadatawfik — operator's mother) used the app
  once with guidance and couldn't return independently. Signal: a
  usability/independence gap for the low-tech-literacy segment, not
  churn. Investigation owed: what specifically blocked her from
  coming back?
- **Signup-to-no-onboarding:** u3 (mariamnasser), u7 (meroo0jj) —
  two users consented to terms, reached the app shell, and never
  created a task. 29% bounce. Investigation owed: what's on the
  first screen that doesn't land?
- **Real returning users:** u5 (t90seegg2006), u6 (medo.tamer). Both
  have 2 active days across their first 5 days, both hit "execute 1
  task then come back" successfully. These are the only two users
  currently generating real retention signal.

VT-23 threshold (n≥20 connected users) is ~18 external users away.
VT-17 (pause prediction) self-activates at 7 days per-user pause
history — only the operator has enough data to trigger it at all.

**Implication for product shape:** the first-screen + guided-demo
failure modes are more urgent than any feature work. Next-session
candidates:
- UX audit of the sign-in → first-task path (what does u3/u7 see?)
- Mom-proof onboarding test pass (what did u4 get stuck on?)
- First-week email nudge for users who onboarded but haven't come
  back in 48h.

None of these ship this round — but Decision 1 removes the
calendar-scope drag from that path, which is the biggest single
friction we can see today.

---

## 4. Instrument-Gap Audit (addendum 2026-04-22 evening)

Triggered by the structural stress test + feedback-loop audit late in
the day. The landing-page thesis (MANIFESTO §29: *"Are humans wrong
about themselves in a structured way that predicts failure?"*) has
been load-bearing since day 1, but several instruments that would
make it testable at deeper granularity don't exist yet. This section
catalogs the gap.

### 4.1 Missing schema fields

- **`Task.deadline_utc`** (nullable DateTime). Without a commitment
  anchor, the "failure" half of the thesis is un-measurable — we only
  see duration delta, not deadline miss. Macro tasks (thesis chapters,
  client milestones) are the natural carriers. Add via alembic 029
  when thesis-instrumentation work begins.
- **`Task.scope_bullet_count_at_plan`** + **`scope_bullet_count_at_execute`**
  (both nullable Int). Freezes the scope statement at plan time and
  re-samples at execute time; enables VT-22 scope-inflation regression.
  Parser: `^\s*[-*•·]` multi-line match on `description`.
- **Derived `is_macro`** flag (computed from `parent_task_id IS NULL AND
  has any child`) or explicit Boolean. Cheap; useful for cohort
  queries ("all macro tasks carrying a deadline").

### 4.2 Reassessment of "useless variables" under this thesis

From the 2026-04-22 stress test, these were flagged dead but should be
reconsidered given the landing-page thesis:

| Field | Old verdict | Reframe |
|---|---|---|
| `parent_task_id` | Rare use at current scale | Macro→sub structure is the deadline-bearing unit; load-bearing when thesis-instruments ship |
| `scope_outcome` | Written but unanalyzed | The post-hoc scope answer. Direct dependent variable for VT-22 |
| `task.description` | Free text, no analyzer | Raw scope statement. Bullet-count parser unlocks VT-22 |
| `Archetype` family | Zero assignments | Deferred not dead. Future deadline-temperament priors when intake ships |

Remaining dead-weight candidates under this thesis:

- `task.confidence_score` — no call site. Safe to remove (cheap
  migration, no user-visible change).
- `task.source` — voice path dead; `manual` vs `web` indistinguishable
  behaviorally. Keep for telemetry, don't build on it.
- `task.initiation_status` + `initiation_delay_minutes` — stuck on
  `not_started` for historical rows (LYR-050). Re-purpose as
  "lead-time-before-deadline" if useful; otherwise prune.
- `task.interruption_type`, `replaced_by_task_id`, `replaces_task_id` —
  low data volume. Infrastructure for a phenomenon that doesn't
  happen at current scale.
- `task.unplanned_reason` — marginal; audit for any read site.
- `stopwatch_session.pause_reason` / `pause_initiator` — legacy
  double-write since migration 020. Confirm no read sites then prune.

### 4.3 Research re-prioritization

Under the landing-page thesis, VT-22 (scope inflation) is the
load-bearing mechanism for testing it — not a companion hypothesis.
VT-17 (pause prediction) stays important but secondary; VT-21
(surface-exposure stratification) supports the "does the mirror
actually change behavior" question orthogonally. VT-23 (GCal
attendance) remains pre-registered but deprioritized — attendance
binaries don't carry scope depth.

See `docs/feedback_loops_closure_plan.md` for the concrete closure
specs on each loop. Loop 11 (deadline + scope-bullet instrument) is
the single schema commit that unblocks thesis-level testing and is
flagged P0 there.

### 4.4 Why this lives here, not in MANIFESTO

MANIFESTO is the thesis + rules + kill criteria. It's stable by
design — edits are dated and numbered (v1.7 as of April 17, 2026).
This instrument-gap audit is a *discovery* about what the current
schema does and doesn't support — not a thesis revision. It belongs
in the strategic-decisions stream, not the manifesto. When the
thesis-instruments actually ship (alembic 029 + scope parser), those
ship docs reference this section; if the thesis itself needs
tightening language, that goes into MANIFESTO.md as a proper revision.

---

## 5. Clustering Acceleration — Phase 5 → Trusted-User Week 2 (addendum 2026-04-22 late-evening)

Triggered by an external trusted-user's direct quote on 2026-04-22:
*"You know how ChatGPT just gets you? This app understands some of my
gaps but doesn't REALLY get me."* That is the cold-start personalization
problem we had pre-registered for Phase 5 (post-May 1). The operator
chose to accelerate it into trusted-user week 2 so the next external
user to sign up lands on a mirror that leans on population / archetype
priors instead of the current flat-1.0 fallback.

### 5.1 What ships in the acceleration

**Wave 1 — silent shrinkage** (ships today):
- Alembic 031 adds `completed` + `skipped_at` + `raw_responses` to
  `archetype_assignment` (distinguishes genuine survey-answered
  assignments from skip-defaulted rows)
- Pure-function `archetype_service.py` implements MEQ-5 / BFI-10 C /
  BSCS-Brief / GP-Short scoring + discipline_z composite + assignment
  algorithm per `docs/methodology.md §1`
- `bias_factor_service.py` extracted from `analytics.py` (no behavior
  change); hosts the new `blend()` function that wraps
  `_adaptive_calibration` with archetype-prior shrinkage
- `GET /v1/analytics/bias_factor/lookup` returns both `cell.bias_factor`
  (personal-only, diagnostic) and `bias_factor_final` (blended,
  canonical). Frontend nudge reads `bias_factor_final`
- `/insights` gains an operator-only diagnostic panel showing the blend
  components per query
- MANIFESTO v1.10 adds Rule 13 pre-registering the shrinkage formula,
  the 5 archetype priors, the `RESEARCH_PRIORS` dict, and the
  Diffuse-Average skip-path default — frozen at launch. VT-25
  (archetype-reveal narrative internalization) drafted inactive.

**Wave 2 — questionnaire UI + retrofit banner** (ships tomorrow):
- 29-item survey (MEQ-5 × BFI-10 C × BSCS-Brief × GP-Short) in
  `frontend/components/archetype-survey.tsx`
- Submission endpoint `POST /v1/users/me/archetype/survey` writes
  ArchetypeAssignment with `completed=True` + archetype_id
- Skip endpoint `POST /v1/users/me/archetype/skip` writes
  ArchetypeAssignment with `archetype_id='diffuse_average'`,
  `completed=False`, `skipped_at=now()`
- `(app)/layout.tsx` gate: after ConsentModal, before TutorialOverlay
- Alembic 032 adds `user.archetype_retrofit_dismissed_at`
- Settings retrofit banner for pre-launch users (u2, u5, u6); banner
  dismissal stamps the column; survey completion makes it disappear

### 5.2 Why silent shrinkage first, reveal UI in v1.1

Shipping shrinkage and reveal simultaneously confounds two separate
treatments: "does archetype prior help cold-start calibration?"
(H_shrinkage) vs "does knowing your archetype change how you plan?"
(H_reveal). They require separate test designs. Silent-first lets us
measure shrinkage's effect via bias_factor-MAE deltas on u5/u6 over
weeks 2–4, then ship reveal in v1.1 with a pre-registered within-user
A/B (Rule 11 framework adapted). Activation of VT-25 follows the
reveal ship, not Rule 13's ship.

### 5.3 What this acceleration explicitly does NOT ship in v1

- Reveal UI (session 5-7 archetype chip) — v1.1
- Reclassification check at sessions 15-20 — Phase 5.5
- 90-day auto-refit scheduler — Phase 5.5
- Per-cell `bias_factor_prior` table — deferred until we have
  empirical per-cell data for Gate 3 pass
- Automated Cronbach α monitoring (lit proxy used until n≥20) — Phase 5.5
- Arabic / Egyptian localization of instrument items — Phase 7+
- Per-archetype calibration_nudge copy variation — v1.2+

### 5.4 Gate status at acceleration

- **Gate 1 (Cronbach α ≥ 0.65 at first 20 users)** — blocking per
  `methodology.md §Gate 1`. Not evaluable at n=5. Lit-proxy used:
  published α values (MEQ-5 ≈ 0.70, BFI-10 C ≈ 0.62, BSCS ≈ 0.83,
  GP ≈ 0.87). Gate 1 evaluation deferred until n≥20 users have
  completed the survey; pre-registered fallback per `methodology.md:114`
  (BSCS+GP composite if BFI-10 C fails) covers the edge-case risk.
- **Gate 2 (silhouette ≥ 0.3 at n≥250)** — blocking for production
  archetype separability. Not evaluable until n≥250. Until then,
  5-archetype structure is treated as "descriptive heuristic backed by
  literature" per `MANIFESTO.md §Methodological note on profile
  taxonomy` line 285, not validated clusters.
- **Gates 3-5** — corrective. System launches with hardcoded priors;
  gates trigger improvements rather than blocks.

### 5.5 Kill criterion — clustering survey retention-cost

If signup-to-onboarding-complete drops below 55% over the 72 hours
following the Wave 2 flag-flip (NEXT_PUBLIC_ARCHETYPE_SURVEY_ENABLED=
true), flip the flag back to false and fall back to Settings-banner-only
distribution. 55% is the floor; current bounce rate is 29% per the
§3 retention-data clarification, so a 26-percentage-point drop is the
threshold above which the survey's retention cost outweighs its
personalization benefit for the cold-start cohort.

### 5.6 Licensing flag (operator pre-public-beta review)

Four instruments with varying licensing clarity:
- **BFI-10**: public domain (Rammstedt & John 2007 explicit)
- **MEQ-5, BSCS-Brief, GP-Short**: published in academic literature,
  research-use exemption typical but not explicit

For trusted-user week 2 dogfooding (n<10), legal risk is effectively
zero. For public beta (Phase 7+) the operator should:
1. Email the 2–3 uncertain-licensed authors as a courtesy disclosure
2. Ensure citations displayed in the survey footer + `/privacy`
3. Use items verbatim — no paraphrasing (strengthens the case)
4. Document the BFI-2 + SCS-5 (Maloney 2012) fallback in
   `docs/methodology.md` so an instrument swap is pre-planned if a
   takedown notice ever arrives
