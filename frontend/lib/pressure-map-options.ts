import type {
  AcademicPressureMapResponse,
  AcademicRecoveryOption,
} from "@/lib/academic";
import { planItemsForOption } from "@/lib/pressure-map-planning";

export interface PressurePlanOptionSelection {
  planOption: AcademicRecoveryOption | null;
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
      primaryRecoveryOption: null,
      canPreviewPlan: false,
      primaryIsPlanOption: false,
    };
  }

  const planOption =
    pressure.recovery_options.find((option) => option.action === "create_plan") ??
    pressure.recovery_options.find((option) => option.action === "split_into_blocks") ??
    null;
  const primaryRecoveryOption = pressure.recovery_options[0] ?? null;
  const canPreviewPlan = planItemsForOption(pressure, planOption).length > 0;
  const primaryIsPlanOption =
    primaryRecoveryOption !== null &&
    planOption !== null &&
    primaryRecoveryOption.action === planOption.action;

  return {
    planOption,
    primaryRecoveryOption,
    canPreviewPlan,
    primaryIsPlanOption,
  };
}
