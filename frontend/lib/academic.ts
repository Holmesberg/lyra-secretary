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
export type AcademicSourceClass = "external" | "native" | "lyra_task";
export type AcademicProviderReadStatus =
  | "available"
  | "unavailable"
  | "not_connected";
export type AcademicEvidenceClass =
  | "external_obligation"
  | "native_obligation"
  | "scheduled_intention";
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
  source_class: AcademicSourceClass;
  evidence_class: AcademicEvidenceClass;
  provider_kind?: string | null;
  raw_authority_level: string;
  redaction_status: string;
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
  external_obligation_count: number;
  native_obligation_count: number;
  academic_task_count: number;
  study_task_count: number;
  academic_task_minutes: number;
  study_task_minutes: number;
  google_calendar_connected: boolean;
  google_calendar_read_status: AcademicProviderReadStatus;
  calendar_busy_minutes: number | null;
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
  known_busy_minutes: number | null;
  planned_lyra_minutes: number;
  estimated_academic_low_minutes: number;
  estimated_academic_high_minutes: number;
  google_calendar_connected: boolean;
  google_calendar_read_status: AcademicProviderReadStatus;
  caveat: string;
}

export interface AcademicMinuteEnvelope {
  low_minutes: number;
  high_minutes: number;
}

export interface AcademicObligationDemandProjection {
  obligation_id: string;
  projection_role: "deadline_obligation" | "standalone_task_obligation";
  source_class: AcademicSourceClass;
  total_estimate: AcademicMinuteEnvelope;
  completed_scope_credit: AcademicMinuteEnvelope;
  remaining_demand: AcademicMinuteEnvelope;
  feasible_future_coverage: AcademicMinuteEnvelope;
  applied_coverage: AcademicMinuteEnvelope;
  unscheduled_demand: AcademicMinuteEnvelope;
  overcoverage: AcademicMinuteEnvelope;
  linked_task_ids: string[];
  coverage_task_ids: string[];
  noncontributing_linked_task_ids: string[];
  estimate_inconsistent: boolean;
}

export interface AcademicDemandCoverageProjection {
  schema_version: "academic_demand_coverage_projection_v1";
  projection_status: "provisional_demand_only";
  capacity_status: "unavailable_no_authority";
  collision_state: "unknown";
  obligation_count: number;
  scenario_count: number;
  total_estimate: AcademicMinuteEnvelope;
  completed_scope_credit: AcademicMinuteEnvelope;
  remaining_demand: AcademicMinuteEnvelope;
  feasible_future_coverage: AcademicMinuteEnvelope;
  applied_coverage: AcademicMinuteEnvelope;
  unscheduled_demand: AcademicMinuteEnvelope;
  overcoverage: AcademicMinuteEnvelope;
  inconsistent_obligation_ids: string[];
  obligations: AcademicObligationDemandProjection[];
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
  demand_coverage_projection: AcademicDemandCoverageProjection;
  source_summary: AcademicSourceSummary;
  methodology: string[];
  warnings: string[];
  surface_id?: string | null;
  truth_class?: string | null;
  signal_targets?: string[] | null;
  clean_profile?: string | null;
  fallback_mode?: string | null;
  authority_rung?: string | null;
  mutation_permission?: string | null;
  public_translator?: string | null;
  surface_role?: string | null;
  allowed_authority?: string[];
  denied_authority?: string[];
  exposure_id?: string | null;
  render_snapshot?: Record<string, unknown> | null;
}

export function getAcademicPressureMap(
  horizonDays = 14
): Promise<AcademicPressureMapResponse> {
  return api<AcademicPressureMapResponse>(
    `/v1/academic/pressure-map?horizon_days=${horizonDays}`
  );
}
