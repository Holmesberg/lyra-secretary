// Mirrors backend PAUSE_REASONS in backend/app/schemas/stopwatch.py.
// Pause reason is research-relevant measurement data, so frontend callers
// should use this vocabulary instead of raw string literals.
export const PAUSE_REASON_VALUES = [
  "mental_fatigue",
  "distraction",
  "task_difficulty",
  "external_interruption",
  "intentional_break",
  "prayer",
  "task_switch",
] as const;

export type PauseReason = (typeof PAUSE_REASON_VALUES)[number];

export const QUICK_PAUSE_REASON: PauseReason = "intentional_break";

export const PAUSE_REASON_OPTIONS: ReadonlyArray<{
  value: PauseReason;
  label: string;
}> = [
  { value: "mental_fatigue", label: "Low focus" },
  { value: "distraction", label: "Distraction" },
  { value: "task_difficulty", label: "Task difficulty" },
  { value: "external_interruption", label: "External interruption" },
  { value: QUICK_PAUSE_REASON, label: "Intentional break" },
  { value: "prayer", label: "Prayer" },
  { value: "task_switch", label: "Switching to another task" },
];
