import type {
  AcademicPressureMapResponse,
  AcademicRecoveryAction,
  AcademicRecoveryOption,
} from "@/lib/academic";
import { planItemsForOption } from "@/lib/pressure-map-planning";

export type PressureMapActionDisposition =
  | "canonical_command"
  | "navigation"
  | "diagnostic"
  | "retired_compatibility";

export interface PressureMapActionContract {
  disposition: PressureMapActionDisposition;
  owner: string;
  target: string | null;
  controlLabel: string | null;
}

export const PRESSURE_MAP_ACTION_REGISTRY = {
  create_plan: {
    disposition: "canonical_command",
    owner: "TaskManager via usePressureMapPlanCommit",
    target: "POST /v1/tasks after explicit preview confirmation",
    controlLabel: "Preview plan draft",
  },
  review_calendar: {
    disposition: "navigation",
    owner: "Settings integrations",
    target: "/settings#integrations",
    controlLabel: "Open integrations",
  },
  confirm_coverage: {
    disposition: "diagnostic",
    owner: "No canonical correction command",
    target: null,
    controlLabel: null,
  },
  clear_or_ignore: {
    disposition: "diagnostic",
    owner: "Pressure Map read-only projection",
    target: null,
    controlLabel: null,
  },
  split_into_blocks: {
    disposition: "retired_compatibility",
    owner: "No canonical split command",
    target: null,
    controlLabel: null,
  },
} satisfies Record<AcademicRecoveryAction, PressureMapActionContract>;

export function pressureMapActionContract(
  action: AcademicRecoveryAction,
): PressureMapActionContract {
  return PRESSURE_MAP_ACTION_REGISTRY[action];
}

export interface PressurePlanOptionSelection {
  planOption: AcademicRecoveryOption | null;
  navigationOption: AcademicRecoveryOption | null;
  primaryRecoveryOption: AcademicRecoveryOption | null;
  canPreviewPlan: boolean;
  primaryIsPlanOption: boolean;
}

export function selectPressurePlanOption(
  pressure: AcademicPressureMapResponse | null,
): PressurePlanOptionSelection {
  if (!pressure) {
    return {
      planOption: null,
      navigationOption: null,
      primaryRecoveryOption: null,
      canPreviewPlan: false,
      primaryIsPlanOption: false,
    };
  }

  const planOption = pressure.recovery_options.find(
    (option) => option.action === "create_plan",
  ) ?? null;
  const navigationOption = pressure.recovery_options.find(
    (option) => pressureMapActionContract(option.action).disposition === "navigation",
  ) ?? null;
  const primaryRecoveryOption = pressure.recovery_options[0] ?? null;
  const canPreviewPlan = planItemsForOption(pressure, planOption).length > 0;
  const primaryIsPlanOption =
    primaryRecoveryOption !== null &&
    planOption !== null &&
    primaryRecoveryOption.action === planOption.action;

  return {
    planOption,
    navigationOption,
    primaryRecoveryOption,
    canPreviewPlan,
    primaryIsPlanOption,
  };
}
