# Post-Week-1-2 Alpha Launch Survey
*Living document. Captured: 2026-05-01. Operator-curated.*

Trigger: send to each alpha user 7-14 days after their first task creation. Goal is qualitative + quantitative signal on whether Lyra worked, with specific attention to **affect** (did the app feel supportive vs judgmental?) and **behavior change** (did using Lyra actually change what users did?).

Format: one-page web form, mix of 5-point Likert + open text. Estimated completion: 4-6 minutes. Skip-allowed on every question.

---

## Section 1 — Affect & tone (4 questions)

These probe whether Lyra's copy + nudges felt supportive vs scolding. Operator-flagged 2026-05-01 after observing the resume-prediction copy ("well past your usual — still planning to come back?") landed as judgmental. The first question is the load-bearing one.

**Q1.** Did the app ever feel judgmental to you?
- 1 — Never, always felt supportive
- 2
- 3 — Neutral
- 4
- 5 — Often, felt like I was being graded

If 4 or 5: free-text "Which moment(s) felt judgmental?" (probe for specific surfaces — calibration nudges, archetype reveal, pause predictions, deadline warnings, etc.)

**Q2.** When the app told you something about your behavior (overruns, skipped tasks, paused sessions), how did it land?
- Recognition — "yeah, that's me, helpful to see"
- Curiosity — "huh, didn't know I did that"
- Defensiveness — "the app's wrong about me"
- Indifference — "didn't care"
- Free text

**Q3.** Did any specific notification ever feel like too much?
- Free text. Listing the notification + when it fired + why it bothered them.

**Q4.** If Lyra were a person, how would you describe its tone?
- Free text. Aiming for adjectives — "patient", "nagging", "neutral", "warm", "clinical", "helpful", "preachy" etc.

---

## Section 2 — Did it change anything? (3 questions)

The H1-adjacent question. Lyra's purpose is behavioral change, not just measurement. If retention is high but behavior didn't shift, we have an entertainment product — not a research instrument.

**Q5.** Compared to before using Lyra, are your time estimates more accurate?
- 1 — Much worse
- 2
- 3 — No change
- 4
- 5 — Much more accurate

**Q6.** Did Lyra change how you plan your day?
- Yes, significantly
- Yes, slightly
- No, but I think it could
- No, and I don't think it will
- Free text "How?" (if any yes)

**Q7.** What's one thing you do differently now because of Lyra (if anything)?
- Free text. Open-ended; classifying these later via thematic coding.

---

## Section 3 — Specific surfaces (4 questions)

Probe whether each major Lyra surface delivered value or felt like noise. These map to MANIFESTO research surfaces — operator can correlate with the per-user activity log.

**Q8.** The duration suggestion ("you usually run X minutes longer for this kind of task") — did you find it useful?
- Useful, I adjusted my plans because of it
- Interesting, but didn't change anything
- Annoying / wrong
- Didn't notice it
- Didn't see this surface

**Q9.** The pause/resume nudges ("you usually pause around now" / "you usually resume by now") — useful?
- Same scale as Q8

**Q10.** The archetype label (if you completed the survey) — did it match how you see yourself?
- Yes, accurate
- Mostly accurate
- Surprised me but maybe true
- Not how I'd describe myself
- Didn't see / didn't take the survey

**Q11.** The "your usual" framing across the app — did it ever feel like the app was telling you who you are vs reflecting what your data showed?
- Reflecting data (good)
- Telling me who I am (uncomfortable)
- Both, depending on the moment (free text on which)
- Didn't notice the difference

---

## Section 4 — Retention & willingness-to-pay (3 questions)

The viability signal. VA-1 + VA-3 from the manifesto.

**Q12.** Will you keep using Lyra after this survey?
- Definitely yes
- Probably yes
- Not sure
- Probably no
- Definitely no
- Free text "Why?" (always shown)

**Q13.** If Lyra cost $3-5/month, would you pay?
- Yes
- Maybe — depends on what improves
- No
- I'd want it free with a paid tier for X feature (free text)

**Q14.** If Lyra disappeared tomorrow, what would you miss most?
- Free text. (Sean Ellis-style "must-have" question — answers like "the only place I can see if I'm overrunning" indicate strong PMF; "nothing really" indicates churn risk.)

---

## Section 5 — Friction (2 questions)

Specific UX pains. Operator can prioritize fixes by frequency.

**Q15.** What was the most frustrating moment in your first 2 weeks with Lyra?
- Free text.

**Q16.** What was the most useful or surprising moment?
- Free text.

---

## Pre-registered analysis

When we have ≥5 responses:
- **Affect distribution.** Q1 mean + std. Threshold: if mean ≥ 3.5 OR ≥30% of users answer 4-5, the tone is materially failing — copy revision sprint immediately.
- **Behavior change distribution.** Q5 + Q6 cross-tabulated against per-user `bias_factor` change over the 14-day period. If users self-report change but bias_factor didn't shift, it's perceived effect without behavioral effect (not nothing, but flagged).
- **Surface usefulness.** Q8/Q9/Q10/Q11 — count of "annoying / wrong" responses per surface. Surfaces with ≥30% negative get a UX review.
- **Retention vs willingness-to-pay correlation.** Q12 × Q13 cross-tab. The off-diagonal cells (especially "definitely yes to keep using" + "no to pay") drive the freemium-vs-paid decision for v1.1.

Open-text questions get thematic coding by operator (or LLM-assisted) into 3-5 buckets per question. Bucket distributions flagged in the same write-up.

---

## Operational

- Delivery channel: email link to a single-page web form. Lyra knows each alpha user's email; can fire 7-day-after-first-task reminder.
- Storage: responses go into a new `survey_response` table (TODO when it ships). Per-user submission, raw JSON of (question_id, answer) pairs + timestamp.
- Anonymization for any future publication: same convention as existing user-deletion policy — link to `cohort=alpha_v1` user_id only; no email or other PII in research outputs.
- Skipped questions allowed; response weighted analyses report the n per question.

---

## Change log

- **2026-05-01** — Doc created. Operator request 2026-05-01: "add this question to the survey, 'did you feel the app as judgemental?'" — Q1 written verbatim from operator's intent + companion questions in Section 1 to triangulate the affect signal across surfaces.
