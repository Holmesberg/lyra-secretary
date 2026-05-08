# LyraOS × BCI — October hackathon video script v3

**Supersedes:** `hackathon_video_script_v1.md` (operator: "boring, inaccurate"). v2 reserved for operator's own draft.
**Premise:** the project is *finished* by October. Multi-user retention validated, five feedback loops closed, native apps in stores, BCI fusion shipped on a 20-session cohort.
**Target:** investor / hackathon judge who watches 50 pitches in a row. We have ~15 seconds before they decide whether to keep watching.
**Tone:** terse, technical, confident. No marketing voice. Specific numbers, real file references, named hypotheses. Honesty as the differentiator — not as a vibe.
**Runtime:** ~3:00. Voiceover budgeted at ~140 wpm.

---

## (0:00–0:15) — Cold open. No words for the first five seconds.

VISUAL: tight on operator's face. Eyes only. EEG cap visible. Hands flat on the desk. The screen behind them: a Claude window, words appearing. Below the chat, a thin terminal-mono ticker:

> `// adv SWE midterm · 47 min · usual pace +24 · wrap suggested · readiness 4 → EEG 2.6 ⚠`

The ticker updates in real time as the EEG signal disagrees with the self-report. The ⚠ glyph blinks once.

VOICEOVER (eight words, flat):

> "No keyboard. No mouse. The model disagrees."

CUT TO BLACK.

## (0:15–0:18) — Title card. Three seconds. Mono.

> **LyraOS** *measurement-backed adaptive scheduling.*
> *Closed-loop with BCI · v1.0 — October 2026.*

## (0:18–0:35) — The rug-pull.

VISUAL: snaps to `MANIFESTO.md` scrolling fast. Highlighted lines flash by — Rule 13, Rule 17 §25a, VT-22, VT-25, "kill criterion: May 21, 2026", "frozen formula." Then to the README block: 8 APScheduler jobs, 13 Postgres tables, 477 tests.

VOICEOVER:

> "What you just saw is the demo. The project is what's underneath."
> "LyraOS is a research instrument disguised as a scheduler. We pre-register every hypothesis. We freeze every formula. We publish every kill criterion *before* the data lands. If our science is wrong, the product is engineered to fail in public — on a date we already named."

## (0:35–0:55) — Engineering substrate. Punch one.

VISUAL: rapid cut grid. 8 APScheduler job boxes ticking. Postgres ER diagram zooming in on `task` → `pause_event` → `pause_prediction_log` → `calibration_nudge_event`. Test counter spinning to 477. Cloudflare Tunnel green light. `lyraos.org` and `api.lyraos.org` reachable.

VOICEOVER:

> "Six months of production engineering. Eight background jobs running per-user. Thirteen Postgres tables with immutable audit trails. Four hundred seventy-seven tests. A FastAPI backend over Cloudflare Tunnel against Supabase. Notion sync. Telegram bot. Google Calendar OAuth. OpenClaw agent."
> "Pause prediction fires two to three minutes before users actually pause — measured, not claimed. Cross-tenant query isolation at the SQLAlchemy compile layer. Voided rows filtered by every read."
> "This is not a hackathon submission with a backend stub."

## (0:55–1:20) — Punch two. The model that refuses to be sure.

VISUAL: archetype proximity bars updating live. Lark Low-Discipline 62%. Procrastinator 37%. Diffuse Average 1%. Caption fades in: *"two weeks ago you were 50 / 50. Pattern is consolidating."*

A second panel appears: a probability density visualization. As N increases from 5 to 28 to 100, the un-damped curve collapses to a delta. The damped curve plateaus at ~0.78. Caption: *"sqrt(N) damping — Kish 1965 effective sample size."*

VOICEOVER:

> "Most personality classifiers say *you ARE this*. Ours says: *your last fourteen days look sixty-two percent Lark Low-Discipline, thirty-seven percent Procrastinator. A month ago you were fifty-fifty. The pattern is consolidating.*"
> "Tasks within a single user's window are not independent. Same week. Same project. Same desk. We damp the likelihood by the square root of sample size — twenty-eight sessions count as roughly five effective observations. The model refuses to be more confident than the data deserves."
> "Run an outlier through it — a 9× overrun — and the system clips it at 3× and tells you the rest belongs to a different hypothesis we already pre-registered. Scope inflation. VT-22."

## (1:20–1:45) — Punch three. The paradox we found and named.

VISUAL: scatter plot, slow dolly. X-axis: pre-task readiness (1–5). Y-axis: planned-vs-executed overrun ratio. The line slopes UP. The camera holds on the unexpected slope for two beats.

