import type { StopResponse } from "@/lib/tasks";

export type StopwatchStopOutputLifespan = "auto" | "pin";

export interface StopwatchStopOutputToast {
  message: string;
  viewId: string | null;
  lifespan: StopwatchStopOutputLifespan;
  detailHref: string;
  exposureId: string | null;
  surfaceId: "stopwatch.micro_mirror" | "stopwatch.calibration_nudge";
}

export type PushStopwatchStopOutputToast = (
  message: string,
  viewId: string | null,
  lifespan: StopwatchStopOutputLifespan,
  detailHref?: string,
  exposureId?: string | null,
  surfaceId?: string | null,
) => void;

export function getStopwatchStopOutputToasts(
  response: StopResponse,
): StopwatchStopOutputToast[] {
  const outputs: StopwatchStopOutputToast[] = [];

  if (response.micro_mirror) {
    outputs.push({
      message: response.micro_mirror,
      viewId: response.micro_mirror_view_id ?? null,
      lifespan: "auto",
      detailHref: "/insights",
      exposureId: response.micro_mirror_exposure_id ?? null,
      surfaceId: "stopwatch.micro_mirror",
    });
  }

  if (response.calibration_nudge) {
    outputs.push({
      message: response.calibration_nudge,
      viewId: response.calibration_nudge_view_id ?? null,
      lifespan: "pin",
      detailHref: "/insights",
      exposureId: response.calibration_nudge_exposure_id ?? null,
      surfaceId: "stopwatch.calibration_nudge",
    });
  }

  return outputs;
}

export function presentStopwatchStopOutputs(
  response: StopResponse,
  pushToast: PushStopwatchStopOutputToast,
) {
  for (const output of getStopwatchStopOutputToasts(response)) {
    pushToast(
      output.message,
      output.viewId,
      output.lifespan,
      output.detailHref,
      output.exposureId,
      output.surfaceId,
    );
  }
}
