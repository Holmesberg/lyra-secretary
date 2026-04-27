# LyraOS × BCI hackathon — video script v1

**Author:** drafted with Claude after April 27 G-Tech hackathon ("we built the actually-usable thing while teams who packaged a good narrative won")
**Project pitched as:** LyraOS-meets-BCI closing-the-loop demo. Layer 1 (LyraOS) is already built. Layer 2 (BCI integration) is the hackathon deliverable.
**Format:** ~3 minutes. Structure mirrors the system itself — punch first, depth second.
**Tone:** confident, tight, technical. No filler, no "we wanted to". Show the system doing things.
**Visual default:** screen-record of `/today`, `/calendar`, `/deadlines`, `/insights` while the voiceover plays. BCI segments cut to gel-cap + raw P300/SSVEP wave + decoded text.

---

## Cold open (0:00 – 0:15) — the WOW

VISUAL: split-screen.
- LEFT: human at desk wearing a BCI cap, eyes on screen, hands flat on the table (no keyboard, no mouse).
- RIGHT: the same screen — a chat with Claude advancing in real time. Words decode into the prompt as the user looks at them.
- BOTTOM TICKER: `LyraOS // 14:03 // adv SWE midterm // 47 min elapsed // bias_factor 1.6× — drift detected → wrap suggested`.

VOICEOVER (8 words):
> "Conversation with an LLM. Eyes only. No keyboard."

CUT TO BLACK. TITLE CARD.

> **LyraOS × BCI — closing the adaptive-scheduling loop.**

---

## Hook (0:15 – 0:40) — what is this thing actually

VISUAL: zoomed in on the running LyraOS day view. A timer is ticking. A deadline pill says "CO Final — in 18 days". A tiny chip says "you usually wrap by 1.4× planned — at 96 min now".

VOICEOVER:
> "LyraOS is a measurement-backed scheduler. It learns how long you actually take, not how long you think you'll take. It knows you overrun by 60% on academic work and 20% on workouts. It nudges you when you're drifting. The model is *yours* — derived from your own data, not from a population average."

> "Until today, the model only updated when you logged. That's the bottleneck. People forget to log."

> "We closed the loop with BCI."

---

## Build phases (0:40 – 2:00) — depth, layered

CHAPTER MARKER on screen, large mono font:

### `// PHASE 1 — DETERMINISTIC BACKEND`

VISUAL: terminal output of FastAPI starting; Postgres schema diagram (10 tables) zooming in on `task`.

VOICEOVER:
> "Phase 1: a deterministic FastAPI backend. Postgres, Alembic-tracked schema, single-mutation authority through TaskManager. Every state transition is enforced by the state machine. Every write is auditable. **Boring on purpose.** Without a deterministic substrate, no measurement claim survives contact with reality."

### `// PHASE 2 — MEASUREMENT`

VISUAL: a task being created, started, paused, resumed, stopped. Numbers update.

VOICEOVER:
> "Phase 2: dense measurement. We capture planned-versus-executed duration on every task, every pause event with reason and initiator, every stopwatch session with sub-minute precision. The core metric is `duration_delta_minutes`: the gap between what you said and what you did."

### `// PHASE 3 — VALIDATED RESEARCH`

VISUAL: MANIFESTO.md scrolling — Rule 13, Rule 17 §25a, hypothesis VT-22 visible.

VOICEOVER:
> "Phase 3: pre-registered research. Every measurement claim is frozen in a Manifesto file before the data lands. Kill criteria are written down in advance. We can't quietly move the goalposts. If the data falsifies the hypothesis, we say so."

### `// PHASE 4 — ADAPTIVE ML LAYER`

VISUAL: bias_factor cell heatmap (category × time-of-day), shrinking toward research priors when sample size is low; archetype proximity bars updating live.

