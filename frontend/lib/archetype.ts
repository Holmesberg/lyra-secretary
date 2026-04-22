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

/** Human-readable archetype labels for reveal copy (v1.1; unused in v1 silent-shrinkage ship). */
export const ARCHETYPE_LABELS: Record<string, string> = {
  disciplined_lark: "Disciplined Lark",
  disciplined_owl: "Disciplined Owl",
  diffuse_average: "Diffuse Average",
  procrastinator: "Procrastinator",
  lark_low_discipline: "Lark, Low Discipline",
};
