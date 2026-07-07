/**
 * Archetype survey item bank + API client.
 *
 * The 29-item battery:
 *   MEQ-5       — 5 items, mixed 1-5/1-4 response scales (morningness)
 *   BFI-10 C    — 2 items, 1-5 Likert (conscientiousness)
 *   BSCS-Brief  — 13 items, 1-5 Likert (self-control)
 *   GP-Short    — 9 items, 1-5 Likert (procrastination)
 *
 * Target completion time: 3-4 minutes at ~7s per item.
 *
 * IMPORTANT (licensing / wording): the item texts below approximate
 * the published instrument wording. For trusted-user week 2 dogfood
 * this is acceptable. BEFORE public beta, operator must verify each
 * item matches the verbatim published text from the source paper:
 *   - MEQ-5:   Adan & Almirall 1991, Chronobiol Int 8:329-336
 *   - BFI-10:  Rammstedt & John 2007, J Res Pers 41:203-212
 *              (BFI-10 explicitly placed in public domain by authors)
 *   - BSCS:    Tangney Baumeister Boone 2004, J Pers 72:271-322
 *   - GP-9:    Lay 1986, J Res Pers 20:474-495 (Steel 2010 short form)
 * See strategic_decisions_april_22.md §5.6 for licensing flag.
 *
 * All reverse-keying happens SERVER-SIDE. Frontend sends raw 1-5
 * (or 1-4 for MEQ-5 items 2,3,4) integers. Scorer in
 * backend/app/services/archetype_service.py handles inversion per
 * Tangney 2004 BSCS indices {2,3,4,5,7,9,10,12,13}.
 */
import { api } from "./api";

export type Instrument = "meq" | "bfi_c" | "bscs" | "gp";

export interface SurveyOption {
  /** Weight sent to the server. MEQ items 1,5 use 1-5; items 2,3,4 use 1-4. BFI/BSCS/GP use 1-5. */
  value: number;
  label: string;
}

export interface SurveyItem {
  /** Stable slug for telemetry (log which items drop-off happens on). */
  id: string;
  instrument: Instrument;
  text: string;
  options: SurveyOption[];
}

// ---------------------------------------------------------------------------
// MEQ-5 (morningness-eveningness, 5 items)
// Items 1 + 5: 1-5 weights. Items 2, 3, 4: 1-4 weights.
// Higher weight = more morning-type for all items.
// ---------------------------------------------------------------------------
export const MEQ_ITEMS: SurveyItem[] = [
  {
    id: "meq_1_wake_preference",
    instrument: "meq",
    text: "If you were entirely free to plan your day, what time would you get up?",
    options: [
      { value: 5, label: "Before 6:30 AM" },
      { value: 4, label: "6:30 – 7:45 AM" },
      { value: 3, label: "7:45 – 9:45 AM" },
      { value: 2, label: "9:45 – 11:00 AM" },
      { value: 1, label: "After 11:00 AM" },
    ],
  },
  {
    id: "meq_2_morning_tiredness",
    instrument: "meq",
    text: "In the first half-hour after waking, how refreshed do you feel?",
    options: [
      { value: 4, label: "Very refreshed" },
      { value: 3, label: "Fairly refreshed" },
      { value: 2, label: "Fairly tired" },
      { value: 1, label: "Very tired" },
    ],
  },
  {
    id: "meq_3_evening_tiredness",
    instrument: "meq",
    text: "At what time in the evening do you feel tired and ready for bed?",
    options: [
      { value: 4, label: "Before 10:00 PM" },
      { value: 3, label: "10:00 – 11:30 PM" },
      { value: 2, label: "11:30 PM – 1:00 AM" },
      { value: 1, label: "After 1:00 AM" },
    ],
  },
  {
    id: "meq_4_peak_time",
    instrument: "meq",
    text: "At what time of day do you feel your best?",
    options: [
      { value: 4, label: "Early morning (5–8 AM)" },
      { value: 3, label: "Late morning / early afternoon" },
      { value: 2, label: "Late afternoon / evening" },
      { value: 1, label: "Late at night" },
    ],
  },
  {
    id: "meq_5_self_identification",
    instrument: "meq",
    text: "Would you say you are a morning or an evening person?",
    options: [
      { value: 5, label: "Definitely a morning person" },
      { value: 4, label: "More morning than evening" },
      { value: 3, label: "Neither, or it depends" },
      { value: 2, label: "More evening than morning" },
      { value: 1, label: "Definitely an evening person" },
    ],
  },
];

