---
authority: active-contract
may_authorize_code: false
runtime_owner: docs
supersedes:
superseded_by:
---

# Sequential Revelation Doctrine

**Status:** Active design doctrine.
**Created:** 2026-05-23.
**Purpose:** Preserve the principle that Lyra should stage complex truth at the
rate humans can metabolize it.

This document does not authorize new product features, AI synthesis, adaptive
scheduling, provider integration, public claims, or runtime mutation. It guides
presentation, onboarding, insight copy, recovery prompts, AI surfaces, and
future explanation design.

## Core Principle

```text
Sequential revelation is not simplifying truth.
It is staging truth at the rate humans can metabolize it.
```

Humans do not understand systems by receiving all true statements at once.
Humans understand through narrative causality:

```text
each revealed idea changes how the next idea is interpreted
```

Therefore sequence is not decoration. Sequence is meaning architecture.

Sequence is also an alignment mechanism. Revealing a claim, warning, pattern,
or recommendation too early can change incentives, self-interpretation, and
future behavior before the human has enough grounding to metabolize it. Lyra
uses sequencing to preserve agency and reality contact, not to hide truth.

## Why This Matters

Lyra contains more truth than any single surface should expose at once:

- intention;
- constraints;
- execution;
- interruption;
- drift;
- recovery;
- calibration;
- uncertainty;
- provider context;
- clean-data boundaries;
- exposure history;
- future hypotheses.

Dumping all of this together does not make Lyra more honest. It makes Lyra
harder to metabolize.

The task is not to hide truth. The task is to stage truth so the next step
becomes understandable.

## Rule

```text
Do not reveal a later-order explanation before the user has the frame needed to
interpret it.
```

Examples:

- Do not show research/governance machinery before the user understands the
  product value.
- Do not show adaptive or hypothesis language before the user understands the
  observed trace.
- Do not show a pattern label before enough sessions make the measurement state
  meaningful.
- Do not show provider ambiguity before showing the useful recovery choice.
- Do not show AI synthesis before deterministic evidence boundaries are clear.

## Product Translation

For user-facing surfaces, preferred sequence is:

```text
what happened
-> why it matters now
-> what can be done next
-> what remains uncertain
-> what may become learnable later
```

For reviewer or teaching surfaces, preferred sequence is:

```text
human problem
-> first value moment
-> concrete workflow
-> why this is different
-> safeguards / evidence / depth
-> ask
```

For LyraSim or technical reports, preferred sequence is:

```text
scenario
-> observed trace
-> expected boundary
-> finding
-> severity
-> replay / next action
```

## Non-Goals

Sequential revelation is not:

- hiding uncertainty;
- dumbing down the system;
- marketing gloss;
- withholding control;
- delaying important safety information;
- or turning evidence into a story that outruns the facts.

It is a cognitive pacing discipline.

## Relationship To Existing Doctrine

This doctrine connects existing Lyra principles:

- `intention -> execution -> drift -> interruption -> consequence ->
  recalibration` from behavioral instrumentation doctrine;
- trajectory integrity from the manifesto: repeated human-system interactions
  shape trajectory, so revelation order is part of authority design;
- progressive revelation as a measurement-state milestone;
- pressure map clarity before stronger recalibration;
- ClaimCompiler and output-surface boundaries;
- LyraSim's distinction between hidden truth, observable trace, and safe
  output;
- the product research principle that Lyra preserves inspectable contact
  between intention, constraint, action, and consequence.

## Surface Guidance

### Onboarding

Onboarding should reveal only the minimum needed to reach the first value
moment.

Good sequence:

```text
add/import work
-> see pressure
-> plan a session
-> recover from drift
```

Avoid:

- explaining the whole architecture;
- front-loading research doctrine;
- showing future automation before the user trusts basic recovery.

### Pressure Map

Pressure Map should first make the week legible.

Good sequence:

```text
cluster / range / trust state
-> suggested next safe action
-> assumptions
-> optional detail
```

Avoid:

- starting with why the model is uncertain;
- overloading the map with every evidence caveat;
- turning a visibility surface into a governance lecture.

### Recovery Prompts

Recovery prompts should reveal the immediate decision before the explanation.

Good sequence:

```text
This session looks incomplete.
Choose how to record it:
done / partial / split / adjust.
```

Then, if needed:

```text
This keeps future estimates from learning from a stale trace.
```

Avoid:

- long explanations before the choice;
- implying the system knows the true cause;
- using ambiguity as a reason to offer no action.

### Insights

Insights should reveal pattern strength progressively.

Good sequence:

```text
settling in
-> emerging pattern
-> medium confidence
-> high confidence
-> optional experiment
```

Avoid:

- identity labels before behavior validates them;
- high-confidence wording from low sample sizes;
- revealing too many patterns at once.

### AI / Synthesis

AI synthesis, if later authorized, must stay downstream of deterministic
evidence.

Good sequence:

```text
evidence summary
-> bounded interpretation
-> uncertainty / alternatives
-> suggested question or action
```

Avoid:

- fluent narrative that collapses uncertainty;
- treating synthesis as truth authority;
- jumping from trace to personality, mastery, or cognitive state.

## Presentation Guidance

Decks should not be documentation dumps.

The job of a pitch deck is to stage meaning:

```text
problem
-> first value
-> mechanism
-> trust
-> ask
```

Backup slides exist because not every true detail belongs in the main sequence.

Rule:

```text
If a slide is true but does not change how the next slide is understood, it is
probably backup.
```

## Failure Modes

### Truth Dump

Everything important is shown at once.

Result:

- user/reviewer cannot identify the product value;
- safeguards look like the product;
- the presenter must carry the meaning verbally.

### Premature Depth

Architecture, governance, or research rigor appears before the first value
moment.

Result:

- the audience evaluates complexity before usefulness;
- the system feels heavier than it is;
- objections are surfaced before desire exists.

### Narrative Overreach

The sequence becomes persuasive but outruns evidence.

Result:

- uncertainty collapses into a confident story;
- copy becomes more authoritative than the data;
- Lyra violates its own evidence boundaries.

### Infinite Deferral

Truth is delayed forever in the name of pacing.

Result:

- users cannot inspect assumptions;
- reviewers cannot verify boundaries;
- agency drops because explanations are unavailable.

## Test Question

For any Lyra surface, ask:

```text
What must the human understand first so this next statement lands correctly?
```

If the answer is unclear, the sequence is not ready.

## Design Standard

Good Lyra surfaces should satisfy all three:

- **Legible:** the first visible thing answers the user's immediate question.
- **Sequential:** each next detail changes the meaning of the next action.
- **Inspectable:** deeper truth remains available without overwhelming the
  first pass.

## Canonical Sentence

```text
Understanding itself is sequential.
```
