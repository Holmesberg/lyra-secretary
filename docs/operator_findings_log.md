# Operator Findings Log

**Owner:** Operator (Ali)
**Paired tools:** `notebooks/operator_analytics.ipynb`, `docs/operator_interrogation_checklist.md`
**Status:** Append-only log. One entry per interrogation pass.

Each entry records what was expected, what was observed, what was
surprising, and which actions (if any) it triggers. Actions are one of:

- **(a) New dogfood item** — added to `docs/dogfood_findings_living.md`
  with a Pn priority.
- **(b) New validity threat (VT)** — added to `MANIFESTO.md §The
  Validity Register` with distinguishing analyses.
- **(c) Noted, not actionable now** — logged but not escalated.

A finding without an action is still a valid entry. "No signal yet"
answers belong here too — leaving a question unanswered silently is
what this log is designed to prevent.

---

## Entry template

Copy the block below for each pass. Fill in every field; use "n/a" or
"no signal yet" where appropriate. Do not delete unused sub-sections —
the structure is load-bearing.

```markdown
## Day {10|30|60|90} — {YYYY-MM-DD} — cohort: {operator|trusted|all}

**Notebook run:** `operator_analytics.local.ipynb` commit/sha: {sha or "working copy"}
**Window:** {start_iso} → {end_iso}
**n (tasks):** {count}
**n (users):** {count}

### Expected patterns

- {what I expected to see, before running the notebook}
- {...}

### Observed patterns

#### Delta
- {median / mean / skew / category breakdown summary}

#### Discrepancy
- {unstratified ρ, stratified ρ, sign-flip yes/no}
- VT-12a: {rho, p, interpretation}
- VT-12b: {readiness=5 variance finding}
- VT-12c: {readiness × category std cells of note}

#### Initiation delay
- {distribution summary, time-of-day/category findings}

#### Unplanned rate
- {overall %, trend direction}

#### Cascade
- {session_index_in_day correlation, chain counts}

#### Data quality
- {null rates of note, any 100%-default flags, stale PAUSED count}

### Surprises

- {findings I did not expect — this is the section future-me will read first}
- {...}

### Actions

- **(a)** {new dogfood item title + priority + one-line description}
  → added to `docs/dogfood_findings_living.md` §{section} as {LYR-xxx | new bullet}
- **(b)** {new VT identifier + hypothesis}
  → added to `MANIFESTO.md §The Validity Register` as VT-{n}
- **(c)** {noted-not-actionable observation}
  → reason for deferral: {one line}

### Questions for next milestone

- {questions the findings raised that the current checklist did not cover}
- {...}

---
```

## Standing rules

1. **Entries are append-only.** If a past finding is wrong, add a new
   entry that corrects it. Do not edit prior entries in place.
2. **Every checklist question has an answer in the corresponding
   "Observed patterns" sub-section.** Missing sub-sections mean the
   question was silently skipped — which is the failure mode this log
   exists to prevent.
3. **Actions reference their destination.** An (a) action that does not
   name the file + section it was added to is incomplete.
4. **n counts are mandatory.** Every pass records both task count and
   user count. Kill-criterion decisions depend on n.
5. **New questions go to the checklist, not the log.** If a pass raises
   a question worth asking again, add it to the next milestone section
   of `docs/operator_interrogation_checklist.md` — not retroactively to
   the current one.

## References

- `docs/operator_interrogation_checklist.md` — the question list
- `notebooks/operator_analytics.ipynb` — the tooling
- `docs/dogfood_findings_living.md` — where (a) actions land
- `MANIFESTO.md §The Validity Register` — where (b) actions land
- `docs/building_phases.md` §Phase 5 / 5.5 — milestone gates
