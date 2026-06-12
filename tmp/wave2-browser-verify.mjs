import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const { chromium } = playwright;
const require = createRequire(import.meta.url);
const { encode } = require("../frontend/node_modules/next-auth/jwt");

const port = process.env.WAVE2_FRONTEND_PORT || "3212";
const origin = `http://127.0.0.1:${port}`;
const outDir = new URL("./", import.meta.url);
const outPath = (name) => fileURLToPath(new URL(name, outDir));
const nextAuthSecret =
  process.env.NEXTAUTH_SECRET || "wave2-local-secret-value-at-least-32-chars";

const now = new Date();
const nowIso = now.toISOString();
let fixtureMode = "tiers";
let resolved73h = false;
let resolveBody = null;

function corsHeaders() {
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-headers": "authorization, content-type, x-idempotency-key",
    "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "access-control-allow-credentials": "true",
  };
}

function json(body, status = 200) {
  return {
    status,
    contentType: "application/json",
    headers: corsHeaders(),
    body: JSON.stringify(body),
  };
}

function isoOffsetMinutes(minutes) {
  return new Date(now.getTime() + minutes * 60_000).toISOString();
}

function taskRow(overrides) {
  return {
    task_id: "task",
    title: "Task",
    description: null,
    start: isoOffsetMinutes(-30),
    end: isoOffsetMinutes(30),
    state: "PLANNED",
    category: "study",
    is_anchor: false,
    rct_arm: null,
    initiation_status: "not_started",
    session_index_in_day: 0,
    pre_task_readiness: null,
    post_task_reflection: null,
    planned_duration_minutes: 60,
    executed_duration_minutes: null,
    duration_delta_minutes: null,
    executed_start: null,
    executed_end: null,
    effective_executed_duration_minutes: null,
    effective_duration_delta_minutes: null,
    effective_executed_end: null,
    execution_duration_provenance: "observed",
    execution_correction_id: null,
    voided_at: null,
    discrepancy_score: null,
    signed_discrepancy: null,
    initiation_delay_minutes: null,
    total_paused_minutes: 0,
    pause_count: 0,
    task_completion_percentage: null,
    voided_reason: null,
    notion_page_id: null,
    deadline_id: null,
    deadline_match_source: null,
    deadline_match_confidence: null,
    deadline_title: null,
    llm_parse_status: null,
    llm_inferred_deadline_id: null,
    llm_deadline_match_confidence: null,
    llm_deadline_candidates: null,
    llm_priority: null,
    llm_binding_rejected_at: null,
    llm_alternative_suggestion: null,
    ...overrides,
  };
}

function stopwatchStatus() {
  if (fixtureMode === "stale") {
    if (resolved73h) {
      return {
        active: false,
        paused: false,
        elapsed_minutes: 0,
        elapsed_seconds: 0,
        paused_others: [],
      };
    }
    return {
      active: true,
      task_id: "p73",
      task_title: "Parked 73h",
      session_id: "s73",
      start_time: isoOffsetMinutes(-74 * 60),
      elapsed_minutes: 91,
      elapsed_seconds: 91 * 60,
      planned_duration_minutes: 90,
      paused: true,
      total_paused_minutes: 0,
      current_pause_seconds: 73 * 60 * 60,
      current_pause_started_at: isoOffsetMinutes(-73 * 60),
      paused_others: [],
    };
  }
  return {
    active: true,
    task_id: "p30",
    task_title: "Parked 30m",
    session_id: "s30",
    start_time: isoOffsetMinutes(-45),
    elapsed_minutes: 12,
    elapsed_seconds: 12 * 60,
    planned_duration_minutes: 60,
    paused: true,
    total_paused_minutes: 0,
    current_pause_seconds: 30 * 60,
    current_pause_started_at: isoOffsetMinutes(-30),
    paused_others: [
      {
        task_id: "p8",
        title: "Parked 8h",
        session_id: "s8",
        paused_minutes: 8 * 60,
        elapsed_minutes: 22,
        elapsed_seconds: 22 * 60,
        start_time: isoOffsetMinutes(-9 * 60),
        total_paused_minutes: 0,
        planned_duration_minutes: 60,
      },
      {
        task_id: "p25",
        title: "Parked 25h",
        session_id: "s25",
        paused_minutes: 25 * 60,
        elapsed_minutes: 34,
        elapsed_seconds: 34 * 60,
        start_time: isoOffsetMinutes(-26 * 60),
        total_paused_minutes: 0,
        planned_duration_minutes: 75,
      },
    ],
  };
}

