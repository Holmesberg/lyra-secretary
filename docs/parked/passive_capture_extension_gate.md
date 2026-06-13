---
authority: parked
may_authorize_code: false
runtime_owner: none
promotion_condition: >
  Explicit timer friction remains a proven retention blocker after the core
  loop is stable, and a confirmation-gated passive evidence design can be
  implemented without surveillance drift.
---

# Passive Capture / Browser Extension Gate

Status: parked. Do not implement yet.

## Why Parked

Users report high tracking friction and forgotten timers. A browser extension
could reduce friction, but it risks breaking Lyra's core invariant:

```text
intention -> execution -> drift -> interruption -> recalibration
```

Passive capture can observe activity-like traces, but activity is not
intention, execution, completion, learning, or effort.

## Allowed Future Shape

If promoted, passive capture must be:

- visible;
- opt-in;
- local-first where possible;
- confirmation-gated;
- provider/domain-redacted by default;
- weak evidence until accepted;
- never clean execution truth by itself.

Safe copy:

```text
Lyra noticed possible work on X. Confirm?
```

Unsafe copy:

```text
You worked on X for 2h.
```

## Evidence Tiers

| Tier | Meaning | Authority |
| --- | --- | --- |
| passive_hint | tab/app/resource activity suggests context | candidate only |
| confirmed_activity | user confirms activity happened | descriptive history |
| linked_execution | user links activity to task/session | execution-supporting evidence |
| clean_execution | explicit timer or equivalent future authority | measured execution |

## Kill Criteria

Kill if:

- users feel watched;
- passive hints become canonical without confirmation;
- provider data becomes completion truth;
- false positives create clutter;
- it increases anxiety or observer capture;
- no clear retention lift over simpler timer/re-entry fixes.

## Promotion Must Wait For

- stable Pulse loop;
- open-thread recovery implemented and useful;
- estimate provenance implemented;
- provider middleware boundaries hardened;
- export/delete/account trust verified;
- exposure logging for passive prompts.
