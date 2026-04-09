# Competitive landscape

Quick scan of tools adjacent to Lyra Secretary. Goal: articulate what's
missing in the market that justifies the metacognitive layer Lyra builds.

## Products

| Product | Category | What it does | What it misses |
|---|---|---|---|
| Twin'Am | Adaptive scheduler | Learns work patterns, suggests blocks | No research layer; black-box suggestions; no planned-vs-executed exposure |
| Habitica | Gamified habit tracker | RPG-style streaks and rewards | Habits, not time; no duration data; no calibration loop |
| Toggl Track | Time tracker | Manual/auto timers, reports | Tracks but doesn't *plan*; no delta between intent and execution |
| RescueTime | Passive time tracker | Auto-categorizes app/site usage | Descriptive, not prescriptive; no user-facing readiness/reflection |
| Clockify | Time tracker | Timesheets, billing | Same as Toggl — logs only, no planning layer |
| Notion | General workspace | Databases, docs, task boards | Storage, not scheduling; no timer, no adaptive loop |
| Todoist | Task manager | Lists, due dates, natural language | No duration, no execution data, no research layer |
| ClickUp | Project mgmt | Tasks, docs, time tracking, everything | Feature sprawl; no adaptive scheduling or calibration feedback |
| Forest | Focus timer | Pomodoro with tree gamification | Fixed intervals; no planning; no delta data |
| Focus Keeper | Focus timer | Pomodoro variants | Same — no planning context, no post-hoc calibration |

## What's missing

No tool in this list closes the **metacognitive loop** between planning
and execution:

1. **Planned vs executed duration as first-class data.** Everyone tracks
   one side or the other — intent (Todoist, Notion) or actuals (Toggl,
   RescueTime). Nothing surfaces the *delta* to the user as a learning
   signal.
2. **Pre-task readiness and post-task reflection as structured input.**
   Treated as journaling (if at all), never as a quantitative instrument
   paired with duration delta.
3. **Calibration feedback as a UX primitive.** "You planned 30, it took
   45, your focus was 3/5 — here's what reference-class forecasting
   suggests for next time." No one ships this.
4. **Research layer visible in the daily view.** Users see the numbers
   that drive the adaptive model, not just the model's output. Makes the
   system legible instead of a black box.

Lyra Secretary's bet: the research layer *is* the product. Adaptive
scheduling without it is just opinionated autocomplete.