// ---------------------------------------------------------------------------
// BFI-10 C (conscientiousness, 2 items, 1-5 Likert)
// Item 1 forward, item 2 reverse-keyed (server-side).
// ---------------------------------------------------------------------------
const LIKERT_5: SurveyOption[] = [
  { value: 1, label: "Strongly disagree" },
  { value: 2, label: "Disagree" },
  { value: 3, label: "Neither agree nor disagree" },
  { value: 4, label: "Agree" },
  { value: 5, label: "Strongly agree" },
];

export const BFI_C_ITEMS: SurveyItem[] = [
  {
    id: "bfi_c_1_thorough",
    instrument: "bfi_c",
    text: "I see myself as someone who does a thorough job.",
    options: LIKERT_5,
  },
  {
    id: "bfi_c_2_lazy",
    instrument: "bfi_c",
    text: "I see myself as someone who tends to be lazy.",
    options: LIKERT_5,
  },
];

// ---------------------------------------------------------------------------
// BSCS-Brief (self-control, 13 items, 1-5 Likert)
// Reverse-keyed server-side: items 2, 3, 4, 5, 7, 9, 10, 12, 13
// (1-indexed per Tangney 2004). Array below is 1-indexed in the same
// order — item i-th in the array corresponds to published item i+1.
// ---------------------------------------------------------------------------
export const BSCS_ITEMS: SurveyItem[] = [
  {
    id: "bscs_1",
    instrument: "bscs",
    text: "I am good at resisting temptation.",
    options: LIKERT_5,
  },
  {
    id: "bscs_2",
    instrument: "bscs",
    text: "I have a hard time breaking bad habits.",
    options: LIKERT_5,
  },
  {
    id: "bscs_3",
    instrument: "bscs",
    text: "I am lazy.",
    options: LIKERT_5,
  },
  {
    id: "bscs_4",
    instrument: "bscs",
    text: "I say inappropriate things.",
    options: LIKERT_5,
  },
  {
    id: "bscs_5",
    instrument: "bscs",
    text: "I do certain things that are bad for me, if they are fun.",
    options: LIKERT_5,
  },
  {
    id: "bscs_6",
    instrument: "bscs",
    text: "I refuse things that are bad for me.",
    options: LIKERT_5,
  },
  {
    id: "bscs_7",
    instrument: "bscs",
    text: "I wish I had more self-discipline.",
    options: LIKERT_5,
  },
  {
    id: "bscs_8",
    instrument: "bscs",
    text: "People would say I have iron self-discipline.",
    options: LIKERT_5,
  },
  {
    id: "bscs_9",
    instrument: "bscs",
    text: "Pleasure and fun sometimes keep me from getting work done.",
    options: LIKERT_5,
  },
  {
    id: "bscs_10",
    instrument: "bscs",
    text: "I have trouble concentrating.",
    options: LIKERT_5,
  },
  {
    id: "bscs_11",
    instrument: "bscs",
    text: "I am able to work effectively toward long-term goals.",
    options: LIKERT_5,
  },
  {
    id: "bscs_12",
    instrument: "bscs",
    text: "Sometimes I can't stop myself from doing something, even if I know it is wrong.",
    options: LIKERT_5,
  },
  {
    id: "bscs_13",
    instrument: "bscs",
    text: "I often act without thinking through all the alternatives.",
    options: LIKERT_5,
  },
];

