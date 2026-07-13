#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const planning = read("frontend/lib/pressure-map-planning.ts");
const options = read("frontend/lib/pressure-map-options.ts");
const preview = read("frontend/components/pulse/PulseAcademicPressureMap.tsx");
const commit = read("frontend/components/pulse/use-pressure-map-plan-commit.ts");
const calendar = read("frontend/app/(app)/calendar/page.tsx");
const integrations = read("frontend/components/integrations-section.tsx");

assert(
  planning.includes("suggestedDurationMinutes: number")
    && planning.includes("suggestedDurationMinutes: duration"),
  "Pressure Map must preserve the system suggestion separately from user-edited block duration",
);

assert(
  planning.includes("personal timing evidence from")
    && planning.includes("research/population starting estimate")
    && planning.includes('sources.join(" + ")'),
  "Pressure Map provenance must expose broad personal and starting-evidence classes",
);

assert(
  !planning.includes("archetype ${calibration.archetype_id}")
    && !planning.includes("archetype fallback"),
  "Pressure Map provenance must not expose raw archetype identity labels",
);

assert(
  commit.includes("suggestedDurationMinutes: minutes")
    && commit.includes("`Estimate source: ${row.estimateSource}`"),
  "calibration must update the preserved suggestion and confirmed tasks must retain safe provenance",
);

assert(
  preview.includes('data-testid="pressure-map-plan-row-estimate-source"')
    && preview.includes("LyraOS&apos;s starting estimate:")
    && preview.includes("start the timer to prove it right or wrong")
    && preview.includes("This is planning footprint, not execution truth."),
  "Pressure Map preview must make the estimate useful, editable, and bounded",
);

assert(
  options.includes('disposition: "canonical_command"')
    && options.includes('owner: "TaskManager via usePressureMapPlanCommit"')
    && options.includes('target: "POST /v1/tasks after explicit preview confirmation"')
    && options.includes('disposition: "navigation"')
    && options.includes('target: "/settings#integrations"')
    && options.includes('owner: "No canonical correction command"')
    && options.includes('disposition: "retired_compatibility"'),
  "every Pressure Map response action must declare an exact command, navigation, diagnostic, or retired owner/target",
);

assert(
  options.includes('(option) => option.action === "create_plan"')
    && !options.includes('find((option) => option.action === "split_into_blocks")'),
  "the frontend must select only the honest plan-draft command and must not revive the retired split action",
);

assert(
  options.includes("function pressureActionRank(")
    && options.includes('contract.disposition === "canonical_command"')
    && options.includes('contract.disposition === "navigation"')
    && options.includes("pressureActionRank(left.option, canPreviewPlan)")
    && !options.includes("pressure.recovery_options[0] ?? null"),
  "Pressure Map primary action must use deterministic executable-first ranking rather than backend array order",
);

assert(
  preview.includes("<DialogTitle>Plan draft</DialogTitle>")
    && preview.includes("does not check free-time capacity")
    && preview.includes('data-testid="pressure-map-review-calendar"')
    && preview.includes('? "Planning note"')
    && !preview.includes("Preview recovery plan")
    && !preview.includes("Next recovery option"),
  "Pressure Map must distinguish plan drafts, navigation, and non-clickable planning notes",
);

assert(
  preview.includes('data-testid="pressure-map-orientation-summary"')
    && preview.includes('data-testid="pressure-map-orientation-facts"')
    && preview.includes("data-fact-count={orientationFacts.length}")
    && preview.includes(".slice(0, 3)")
    && preview.includes('testId: "pressure-map-main-cause"')
    && preview.includes('testId: "pressure-map-largest-caveat"')
    && preview.includes('data-testid="pressure-map-hidden-items"')
    && preview.includes('data-testid="pressure-map-hidden-reasons"')
    && preview.includes('data-testid="pressure-map-calibration-cue"')
    && preview.includes('data-testid="pressure-map-primary-action"')
    && preview.includes('data-testid="pressure-map-secondary-navigation"')
    && preview.includes("Start the next timer to make the next estimate more yours.")
    && preview.includes('? "Planning note"')
    && preview.includes(': "Primary action"'),
  "Pressure Map must bound its orientation facts, disclose capped content, and expose exactly one primary action",
);

assert(
  integrations.includes('<Card id="integrations" tabIndex={-1}>'),
  "review_calendar navigation must terminate at the existing Settings integrations surface",
);

assert(
  calendar.includes('dayBoundaries: { start: "00:00", end: "24:00" }')
    && calendar.includes("const endHour = 24;"),
  "Pressure Map recovery blocks before 06:00 or crossing 23:00 must remain visible in Calendar",
);

const browserProof = read("scripts/browser_holmesberg_product_loop_dogfood.mjs");
assert(
  browserProof.includes("mobile Calendar keeps the pressure-map recovery block inspectable")
    && browserProof.includes("calendar-pressure-map-commit-day-mobile"),
  "Pressure Map Calendar proof must retain the mobile off-hours visibility check",
);

console.log(JSON.stringify({
  ok: true,
  checked: "pressure_map_planning_provenance_contract",
}));