function pressureMapPayload() {
  return {
    generated_at_utc: nowIso,
    horizon_days: 14,
    headline: "No urgent pressure detected",
    pressure_summary: "No active obligations in this verification fixture.",
    items: [],
    compression_points: [],
    recovery_options: [],
    coverage_questions: [],
    capacity_context: {
      known_busy_minutes: 0,
      planned_lyra_minutes: 0,
      estimated_academic_low_minutes: 0,
      estimated_academic_high_minutes: 0,
      google_calendar_connected: false,
      caveat: "Verification fixture.",
    },
    estimated_low_minutes: 0,
    estimated_high_minutes: 0,
    source_summary: {
      deadlines_total: 0,
      external_obligation_count: 0,
      native_obligation_count: 0,
      academic_task_count: 0,
      study_task_count: 0,
      academic_task_minutes: 0,
      study_task_minutes: 0,
      google_calendar_connected: false,
      calendar_busy_minutes: 0,
      planned_lyra_minutes: 0,
    },
    methodology: [],
    warnings: [],
    exposure_id: null,
  };
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });

  page.on("console", (msg) => {
    if (msg.type() === "error") console.error(`[browser console] ${msg.text()}`);
  });

  await page.route("**/api/auth/session**", async (route) => {
    await route.fulfill(
      json({
        user: { name: "Wave Two", email: "wave2-browser@example.test", image: null },
        expires: "2099-01-01T00:00:00.000Z",
        backendToken: "wave2-local-token",
      })
    );
  });

  const sessionCookie = await encode({
    secret: nextAuthSecret,
    token: {
      sub: "wave2-google-sub",
      email: "wave2-browser@example.test",
      name: "Wave Two",
      given_name: "Wave",
      backendToken: "wave2-local-token",
    },
  });
  await page.context().addCookies([
    {
      name: "next-auth.session-token",
      value: sessionCookie,
      url: origin,
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders(), body: "" });
      return;
    }
    if (url.pathname === "/v1/users/me") {
      await route.fulfill(
        json({
          user_id: 9202,
          email: "wave2-browser@example.test",
          terms_accepted_at: nowIso,
          onboarding_completed_at: nowIso,
          has_active_task_history: true,
          tutorial_completed_at: nowIso,
          tutorial_skipped_at: null,
          archetype_survey_eligible: false,
          archetype_assignment_completed: true,
          archetype_retrofit_dismissed_at: nowIso,
          archetype_id: null,
          executed_session_count: 3,
          google_calendar_connected: false,
          is_operator: true,
        })
      );
      return;
    }
    if (url.pathname === "/v1/stopwatch/status") {
      await route.fulfill(json(stopwatchStatus()));
      return;
    }
    if (url.pathname === "/v1/tasks/query") {
      await route.fulfill(
        json({
          tasks: [
            taskRow({
              task_id: "executed-no-card",
              title: "Executed task must not be re-entry",
              state: "EXECUTED",
              start: isoOffsetMinutes(-180),
              end: isoOffsetMinutes(-120),
              planned_duration_minutes: 60,
              executed_start: isoOffsetMinutes(-180),
              executed_end: isoOffsetMinutes(-125),
              executed_duration_minutes: 55,
              duration_delta_minutes: 5,
              post_task_reflection: 4,
            }),
          ],
          total: 1,
        })
      );
      return;
    }
    if (url.pathname === "/v1/deadlines") {
      await route.fulfill(json({ deadlines: [], total: 0 }));
      return;
    }
    if (url.pathname === "/v1/integrations") {
      await route.fulfill(json({ integrations: [] }));
      return;
    }
    if (url.pathname === "/v1/academic/pressure-map") {
      await route.fulfill(json(pressureMapPayload()));
      return;
    }
    if (url.pathname === "/v1/notifications/web/pending") {
      await route.fulfill(json({ notifications: [], count: 0 }));
      return;
    }
    if (url.pathname === "/v1/notifications/web/ack") {
      await route.fulfill(json({ acknowledged: 0 }));
      return;
    }
    if (url.pathname === "/v1/stopwatch/stale-pauses/s73/resolve") {
      resolveBody = request.postDataJSON();
      resolved73h = true;
      await route.fulfill(
        json({
          resolved: true,
          task_id: "p73",
          session_id: "s73",
          new_state: "EXECUTED",
          active_minutes: 91,
          planned_duration_minutes: 90,
          paused_minutes: 73 * 60,
          task_completion_percentage: resolveBody.task_completion_percentage,
          post_task_reflection: resolveBody.post_task_reflection,
          scope_outcome: resolveBody.scope_outcome,
          data_quality_flag: "user_resolved_stale_pause",
          closed_at: isoOffsetMinutes(-73 * 60),
        })
      );
      return;
    }
    if (url.pathname.includes("/ack/render")) {
      await route.fulfill(json({ ok: true }));
      return;
    }
    await route.fulfill(json({ ok: true }));
  });

  await page.goto(`${origin}/pulse#quick-capture`, { waitUntil: "domcontentloaded" });
  const reentry = page.locator('section[aria-label="Re-entry queue"]');
  await reentry.getByText("Parked 30m").waitFor({ timeout: 15_000 });
  await reentry.getByText("Parked 8h").waitFor({ timeout: 15_000 });
  await reentry.getByText("Parked 25h").waitFor({ timeout: 15_000 });

  const reentryText = await reentry.innerText();
  const requiredCopy = [
    "Paused for 30m. Pick it back up?",
    "Parked for 8h. Pick up, reschedule, or leave parked.",
    "Open thread from earlier. Parked for 25h.",
  ];
  for (const text of requiredCopy) {
    if (!reentryText.includes(text)) {
      throw new Error(`Missing Wave 2 re-entry copy: ${text}`);
    }
  }
  if (reentryText.includes("Executed task must not be re-entry")) {
    throw new Error("EXECUTED task appeared in the re-entry queue.");
  }
  await page.screenshot({ path: outPath("wave2-reentry-tiers.png"), fullPage: true });

  fixtureMode = "stale";
  await page.reload({ waitUntil: "domcontentloaded" });
  await reentry.getByText("Parked 73h").waitFor({ timeout: 15_000 });
  const staleText = await reentry.innerText();
  await fs.writeFile(new URL("wave2-stale-reentry-text.txt", outDir), staleText);
  for (const text of ["Parked for 73h. Resolve what happened.", "Resolve session"]) {
    if (!staleText.toLowerCase().includes(text.toLowerCase())) {
      throw new Error(`Missing stale Wave 2 re-entry copy: ${text}`);
    }
  }

  await reentry.getByText("Parked 73h").scrollIntoViewIfNeeded();
  await reentry.getByRole("button", { name: "Resolve session" }).click();
  await page.getByText("How was your focus?").waitFor({ timeout: 10_000 });
  const modalText = await page.locator('[role="dialog"]').innerText();
  await fs.writeFile(new URL("wave2-modal-text.txt", outDir), modalText);
  for (const text of [
    "Active work: 1h 31m.",
    "Planned: 1h 30m.",
    "Paused: 73h.",
    "Lyra will close the session at the time you paused it.",
    "Completion % (required)",
    "Scope (required)",
  ]) {
    if (!modalText.includes(text)) {
      throw new Error(`Missing stale-resolution modal copy: ${text}`);
    }
  }
  await page.screenshot({
    path: outPath("wave2-stale-resolution-modal.png"),
    fullPage: true,
  });

  await page.getByText("Weak - distracted more than working").click();
  await page.locator("#pct").fill("90");
  await page.getByText("Expanded scope").click();
  await page.getByRole("button", { name: "Resolve session" }).click();
  await page.waitForTimeout(750);

  if (!resolveBody) {
    throw new Error("Stale-pause resolve endpoint was not called.");
  }
  const expectedBody = {
    post_task_reflection: 2,
    task_completion_percentage: 90,
    scope_outcome: "expanded",
  };
  for (const [key, value] of Object.entries(expectedBody)) {
    if (resolveBody[key] !== value) {
      throw new Error(
        `Resolve body ${key} mismatch: expected ${value}, got ${resolveBody[key]}`
      );
    }
  }
  const afterText = await page.locator("body").innerText();
  if (afterText.includes("Parked 73h")) {
    throw new Error("Resolved 73h card remained visible after resolution.");
  }
  await page.screenshot({ path: outPath("wave2-after-resolution.png"), fullPage: true });

  await browser.close();
  await fs.writeFile(
    new URL("wave2-browser-verify-result.json", outDir),
    JSON.stringify({ ok: true, resolveBody }, null, 2)
  );
}

main().catch(async (error) => {
  await fs
    .writeFile(
      new URL("wave2-browser-verify-result.json", outDir),
      JSON.stringify({ ok: false, error: String(error?.stack || error) }, null, 2)
    )
    .catch(() => {});
  console.error(error);
  process.exit(1);
});