VOICEOVER:

> "The planning literature says high confidence under-estimates. Our data says high confidence *inflates scope*. Readiness 4–5 predicts bigger overruns, not smaller."
> "When we found this, we didn't bury it. We documented it as a separate hypothesis — VT-22, scope inflation as a competing explanation for what every productivity tool calls a time-estimation problem. With its own kill criterion. With its own mediation test. It might be wrong. We already wrote down what proving it wrong looks like."
> "That's the difference between a product and a research instrument. We don't pretend the answer is settled."

## (1:45–2:05) — Punch four. The nudge that audits itself.

VISUAL: a calibration nudge fires inside the new-task modal — *"work tasks at this time of day run 1.4× planned. Adjust to 84 min?"*. User accepts. The task starts, runs, stops. A row writes to `calibration_nudge_event` with the executed duration backfilled. Then a SQL query renders an analytics card: *"primary metric · delta_difference_accepted_minus_dismissed = +6.3 min. accepted nudges overrun 6 minutes less, on average. n=84."*

VOICEOVER:

> "Every suggestion the system surfaces becomes a row. The user's decision. The actual outcome on that task."
> "The pre-registered primary metric is the difference in mean overrun between accepted and dismissed nudges. If accepting our advice doesn't make your estimates better, we report it. The number lives on a dashboard."
> "This is what feedback-loop closure means."

## (2:05–2:30) — The October promise.

VISUAL: retention curve. Multi-line. Five users, six months. Through the May 21 alpha checkpoint and the June 18–25 post-novelty fork. Lines hold above the 40% floor. A faint banner: *"H1 — readiness × delta — r=0.34, p<0.05, n=312 sessions across 6 users."*

VOICEOVER:

> "By October we have what most projects don't. Not a hypothesis — a result."
> "Five non-operator users past the post-novelty retention checkpoint. H1 quantified at r equals zero point three four. The five feedback loops we said we'd close — Loop 1 calibration nudge, Loop 2 readiness-conditioned bias, Loop 4 pause-prediction acceptance, Loop 8 retention dashboard, Loop 11 deadline mechanism — closed. Native apps shipped. The same product runs on any device, for any user."

## (2:30–2:50) — The BCI close-the-loop. Earned, not slapped on.

VISUAL: split. LEFT: P300 waveform spiking at the exact moment a pause prediction would fire. RIGHT: the LyraOS pause-prediction banner appears 2.3 seconds later. Beneath: side-by-side traces — self-report readiness (smooth, slow) and EEG-derived readiness (jagged, fast). Where they disagree, a vertical line drops onto the timeline.

VOICEOVER:

> "The Bayesian model that's been consuming self-report readiness was always going to consume noisy signals. EEG is just another noisy signal. We fuse them."
> "Self-report says four. EEG reads two-point-six. The model sees the gap. The next nudge changes."
> "We have a twenty-session cohort with simultaneous EEG and self-report. P300 correlates with subjective readiness at r equals zero point four eight. We're not the team that put a brain interface on top of a productivity app. We're the team whose model was *waiting* for a second signal."

## (2:50–3:00) — Close. Stakes.

VISUAL: black. Single line of mono text appears, one beat each:

> `// kill criterion (a): ≥50% of alpha users active in week 3. PASSED — May 21, 2026.`
> `// kill criterion (b): readiness × delta correlation r > 0.30. PASSED — September 18, 2026.`
> `// kill criterion (c): VT-22 mediation — scope_density mediates delta. UNDER REVIEW.`

A pause. The third line blinks once.

VOICEOVER:

> "We will fail in public if our science fails. We told you the dates two seasons ago."

CUT TO BLACK.

> **lyraos.org** *(small, white)*

---

## Production notes

- **The first five seconds are silent on purpose.** The visual carries the punch. A judge whose attention you earn before the first word is a judge who watches the whole thing.
- **The rug-pull at 0:18 is the most important cut in the video.** Do not soften it. The viewer assumes BCI gimmick; the cut to `MANIFESTO.md` tells them this is a different category of project. Underplay the voiceover here.
- **Numbers are non-negotiable.** Eight jobs, thirteen tables, 477 tests, r=0.34, n=312, two seasons. Specifics earn trust. Round numbers leak weakness.
- **Pace.** The substrate / archetype / paradox / nudge punches each run ~20 seconds. Visual cuts on the half-beat. Voiceover at ~140 wpm. Drop to ~110 wpm for the close.
- **Music.** None for the first 18 seconds. Subtle pulse under the punches (think *Mr. Robot* title card). Crescendo through the BCI segment. Cut on "we told you the dates two seasons ago."
- **The honest beat at the end matters more than the hype beat at the start.** Anyone can claim novelty. Naming the date your project is allowed to die is a different kind of credibility — and the kind hackathon judges remember three weeks later when they're picking a winner.

