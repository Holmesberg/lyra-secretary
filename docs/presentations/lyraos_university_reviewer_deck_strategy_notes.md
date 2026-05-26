# LyraOS University Reviewer Deck Strategy Notes

**Status:** Presentation planning notes.
**Created:** 2026-05-23.
**Scope:** Reviewer-facing presentation strategy only. Do not treat this as a
runtime product spec, architecture refactor, or implementation authorization.

These notes preserve the working conversation around the university reviewer
deck after V2 and V3. The goal is to guide a future V4 deck without losing the
stronger product story, the reference-deck lessons, or the unresolved caveats.

## Current Deck State

- V2 was richer and more doctrinal, but too system-heavy and occasionally
  defensive.
- V3 is much cleaner and more practical, with a better pitch rhythm, but may
  slightly undersell the product.
- Do not edit V3 in-place. If revised, create V4 as a new artifact.
- V4 should be a balanced synthesis of V2 and V3:
  - keep V3's straightness, practicality, and 12-ish slide pitch rhythm;
  - restore some of V2's stronger product spine and conceptual energy;
  - keep technical depth in backups.

## Core Presentation Goal

The deck exists to win approval for a small Baseet-oriented pilot, not to
showcase every internal mechanism.

Every main-deck slide should help the reviewer arrive at:

```text
This is clearly useful for students.
It is scoped enough to pilot.
It is serious enough to trust.
```

The deck should not make the presenter carry the real value in their head. The
slides themselves should make the product arc obvious.

## Stronger Product Spine

The stronger hidden claim is:

```text
Lyra is not only helping students plan.
It is making the gap between intention and execution visible, repairable,
and eventually learnable.
```

This should be made explicit without making the deck abstract.

Suggested four-beat arc:

1. Students do not just need reminders. They need reality contact.
2. Lyra makes academic pressure legible.
3. When plans drift, Lyra turns that drift into recovery choices.
4. Over time, confirmed patterns make planning less fictional.

Potential high-level line:

```text
Lyra helps students maintain contact between intention, time, action, and
consequence.
```

Use this sparingly. It is a spine, not a slogan to repeat on every slide.

## First Slide Direction

Restore the stronger V2-style core promise because it is memorable and
product-shaped:

```text
Load becomes visible.
Plans become executable.
Drift becomes recoverable.
```

Recommended first-slide structure:

```text
LyraOS
Student-owned academic load, planning, and recovery.

Core promise:
Load becomes visible.
Plans become executable.
Drift becomes recoverable.

A workspace that helps students see the week, choose the next move, and recover
before pressure compounds.
```

## Slides And Concepts To Preserve

### Missing Layer

The Missing Layer slide was strong and should remain in V4.

It should explain that:

- LMS/Baseet shows academic structure;
- calendars show availability;
- task tools show intention;
- Lyra shows the relationship between academic load, execution, drift, and
  recovery.

This slide should sell Lyra as a new layer, not merely a planner.

### Pressure Map

Keep this as a product hero slide.

Strong line:

```text
Visible load is 9-14 hours: a range, not fake precision.
```

It communicates practical usefulness and epistemic maturity in one sentence.

### Recovery Moment

Keep the recovery wedge, but clarify the actual action.

Current phrase:

```text
done / partial / split / adjust
```

Potential clarification:

```text
Lyra asks the student to choose how the stale or missed session should be
recorded:
- mark done;
- mark partial;
- split remaining work;
- adjust the session duration.
```

Do not let this sound like magic state mutation. The product value is that Lyra
turns drift into a clear user decision.

### Insights

The early user sentence should return to the Insights slide:

```text
It made me more aware of where my time is being spent.
```

This is one of the strongest simple value signals. Put it near the screenshot.

The Insights screenshot should stay large, ideally on the right from near the
header to the bottom, with minimal text on the left. It must be readable enough
to inspect actual words.

### Evidence Before Claims

The V2 Slide 13 "Evidence Before Claims" was valuable, but should be backup
material unless the reviewer is technical.