// ---------------------------------------------------------------------------
// GP-Short (procrastination, 9 items, 1-5 Likert)
// All items forward-keyed: higher response = more procrastination.
// ---------------------------------------------------------------------------
export const GP_ITEMS: SurveyItem[] = [
  {
    id: "gp_1_delay_returns",
    instrument: "gp",
    text: "I often find myself performing tasks that I had intended to do days before.",
    options: LIKERT_5,
  },
  {
    id: "gp_2_late_starter",
    instrument: "gp",
    text: "I often get started on a task later than I could have.",
    options: LIKERT_5,
  },
  {
    id: "gp_3_last_minute",
    instrument: "gp",
    text: "I'm usually working until the last minute to finish things.",
    options: LIKERT_5,
  },
  {
    id: "gp_4_put_off",
    instrument: "gp",
    text: "In preparation for some deadlines, I often waste time doing other things.",
    options: LIKERT_5,
  },
  {
    id: "gp_5_promise",
    instrument: "gp",
    text: "I promise myself I'll do something and then drag my feet.",
    options: LIKERT_5,
  },
  {
    id: "gp_6_unfinished_work",
    instrument: "gp",
    text: "A project usually has to be near its deadline before I can really get moving on it.",
    options: LIKERT_5,
  },
  {
    id: "gp_7_morning_dely",
    instrument: "gp",
    text: "If something is due, I leave it until the last minute and then complain about the lack of time.",
    options: LIKERT_5,
  },
  {
    id: "gp_8_friends_finish",
    instrument: "gp",
    text: "I find myself running out of time.",
    options: LIKERT_5,
  },
  {
    id: "gp_9_delay",
    instrument: "gp",
    text: "I generally delay before starting work I have to do.",
    options: LIKERT_5,
  },
];

// ---------------------------------------------------------------------------
// API types + client
// ---------------------------------------------------------------------------

export interface ArchetypeSurveyPayload {
  meq: number[];
  bfi_c: number[];
  bscs: number[];
  gp: number[];
}

export interface ArchetypeAssignmentResult {
  archetype_id: string;
  completed: boolean;
  chronotype: string | null;
  discipline_z: number | null;
  meq_score: number | null;
  bfi_c_score: number | null;
  bscs_score: number | null;
  gp_score: number | null;
}

