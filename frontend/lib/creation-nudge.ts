import type { BiasFactorCell, CreateTaskInput } from "./tasks";
import { roundTo5 } from "./task-time";

// Pure value helpers only. Creation-nudge exposure render, suppression, and
// decision lifecycle authority stays in NewTaskModal.
const RESEARCH_PRIOR_DEFAULT = {
  biasFactor: 1.35,
  citation: "Kahneman & Tversky 1979 (planning fallacy mean)",
};

const RESEARCH_PRIORS: Record<string, { biasFactor: number; citation: string }> = {
  development: {
    biasFactor: 1.5,
    citation: "Buehler et al. 1994; Connolly & Dean 1997",
  },
  work: { biasFactor: 1.45, citation: "Buehler et al. 1994" },
  study: { biasFactor: 1.4, citation: "Newby-Clark et al. 2000" },
  academic: { biasFactor: 1.4, citation: "Newby-Clark et al. 2000" },
  exercise: { biasFactor: 1.15, citation: "Roy et al. 2005" },
  fitness: { biasFactor: 1.15, citation: "Roy et al. 2005" },
};

export type NudgeDecisionData = {
  decision: "accepted" | "dismissed";
  suggested_minutes: number;
  bias_factor: number;
  sample_size: number;
  viewed_at: string;
};

export type NudgeDecisionPayload = Pick<
  CreateTaskInput,
  | "nudge_decision"
  | "nudge_suggested_duration_minutes"
  | "nudge_bias_factor"
  | "nudge_sample_size"
  | "nudge_viewed_at"
>;

type CalibrationNudgeDecisionSource = {
  suggestedMin: number;
  factor: number;
  cell: { sessions: number };
  firedAt: string;
};

export interface LocalResearchCreationNudge {
  cell: BiasFactorCell;
  factor: number;
  personalFactor: null;
  blendFactor: number;
  personalWeight: 0;
  priorWeight: 1;
  priorFactor: number;
  priorCitation: string;
  suggestedMin: number;
  executionSuggestedMin: number;
  pauseOverheadMin: 0;
  pauseOverheadSampleSize: 0;
  occupancySuggestedMin: number;
  occupancyStrategy: "execution_only_research_prior";
  firedAt: string;
  exposureId: string;
  backendReady: false;
}

export function nudgePayloadFromDecision(
  nudgeDecisionData: NudgeDecisionData | null,
): NudgeDecisionPayload {
  if (!nudgeDecisionData) {
    return {};
  }
  return {
    nudge_decision: nudgeDecisionData.decision,
    nudge_suggested_duration_minutes: nudgeDecisionData.suggested_minutes,
    nudge_bias_factor: nudgeDecisionData.bias_factor,
    nudge_sample_size: nudgeDecisionData.sample_size,
    nudge_viewed_at: nudgeDecisionData.viewed_at,
  };
}

export function nudgeDecisionFromCalibration(
  nudge: CalibrationNudgeDecisionSource,
  decision: NudgeDecisionData["decision"],
): NudgeDecisionData {
  return {
    decision,
    suggested_minutes: nudge.suggestedMin,
    bias_factor: nudge.factor,
    sample_size: nudge.cell.sessions,
    viewed_at: nudge.firedAt,
  };
}

export function localResearchNudge(
  category: string,
  tod: string,
  planned: number,
  firedAt: string,
  exposureId: string,
): LocalResearchCreationNudge {
  const prior = RESEARCH_PRIORS[category] ?? RESEARCH_PRIOR_DEFAULT;
  const suggestedMin = roundTo5(planned * prior.biasFactor);
  return {
    cell: {
      bias_factor: prior.biasFactor,
      bias_factor_mean: prior.biasFactor,
      sessions: 0,
      confidence: "research",
      interpretation: "underestimates",
      category,
      time_of_day: tod,
      citation: prior.citation,
    } satisfies BiasFactorCell,
    factor: prior.biasFactor,
    personalFactor: null,
    blendFactor: prior.biasFactor,
    personalWeight: 0,
    priorWeight: 1,
    priorFactor: prior.biasFactor,
    priorCitation: prior.citation,
    suggestedMin,
    executionSuggestedMin: suggestedMin,
    pauseOverheadMin: 0,
    pauseOverheadSampleSize: 0,
    occupancySuggestedMin: suggestedMin,
    occupancyStrategy: "execution_only_research_prior",
    firedAt,
    exposureId,
    backendReady: false,
  };
}