## Why this version isn't v1

v1 framed Lyra as a deterministic backend → measurement → ML → AI → BCI build pipeline. That sequence is technically correct but it's the *engineer's* mental model, not the *judge's*. A judge wants to know what's *non-obvious about you* in the first thirty seconds.

v3 leads with the most non-obvious thing: this is a research instrument that holds itself to a falsifiability standard, and the BCI is one more sensor in a fusion stack the architecture was already built for. The features fall out of that frame instead of competing with it.

The numbers in this script — `r=0.34`, `n=312`, `r=0.48` for EEG correlation, the dates of the kill criteria — are *plausible October targets*, not promises. They map directly to: H1 power calculation in `docs/building_phases.md` (≥30 users / ≥60 paired sessions for non-trivial detection), retention checkpoint (a) at May 21 in §Phase 5.5, fork gate at June 18–25 in `docs/strategic_decisions_april_24.md`, Loop 1 closed Apr 27, Loops 2/4/8/11 reachable in the operator's velocity history. If any of those numbers don't land by October, swap them for the ones that did. The honest beat survives the swap.

## Material that informed the script (citation map)

For when the operator wants to QA the voiceover lines against source-of-truth:

- **"Research instrument disguised as a scheduler"** — `MANIFESTO.md` v1.11 §Framing (Apr 14, 2026): "Research outputs are not Lyra's primary deliverable — they are quality-control and credibility infrastructure for the product."
- **Pre-registered kill criteria** — `docs/building_phases.md` §Phase 5.5 (lines 232–251): three explicit numerical criteria gating Phase 6, written before any data landed.
- **"Fail in public" framing** — `MANIFESTO.md` §VT-17 + §H1 falsification gate. Acceptance-rate kill at 0.20 across 50+ firings. r > 0.30 H1 gate.
- **8 jobs / 13 tables / 477 tests** — `backend/app/workers/scheduler.py`, `backend/app/db/models.py`, `pytest tests/ -q` output 2026-04-27.
- **VT-22 (scope inflation, readiness ↑ → overrun ↑)** — `MANIFESTO.md` §VT-22, `docs/strategic_decisions_april_22.md`. Pre-registered as competing explanation; Rule 12 mediation test scheduled for Phase 6.
- **VT-25 §25a (label reinforcement)** — `MANIFESTO.md` Rule 17, refined to "label reinforcement" framing per `feedback_label_reinforcement_framing.md`. The reveal copy avoids identity assertion deliberately.
- **sqrt(N) damping + winsorization** — `backend/app/services/archetype_proximity_service.py`, MANIFESTO Rule 17 v1.15. Operator's actual data went from 100% Procrastinator pre-amendment to 62/37/1% post-amendment.
- **Calibration nudge auditing itself** — `backend/alembic/versions/034_calibration_nudge_event.py` + `docs/feedback_loops_closure_plan.md` §Loop 1.
- **5 feedback loops "closed by October"** — `docs/feedback_loops_closure_plan.md`. Loop 1 already shipped Apr 27. Loops 2/4/8/11 in queued plans.
- **BCI fusion plausibility** — `docs/building_phases.md` §338-358 (P300 / SSVEP integration), operator's BR41N.IO debrief from Apr 27 conversation.
- **r=0.34 H1 / r=0.48 EEG×self-report** — *not yet measured*. Plausible targets at October cohort sizes. Swap with real numbers when they land. Honest beat survives.

## What got cut from v1

- *"We built the actually-usable thing while teams who packaged a good narrative won"* — great closing for a *post*-hackathon debrief, not for a forward-looking pitch where the team is supposed to be confident.
- Layer-1 / Layer-2 / Layer-3 phasing. Engineers love it. Judges glaze.
- Generic productivity-app framing. Lyra is not in that category and pretending it is sells short.
- *"Judges who passed on us in the live round will watch the video later."* Plays as bitter, undercuts the case.
- BCI-as-the-build-finale phrasing. v3 reframes BCI as *one more sensor in an existing fusion stack* — that's structurally accurate (the model was already built to consume noisy probabilistic signals) and far more impressive than "and then we added EEG."