export async function submitArchetypeSurvey(
  payload: ArchetypeSurveyPayload
): Promise<ArchetypeAssignmentResult> {
  return api<ArchetypeAssignmentResult>("/v1/users/me/archetype/survey", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function skipArchetypeSurvey(): Promise<ArchetypeAssignmentResult> {
  return api<ArchetypeAssignmentResult>("/v1/users/me/archetype/skip", {
    method: "POST",
  });
}

export async function dismissArchetypeRetrofit(): Promise<{
  ok: boolean;
  archetype_retrofit_dismissed_at: string | null;
}> {
  return api("/v1/users/me/archetype/retrofit-dismiss", { method: "POST" });
}

/** Human-readable archetype labels. */
export const ARCHETYPE_LABELS: Record<string, string> = {
  disciplined_lark: "Disciplined Lark",
  disciplined_owl: "Disciplined Owl",
  diffuse_average: "Diffuse Average",
  procrastinator: "Procrastinator",
  lark_low_discipline: "Lark, Low Discipline",
};

/** One-line characterizations of each archetype — the hero copy that
 *  tells the user what their profile means for planning, not the math. */
export const ARCHETYPE_DESCRIPTIONS: Record<string, string> = {
  disciplined_lark:
    "You wake early and execute on what you plan. Research shows people like you slightly UNDERestimate tasks — your own optimism is the main risk. Barzakh applies a gentle discount, then lets your personal data take over.",
  disciplined_owl:
    "Evening energy with solid follow-through. Mornings are structurally harder for owls, so Barzakh factors in a small uplift for early-hour tasks — otherwise you'd look like you overrun when you're really just running against your circadian grain.",
  diffuse_average:
    "The population midpoint — your planning shape hasn't clustered into a sharper profile yet. Barzakh uses Kahneman & Buehler's planning-fallacy mean as your starting prior: ~30% overruns expected on most categories until your own data sharpens the estimate.",
  procrastinator:
    "Steel 2010 research shows GP-high folks typically underestimate by 1.6–2.2×. Barzakh bakes this in — your scheduled 30 min gets ~54 min of real room by default. This isn't a judgement; it's your runway for shipping what you actually plan.",
  lark_low_discipline:
    "Morning chronotype gives you a peak window that partially compensates — not a full procrastinator, not a disciplined lark. Barzakh predicts middle-ground overruns in your peak hours and larger ones off-peak.",
};

/** What the blend means for the user's planning, state-specific. Keep
 *  copy archetype-identity-forward; math lives below the fold. */
export const ARCHETYPE_PLANNING_IMPLICATION: Record<string, string> = {
  disciplined_lark:
    "Expect Barzakh's predictions to stay close to your planned durations. Your personal data will refine them downward over time.",
  disciplined_owl:
    "Expect slight uplift on morning tasks, neutrality in afternoons/evenings. Personal data sharpens both bands with use.",
  diffuse_average:
    "Expect roughly +30% over plan on most categories until you've built up enough personal data (~30 sessions per category-time cell) for the blend to shift toward you.",
  procrastinator:
    "Expect Barzakh to suggest larger scheduled blocks than you'd typically plan. The suggestion isn't pessimism — it's the runway your history actually needs.",
  lark_low_discipline:
    "Expect moderate uplift on all tasks with slightly less on your peak morning window. Personal data will sharpen the peak-vs-off-peak split.",
};

// ──────────────────────────────────────────────────────────────────────
// VT-25 dynamic-reveal client (MANIFESTO Rule 17, 2026-04-27).
// Replaces the static "Profile: Procrastinator" reveal with a
// continuously-updated Bayesian posterior over the 5 archetypes.
// Backend service: backend/app/services/archetype_proximity_service.py
// Endpoint: GET /v1/analytics/archetype/proximity (+ /trend variant)
// ──────────────────────────────────────────────────────────────────────

export interface ArchetypeProximity {
  archetype_id: string;
  label: string;
  /** Posterior probability in [0, 1]. Sums to ~1.0 across the 5 archetypes. */
  score: number;
  /** Rank by score desc (1 = highest). */
  rank: number;
  /** Number of EXECUTED tasks contributing to this posterior (n=0 → uniform). */
  n_tasks: number;
}

export interface ProximityResponse {
  proximity: ArchetypeProximity[];
  lookback_days: number;
  n_tasks: number;
  ready?: boolean;
  display_mode?: "behavioral_proximity" | "settling_in" | string;
  surface_id?: string;
  truth_class?: "trace" | "metric" | "interpretation" | "intervention" | "diagnostic_only";
  usage_class?: string;
  clean_profile?: string | null;
  eligible_sample_count?: number;
  min_n_required?: number;
  suppressed_reason?: string | null;
  fallback_mode?: string;
  legacy_adapter?: string | null;
  exposure_id?: string | null;
  render_id?: string | null;
  primary_metric: string;
}

export interface ProximityTrend {
  current: ArchetypeProximity[];
  prior: ArchetypeProximity[];
  /** Score delta per archetype_id (current − prior). Positive = trending up. */
  delta_per_archetype: Record<string, number>;
  current_window_days: number;
  prior_window_days: number;
}

/**
 * Get the user's current archetype proximity over the last N days.
 * Uniform 1/5 across all archetypes if no qualifying tasks (cold start).
 */
export function getArchetypeProximity(days = 14): Promise<ProximityResponse> {
  return api<ProximityResponse>(
    `/v1/analytics/archetype/proximity?days=${days}`
  );
}

/**
 * Get current vs prior window proximity for trend display.
 * Powers the "a month ago you were X — pattern is consolidating toward Y" copy.
 */
export function getArchetypeProximityTrend(
  currentDays = 14,
  priorDays = 14
): Promise<ProximityTrend> {
  return api<ProximityTrend>(
    `/v1/analytics/archetype/proximity/trend?current_days=${currentDays}&prior_days=${priorDays}`
  );
}