Keep as a backup slide:

```text
Inputs -> provider-blind facts -> evidence gates -> claim boundary -> student
surfaces
```

If "ClaimCompiler" appears, gloss it as a "claim boundary" rather than leading
with internal terminology.

### Dogfooding And User Feedback

Dogfooding and user feedback are not just story. They are readiness methods.

They should be framed as:

- product discovery under real academic pressure;
- a way to surface edge cases before broader exposure;
- a feedback loop for stress-testing usefulness, workflow friction, and
  confusing prompts;
- part of technical scaling readiness alongside tests, browser smoke,
  kill-switches, and LyraSim.

## Slide 10 Direction

Avoid the casual phrase:

```text
built over ~40 days...
```

Use the more mature tone:

```text
The current prototype emerged through rapid iteration under real academic
pressure.
```

The timeline context can be explained verbally or in speaker notes:

- midterms;
- coursework;
- BCI hackathon;
- finals;
- dogfooding while building.

The point is not speed for its own sake. The point is reality-contact:

```text
The system sharpened because real use kept breaking simpler assumptions.
```

## Redundancy To Cut

V3 repeats the same ideas too often:

- pressure is visible;
- recovery is student-owned;
- Baseet provides context;
- Lyra avoids overclaiming.

After the Pressure Map and Recovery Moment, later slides should escalate:

- continuity across drift;
- compounding insight from confirmed use;
- university aggregate learning;
- pilot success metrics;
- ask.

## Undersold Value

V3 may understate three important values:

1. Lyra is a mirror, not just a planner.
   It shows where the week actually breaks.

2. Lyra creates continuity across slips.
   Most tools become stale when plans fail. Lyra makes drift the next
   interaction.

3. Lyra improves because reality leaves traces.
   Not through hidden monitoring, but through confirmed patterns over time.

## Brain Dump And Baseet

The brain dump feature may become less central for the Baseet module once task
supersession and deadline tracking are handled properly.

Do not delete or downplay it globally:

- It remains useful for non-Baseet modules.
- It remains useful when provider data is incomplete.
- It remains useful for messy human intent that does not originate from an LMS.

For the Baseet pilot, brain dump should be framed as optional fallback input,
not the core Baseet value.

## Baseet And Plugin/Middleware Framing

Slide 8 needs to make the middleware/plugin idea clearer.

Better framing:

```text
Baseet is the academic structure provider for this pilot.
Lyra is the planning and recovery layer above provider systems.
The same layer can connect to Moodle, Canvas, Calendar, or future work systems.
```

The point:

```text
Provider systems organize context.
Lyra helps students turn context into execution and recovery.
```

## Plugin Side Note

Big tech/plugin ecosystems usually do not require the host system to be open
source.

Common integration paths:

- public API;
- OAuth app;
- webhook integration;
- SDK/plugin framework;
- browser extension;
- LTI-style education integration;
- private partner API;
- repo access only when the plugin must be built inside the host codebase.

For Baseet:

- If Baseet exposes a stable API or integration contract, Lyra can integrate
  without direct repo access.
- If the plugin must live inside Baseet's frontend/backend, or if no stable API
  exists yet, repo access from Bassem would help a lot.
- The ideal ask is not "open source the repo"; it is:

```text
Can we define the smallest provider adapter contract for deadlines, courses,
resources, and optional progress candidates?
```

Then decide whether implementation belongs in Baseet, Lyra, or a thin
middleware adapter.

## Edge Cases To Keep In Mind

The presenter should not overpromise that all ambiguity is solved.

Known edge-case families:

- anomalous sessions far above or below baseline;
- one extreme task inflating averages;
- tasks superseding deadlines incorrectly;
- provider progress that looks like completion but is only context;
- duplicate/stale deadlines;
- ambiguous abandoned sessions;
- Baseet/module data that reduces manual entry but does not prove execution.

These should be backup or Q&A material, not main-deck friction.