VOICEOVER:
> "Phase 4: a personal Bayesian model. Each `category × time-of-day` cell carries a bias factor — your overrun ratio for that work shape. When samples are sparse, we shrink toward population priors from time-estimation literature. When samples are dense, your data dominates. A posterior over five behavioral archetypes runs live, watching the pattern shift as you log more days."

### `// PHASE 5 — AI LAYER`

VISUAL: a chat with an LLM that has tool access to LyraOS — creating tasks, querying analytics, drafting reflections. Brief glimpse, not the headline.

VOICEOVER:
> "Phase 5: an LLM agent on top of the API. The model can read the user's history, plan, schedule, and reflect. The agent doesn't decide *for* the user — it decides *with* them, and every decision routes through the same audit-tracked endpoints a human would touch."

### `// PHASE 6 — CLOSING THE LOOP (BCI)`

VISUAL: the gel cap. Raw EEG. P300 waveform. SSVEP frequency tags overlaid on the LyraOS UI. The user fixates on a task; the cursor moves. They type a reflection without lifting a finger.

VOICEOVER (slower, this is the punch):
> "Phase 6: the loop closes. P300 picks up your intent. SSVEP routes your gaze. The agent reads both. LyraOS adapts in real time — re-prioritizing, suggesting wraps, capturing reflections — without a single keystroke. The bottleneck isn't logging anymore. The bottleneck is the speed of your own thought."

---

## What was on the line (2:00 – 2:30) — why this matters

VISUAL: cuts back to the operator's actual `/today` view. Real data. Real overruns. Real predictions.

VOICEOVER:
> "Most productivity tools are opinions disguised as software. LyraOS is the opposite — it's a measurement instrument that happens to be useful. The BCI layer makes it usable for people who can't type, and it makes it *fast enough* for people who can."

> "G-Tech engineers could use this themselves. Not as a hackathon prototype. As the thing they actually run their week with."

---

## Close (2:30 – 2:50) — the honest beat

VISUAL: side-by-side again. BCI cap on the left, LyraOS dashboard on the right. The two systems exchanging data. A small flag in the bottom corner: `Layer 1 shipped // Layer 2 in pilot // Layer 3 (real-time adaptive) — next hackathon`.

VOICEOVER:
> "We didn't win this one. We built the actual system instead of the narrative. Tomorrow that's a feature. Today it's a tradeoff — and we chose the system."

> "Next hackathon: real-time adaptive scheduling, BCI in the inner loop. The model updates while you work, not after."

CUT TO BLACK.

> **lyraos.org** *(small)*

---

## Production notes

- **First 15 seconds are non-negotiable.** Every other section can be trimmed. The cold open carries the WOW; everything after is depth for the judges who keep watching.
- **Phase chapter markers** are deliberately heavy — judges scan, they need anchor points. Mono font, large, full-width, hold for ≥1 second.
- **Voiceover pace ~140 wpm** for the build phases (slightly faster than usual conversational; conveys energy without rushing). Drop to ~110 wpm for the closing beat.
- **No music for the first 15 seconds.** The visual + voice does the work. Music can sneak in under the chapter cards and crescendo on Phase 6.
- **BCI footage:** prioritize the moment of *cursor moving without hands* over any waveform aesthetic. The judges have seen waveforms. They haven't seen a measurement-backed scheduler driven by gaze + intent.
- **Honest beat at the end matters.** Mentioning we didn't win flips the room — the judges who passed on us in the live round watch the video later and realize what they missed. Don't beg; just state it.

## Sequencing rationale (operator note)

The build phases land in the order the project actually shipped, which mirrors how real systems get built. That's the embedded argument: this isn't a demo we packaged in 48 hours. It's a real thing with a defensible substrate. The judges who liked the narrative-packaged demos will recognize it; the judges who knew better will respect it.

The Phase 6 punch is intentionally short — every word over ~30 has diminishing returns. The fact of *cursor moving without hands while the LyraOS bar updates* does most of the persuading.
