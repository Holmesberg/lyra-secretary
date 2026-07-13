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
const preview = read("frontend/components/pulse/PulseAcademicPressureMap.tsx");
const commit = read("frontend/components/pulse/use-pressure-map-plan-commit.ts");
const calendar = read("frontend/app/(app)/calendar/page.tsx");

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
  calendar.includes('dayBoundaries: { start: "00:00", end: "24:00" }')
    && calendar.includes("const endHour = 24;"),
  "Pressure Map recovery blocks before 06:00 or crossing 23:00 must remain visible in Calendar",
);

console.log(JSON.stringify({
  ok: true,
  checked: "pressure_map_planning_provenance_contract",
}));