## Workshop And Berlin Deck Lessons

Reference material in `docs/presentations/drive-download-20260523T104559Z-3-001.zip`
and `Berlin_Deep_Tech_Week_Pitch_Deck.pptx` suggests:

- story first, slides second;
- use large fonts and short, information-dense sentences;
- do not add too much information on slides;
- use storytelling and a unique structure;
- avoid too many details on a single topic;
- backup slides exist to answer follow-up questions without cluttering the main
  pitch;
- the prototype/pitch should focus on the first value moment;
- define the use case as user + goal + product + interaction;
- be specific and simplify so people understand;
- do not presume audience enthusiasm;
- show the first value moment before architecture.

Berlin deck style cues:

- dark clean background;
- one declarative title;
- one supporting sentence;
- 2-4 simple blocks;
- specific ask;
- fewer decorative systems;
- less symmetry-for-symmetry's-sake;
- no dense architecture until needed.

If there is a contradiction between internal preference and the workshop
guidance, prefer the workshop guidance for the reviewer deck.

## V4 Candidate Structure

Main deck should be 12-15 slides. Backup slides may follow, but total deck
should stay at or below 20 slides.

Candidate main flow:

1. Title / Core Promise
   Load visible, plans executable, drift recoverable.

2. Student Story
   Maya opens Lyra Sunday night with a compressed academic week.

3. The Missing Layer
   Existing tools store pieces; Lyra shows the collision between intention,
   time, action, and consequence.

4. First Value Moment
   Baseet/Moodle context plus optional brain dump becomes an explainable
   pressure map.

5. Pressure Map
   Product hero and range-not-fake-precision line.

6. Recovery Moment
   Missed session becomes a clear user choice.

7. Insights / Mirror With Memory
   Large screenshot and early user sentence.

8. Why Baseet Matters / Plugin Layer
   Baseet provides academic structure; Lyra provides execution/recovery layer.

9. Compounding Value
   Confirmed use turns repeated drift into better estimates and weak planning
   hypotheses.

10. Built Through Reality
   Rapid iteration under real academic pressure; dogfooding and feedback as
   readiness methods.

11. What The University Learns
   Aggregate workload realism, deadline clustering, recovery friction, pressure
   peaks.

12. Pilot Success Metrics
   Survey-first metrics plus supporting dashboard metrics.

13. The Ask
   Small opt-in Baseet-oriented demo cohort.

Optional main slide if 14-15 are needed:

- Student support options if repeated drift occurs.
- Current vs future-gated value if reviewer needs scope clarity before the ask.

## Backup Candidates

Backups should answer questions, not be presented by default:

- Data Access Model.
- Evidence Before Claims architecture.
- Research Rigor.
- LyraSim.
- Current vs Future-Gated.
- Student Support Integration.
- Technical Readiness / Scale.
- Repo-Grounded Evidence.

## Success Metric Direction

Use both survey-first numbers and dashboard metrics.

Primary survey metrics:

- planning clarity improved;
- pressure map helped prioritize;
- recovery prompt was useful;
- student understood where time was going;
- workflow felt low-friction;
- confirmation model felt trustworthy;
- student would keep using Lyra during deadline-heavy weeks.

Supporting dashboard metrics:

- activation rate;
- weekly active use;
- pressure map revisit rate;
- recovery prompt completion;
- unresolved stale session reduction;
- export/delete/settings discoverability;
- repeated use during deadline clusters.

Avoid success language like:

```text
when X feels wrong
```

unless it is formalized as survey data.

## V4 Tone Target

Keep:

- straightness;
- practicality;
- the pilot ask;
- positive access-boundary language.

Restore:

- core promise;
- Missing Layer energy;
- mirror / continuity / compounding value;
- early user sentence;
- evidence-before-claims backup.

Avoid:

- defensive language that introduces complaints before they exist;
- excessive governance in the main deck;
- AI-generated symmetry and filler cards;
- vague "safe" claims without product value;
- burying the student story under architecture.

