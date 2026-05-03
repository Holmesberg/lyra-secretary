# Journey signal counts — onboarding through task completion

**Companion:** `docs/data_utilization_inventory_2026_05_02.md` (authoritative disposition table).

---

## 1. Where the **≥208** number comes from

The inventory is explicit: six sequential Explore passes produced a **floor of ≥208** distinct **dark / implicit / derivable** signal items — **not** a raw count of DB columns only.

| Pass | Scope | Contribution (per inventory §Methodology) |
|------|--------|----------------------------------------|
| 1 | DB columns across **17 tables** | 24 DARK + 5 derivable-dark = **29** |
| 2 | Backend API reflection layer (10 derived endpoints) | **7** unconsumed by frontend |
| 3 | Frontend UI (16 surfaces) | **11** high-value never displayed |
| 4 | Cross-table joins + Redis + `jarvis_invocation` + scheduler | **+36** |
| 5 | Journey-stage implicit signals (**21 stages**) | **+131** |
| 6 | Transition-topology pass | **+12** named patterns |
| **Reported total** | | **≥208** |

**Important:** The doc warns these passes **overlap** (same primitive may appear as a column and again as a journey-stage variant). The **≥208** figure is **inventory accounting**, not “208 independent booleans.” Do **not** sum the pass rows as if disjoint — use §6 disposition rollup for planning.

---

## 2. “Useful” signals — three definitions (pick one when comparing to 208)

| Definition | Approx. scale | Meaning |
|------------|---------------|---------|
| **A — Inventoried substrate** | **≥208** | Everything triaged in the utilization inventory (includes DEFER, NOT-INSTRUMENTED, duplicates across passes). |
| **B — Transition-actionable** | **~52** | SURFACE (~12) + PROMOTE-TO-JARVIS (~24) + Phase 6 INSTRUMENT (**5** telemetry types) + RETIRE writers (~1–3) + selected DERIVABLE rows bundled into those phases. Rough order-of-magnitude from §6 rollup; not additive with 208 without deduping. |
| **C — Already correct REFLECTED / NO-ACTION** | **~95** | Columns/paths already surfaced or correctly restricted — **useful** because they *are* the live loop; no transition work. |

For **feedback-loop enhancement**, prioritize **B** (what ships next) plus **NOT-INSTRUMENTED** rows slated for the **top-7** list.

---

## 3. Flow: onboarding → task end — stages and high-value signals

Stages follow inventory **§4 — Journey-Stage Implicit Signals (21 stages)**. For each stage, **one** headline primitive is listed there; many stages also have **additional** columns elsewhere in §1–§3.

| Stage | Journey focus | Inventory “top implicit signal” class | Disposition (summary) |
|-------|----------------|----------------------------------------|------------------------|
| 1 | Pre-signup | UTM / referrer / dwell | NOT-INSTRUMENTED → NO-ACTION (defer) |
| 2 | OAuth signup | OAuth latency / scope hesitation | NOT-INSTRUMENTED → NO-ACTION |
| 3 | First load / onboarding routing | Auth-to-render latency | NOT-INSTRUMENTED → INSTRUMENT (deferred) |
| 4 | Brain dump onboarding | Parse-to-commit, binding, edits | **INSTRUMENT** (top-7 **#1**) |
| 5 | 29-item archetype survey | Per-item dwell + variance | **INSTRUMENT** (top-7 **#3**) |
| 6 | Tutorial complete/skip | Step engagement | NOT-INSTRUMENTED → NO-ACTION |
| 7 | Settings → Integrations | Connect order, retries | NOT-INSTRUMENTED → INSTRUMENT (deferred; needs `connected_at`) |
| 8 | First task creation | Modal open→submit, field order | **INSTRUMENT** (top-7 **#5**) |
| 9 | Calendar view | Path preferences | NOT-INSTRUMENTED → NO-ACTION (defer) |
| 10 | Today view | Frequency / scroll / refresh | NOT-INSTRUMENTED → NO-ACTION (defer) |
| 11 | Stopwatch start (readiness modal) | Latency, edits | NOT-INSTRUMENTED → NO-ACTION (defer) |
| 12 | During execution | Completion-% trajectory | **INSTRUMENT** (top-7 **#2**) |
| 13 | Pause flow | Reason-pick latency | **INSTRUMENT** (top-7 **#4**) |
| 14 | Resume flow | Trigger source | DARK → PROMOTE-TO-JARVIS |
| 15 | Task switching mid-session | Switch depth + return | DERIVABLE-DARK → PROMOTE-TO-JARVIS |
| 16 | Stop flow | Reflection hesitation | NOT-INSTRUMENTED → NO-ACTION (defer) |
| 17 | Post-stop reflection surfaces | Dwell by `reflection_type` | DERIVABLE-DARK → PROMOTE-TO-JARVIS |
| 18 | End-of-session navigation | Next-page choice | NOT-INSTRUMENTED → NO-ACTION (defer) |
| 19 | Day-end / cross-day return | Return-after-cascade latency | **DERIVABLE → SURFACE** (Phase 4; no new capture) |
| 20 | Void / abandon / reschedule / skip | Abandonment-path preference | **DERIVABLE → SURFACE** (Phase 4) |
| 21 | Account deletion | Modal dwell, checkbox | NOT-INSTRUMENTED → NO-ACTION |

**Quick counts on this table alone**

- **Stages with Phase 6 net-new instrumentation (top-7 wiring):** **5** (stages 4, 5, 8, 12, 13) — matches inventory §5 (“**5 telemetry types**, not 7”).
- **Stages with derivable SURFACE without new capture:** **2** (19, 20).
- **Stages with PROMOTE-TO-JARVIS / discovery-first:** **3** (14, 15, 17) plus many **column-level** PROMOTE rows in §1.
- **Stages explicitly deferred or NO-ACTION for now:** the remainder.

This **21-row** view does **not** replace the **≥208** full inventory; it is the **narrative spine** for “where” implicit signal attaches along the user journey.

---

## 4. Implicit signal: incomplete task description before deadline (May 2)

**Source:** `docs/dogfood_findings_living.md` (May 2 entry).

**Definition (behavioral):** The user attached or accepted a **deadline** for a task but did **not** finish composing the task’s **planned description / scope** (body + structured bullets) **before the deadline instant**. That mismatch indicates **declared urgency without planning depth** — a **priority-measurement** primitive for Phase 6.

**Capture stance**

- **Full fidelity** likely needs a **boundary event** at or before `deadline.due_at_utc` (telemetry or server-side snapshot) — aligns with **NOT-INSTRUMENTED** until Phase 6.
- **Proxies** (partial, existing columns): `deadline_id`, `Deadline.due_at_utc`, `Task.description`, `scope_bullet_count_at_plan`, `last_modified_at` — sufficient for **operator/JARVIS exploratory** queries before hard user-facing copy.

Canonical disposition row: **`docs/data_utilization_inventory_2026_05_02.md` — Revision 2**.

---

*Append-only companion. Amend via new revision sections in the utilization inventory.* 
