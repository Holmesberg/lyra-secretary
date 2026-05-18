import { api } from "./api";

export type AcademicTrustState =
  | "verified_exact"
  | "verified_reachable"
  | "ambiguous"
  | "requires_user_confirmation"
  | "stale"
  | "dead_link"
  | "access_denied";

export type AcademicPressureLevel = "low" | "medium" | "high" | "overdue";
export type AcademicComplexityTier = "low" | "medium" | "high" | "unknown";
export type AcademicConfidence = "low" | "medium" | "high";
export type AcademicCompressionKind =
  | "due_soon"
  | "overdue"
  | "cluster"
  | "known_load"
  | "uncertain_coverage";
export type AcademicRecoveryAction =
  | "confirm_coverage"
  | "split_into_blocks"
  | "create_plan"
  | "review_calendar"
  | "clear_or_ignore";

export interface AcademicPressureEstimate {
  low_minutes: number;
  high_minutes: number;
  confidence: AcademicConfidence;
  assumptions: string[];
}

export interface AcademicPressureItem {
  obligation_id: string;
  title: string;
  due_at_utc: string;
  source: string;
  obligation_type: string;
  trust_state: AcademicTrustState;
  complexity_tier: AcademicComplexityTier;
  complexity_source: string;
  pressure_level: AcademicPressureLevel;
  days_until_due: number;
  estimate: AcademicPressureEstimate;
  warnings: string[];
}

export interface AcademicSourceSummary {
  deadlines_total: number;
  moodle_deadlines: number;
  native_deadlines: number;
  google_calendar_connected: boolean;
  calendar_busy_minutes: number;
  planned_lyra_minutes: number;
}

export interface AcademicCompressionPoint {
  kind: AcademicCompressionKind;
  title: string;
  detail: string;
  obligation_ids: string[];
}

export interface AcademicRecoveryOption {
  action: AcademicRecoveryAction;
  label: string;
  detail: string;
  obligation_ids: string[];
}

export interface AcademicCoverageQuestion {
  obligation_id: string;
  question: string;
  reason: string;
  trust_state: AcademicTrustState;
}

export interface AcademicCapacityContext {
  known_busy_minutes: number;
  planned_lyra_minutes: number;
  estimated_academic_low_minutes: number;
  estimated_academic_high_minutes: number;
  google_calendar_connected: boolean;
  caveat: string;
}

export interface AcademicPressureMapResponse {
  generated_at_utc: string;
  horizon_days: number;
  headline: string;
  pressure_summary: string;
  items: AcademicPressureItem[];
  compression_points: AcademicCompressionPoint[];
  recovery_options: AcademicRecoveryOption[];
  coverage_questions: AcademicCoverageQuestion[];
  capacity_context: AcademicCapacityContext;
  estimated_low_minutes: number;
  estimated_high_minutes: number;
  source_summary: AcademicSourceSummary;
  methodology: string[];
  warnings: string[];
  surface_id?: string | null;
  truth_class?: string | null;
  signal_targets?: string[] | null;
  clean_profile?: string | null;
  fallback_mode?: string | null;
  exposure_id?: string | null;
  render_id?: string | null;
}

export function getAcademicPressureMap(
  horizonDays = 14
): Promise<AcademicPressureMapResponse> {
  return api<AcademicPressureMapResponse>(
    `/v1/academic/pressure-map?horizon_days=${horizonDays}`
  );
}
