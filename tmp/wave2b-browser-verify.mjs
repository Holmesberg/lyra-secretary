import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const { chromium } = playwright;
const require = createRequire(import.meta.url);
const { encode } = require("../frontend/node_modules/next-auth/jwt");

const port = process.env.WAVE2B_FRONTEND_PORT || "3214";
const origin = `http://127.0.0.1:${port}`;
const outDir = new URL("./", import.meta.url);
const outPath = (name) => fileURLToPath(new URL(name, outDir));
const nextAuthSecret =
  process.env.NEXTAUTH_SECRET || "wave2b-local-secret-value-at-least-32-chars";

const now = new Date();
const nowIso = now.toISOString();
let mode = "start";
let startCalls = [];
let markDoneCalls = [];
let startSucceeded = false;
let markDoneSucceeded = false;

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
    start: isoOffsetMinutes(5),
    end: isoOffsetMinutes(50),
    state: "PLANNED",
    category: "study",
    is_anchor: false,
    rct_arm: null,
    initiation_status: "not_started",
    session_index_in_day: 0,
    pre_task_readiness: null,
    post_task_reflection: null,
    planned_duration_minutes: 45,
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

function pressureMapPayload() {
  return {
    generated_at_utc: nowIso,
    horizon_days: 14,
    headline: "No urgent pressure detected",
    pressure_summary: "Verification fixture.",
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
        user: { name: "Wave Two B", email: "wave2b-browser@example.test", image: null },
        expires: "2099-01-01T00:00:00.000Z",
        backendToken: "wave2b-local-token",
      })
    );
  });

  const sessionCookie = await encode({
    secret: nextAuthSecret,
    token: {
      sub: "wave2b-google-sub",
      email: "wave2b-browser@example.test",
      name: "Wave Two B",
      given_name: "Wave",
      backendToken: "wave2b-local-token",
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
          user_id: 9203,
          email: "wave2b-browser@example.test",
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
      await route.fulfill(
        json(
          startSucceeded
            ? {
                active: true,
                task_id: "start-task",
                task_title: "Wave 2B start target",
                session_id: "session-start",
                start_time: nowIso,
                elapsed_minutes: 0,
                elapsed_seconds: 0,
                planned_duration_minutes: 45,
                paused: false,
                total_paused_minutes: 0,
                paused_others: [],
              }
            : { active: false, paused: false, paused_others: [] }
        )
      );
      return;
    }
    if (url.pathname === "/v1/tasks/query") {
      if (mode === "markDone") {
        await route.fulfill(
          json({
            tasks: markDoneSucceeded
              ? []
              : [
                  taskRow({
                    task_id: "missed-task",
                    title: "Wave 2B missed plan",
                    start: isoOffsetMinutes(-90),
                    end: isoOffsetMinutes(-45),
                    planned_duration_minutes: 45,
                  }),
                ],
            total: markDoneSucceeded ? 0 : 1,
          })
        );
        return;
      }
      await route.fulfill(
        json({
          tasks: [
            taskRow({
              task_id: "start-task",
              title: "Wave 2B start target",
            }),
          ],
          total: 1,
        })
      );
      return;
    }
    if (url.pathname === "/v1/stopwatch/start") {
      startCalls.push(request.headers()["x-idempotency-key"] || null);
      startSucceeded = true;
      await route.fulfill(
        json({
          session_id: "session-start",
          task_id: "start-task",
          start_time: nowIso,
          is_future_task: false,
          planned_start: isoOffsetMinutes(5),
          pre_task_readiness: 3,
          initiation_delay_minutes: 0,
          parent_task_id: null,
          interruption_type: null,
        })
      );
      return;
    }
    if (url.pathname === "/v1/tasks/missed-task/mark-done") {
      markDoneCalls.push(request.headers()["x-idempotency-key"] || null);
      markDoneSucceeded = true;
      await route.fulfill(
        json({
          task_id: "missed-task",
          done: true,
          retrospective: true,
          previous_state: markDoneCalls.length > 1 ? "EXECUTED" : "PLANNED",
          new_state: "EXECUTED",
          initiation_status: "retroactive",
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
    if (url.pathname.includes("/ack/render")) {
      await route.fulfill(json({ ok: true }));
      return;
    }
    await route.fulfill(json({ ok: true }));
  });

  await page.goto(`${origin}/pulse`, { waitUntil: "domcontentloaded" });
  await page.getByText("Wave 2B start target").first().waitFor({ timeout: 15_000 });
  const startButton = page.getByRole("button", { name: /Start session/i });
  await startButton.dblclick();
  await page.getByText("Wave 2B start target").first().waitFor({ timeout: 15_000 });
  await page.waitForTimeout(500);
  if (startCalls.length < 1) {
    throw new Error("Start session call was not observed.");
  }
  if (startCalls.some((header) => !header)) {
    throw new Error(`Start call missing idempotency header: ${JSON.stringify(startCalls)}`);
  }
  const startBody = await page.locator("body").innerText();
  if (startBody.includes("Failed to start") || startBody.includes("already running")) {
    throw new Error("Start double-click surfaced an error state.");
  }
  await page.screenshot({
    path: outPath("wave2b-start-idempotency.png"),
    fullPage: true,
  });

  mode = "markDone";
  startSucceeded = false;
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByText("Wave 2B missed plan").waitFor({ timeout: 15_000 });
  const doneButton = page.getByRole("button", { name: /^Done$/i });
  await doneButton.dblclick();
  await page.waitForTimeout(700);
  if (markDoneCalls.length < 1) {
    throw new Error("Mark-done call was not observed.");
  }
  if (markDoneCalls.some((header) => !header)) {
    throw new Error(
      `Mark-done call missing idempotency header: ${JSON.stringify(markDoneCalls)}`
    );
  }
  const doneBody = await page.locator("body").innerText();
  if (doneBody.includes("Failed to mark done") || doneBody.includes("current state")) {
    throw new Error("Mark-done double-click surfaced an error state.");
  }
  if (doneBody.includes("Wave 2B missed plan")) {
    throw new Error("Mark-done card did not dismiss after successful action.");
  }
  await page.screenshot({
    path: outPath("wave2b-markdone-idempotency.png"),
    fullPage: true,
  });

  await browser.close();
  await fs.writeFile(
    new URL("wave2b-browser-verify-result.json", outDir),
    JSON.stringify({ ok: true, startCalls, markDoneCalls }, null, 2)
  );
}

main().catch(async (error) => {
  await fs
    .writeFile(
      new URL("wave2b-browser-verify-result.json", outDir),
      JSON.stringify({ ok: false, error: String(error?.stack || error) }, null, 2)
    )
    .catch(() => {});
  console.error(error);
  process.exit(1);
});
