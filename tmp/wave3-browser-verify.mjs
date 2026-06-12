import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const { chromium } = playwright;
const require = createRequire(import.meta.url);
const { encode } = require("../frontend/node_modules/next-auth/jwt");

const port = process.env.WAVE3_FRONTEND_PORT || "3000";
const origin = process.env.WAVE3_FRONTEND_ORIGIN || `http://localhost:${port}`;
const outDir = new URL("./", import.meta.url);
const outPath = (name) => fileURLToPath(new URL(name, outDir));
const nextAuthSecret =
  process.env.NEXTAUTH_SECRET || "wave3-local-secret-value-at-least-32-chars";

const now = new Date();
const nowIso = now.toISOString();
let pressureMode = "safe";
let createCalls = [];
let commitCalls = [];

function corsHeaders() {
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-headers":
      "authorization, content-type, x-idempotency-key",
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

async function saveScreenshot(page, name) {
  const path = outPath(name);
  try {
    await page.screenshot({ path, fullPage: true });
  } catch {
    await page.screenshot({ path });
  }
}

function isoOffsetMinutes(minutes) {
  return new Date(now.getTime() + minutes * 60_000).toISOString();
}

function pressureItem() {
  return {
    obligation_id: "ob-wave3",
    title: "Wave 3 pressure fixture",
    source: "external_obligation",
    source_class: "external",
    evidence_class: "external_obligation",
    provider_kind: "moodle",
    obligation_type: "assignment",
    complexity_tier: "medium",
    complexity_source: "operator_fixture",
    days_until_due: 2,
    pressure_level: "high",
    trust_state: "verified_reachable",
    warnings: ["coverage correctness needs confirmation"],
    estimate: {
      low_minutes: 60,
      high_minutes: 90,
      confidence: "medium",
      assumptions: ["operator fixture"],
    },
  };
}

function pressureMapPayload() {
  const items = [pressureItem()];
  const recovery_options =
    pressureMode === "plan"
      ? [
          {
            action: "confirm_coverage",
            label: "Confirm coverage",
            detail: "Check whether this obligation already has enough planned work.",
            obligation_ids: ["ob-wave3"],
          },
          {
            action: "create_plan",
            label: "Create editable focus blocks",
            detail: "Draft blocks from selected obligations.",
            obligation_ids: ["ob-wave3"],
          },
        ]
      : [];
  return {
    generated_at_utc: nowIso,
    horizon_days: 14,
    headline: "Wave 3 pressure fixture",
    pressure_summary: "One obligation needs planning attention.",
    items,
    compression_points: [],
    recovery_options,
    coverage_questions: [],
    capacity_context: {
      known_busy_minutes: 0,
      planned_lyra_minutes: 0,
      estimated_academic_low_minutes: 60,
      estimated_academic_high_minutes: 90,
      google_calendar_connected: false,
      caveat: "Verification fixture.",
    },
    estimated_low_minutes: 60,
    estimated_high_minutes: 90,
    source_summary: {
      deadlines_total: 1,
      external_obligation_count: 1,
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

function taskQueryPayload() {
  return {
    tasks: [],
    total: 0,
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
        user: {
          name: "Wave Three",
          email: "wave3-browser@example.test",
          image: null,
        },
        expires: "2099-01-01T00:00:00.000Z",
        backendToken: "wave3-local-token",
      }),
    );
  });

  const sessionCookie = await encode({
    secret: nextAuthSecret,
    token: {
      sub: "wave3-google-sub",
      email: "wave3-browser@example.test",
      name: "Wave Three",
      given_name: "Wave",
      backendToken: "wave3-local-token",
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
          user_id: 9303,
          email: "wave3-browser@example.test",
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
        }),
      );
      return;
    }
    if (url.pathname === "/v1/stopwatch/status") {
      await route.fulfill(json({ active: false, paused: false, paused_others: [] }));
      return;
    }
    if (url.pathname === "/v1/tasks/query") {
      await route.fulfill(json(taskQueryPayload()));
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
    if (url.pathname === "/v1/academic/pressure-map") {
      await route.fulfill(json(pressureMapPayload()));
      return;
    }
    if (url.pathname === "/v1/analytics/bias_factor/lookup") {
      await route.fulfill(
        json({
          category: url.searchParams.get("category") ?? "planning",
          time_of_day: url.searchParams.get("time_of_day") ?? "afternoon",
          planned_minutes: Number(url.searchParams.get("planned_minutes") ?? 60),
          bias_factor_final: 1,
          source: "research",
          signal_level: "cold_start",
          sessions: 0,
          archetype_id: null,
          execution_suggested_minutes: 60,
          occupancy_suggested_minutes: 60,
          pause_overhead_minutes: null,
          pause_overhead_sample_size: 0,
        }),
      );
      return;
    }
    if (url.pathname === "/v1/create") {
      const body = request.postDataJSON();
      createCalls.push(body);
      if (!body.force) {
        await route.fulfill(
          json({
            task_id: null,
            created: false,
            notion_synced: false,
            severity: "soft",
            soft_reasons: ["planned_overlap"],
            conflicts: [
              {
                task_id: "existing-conflict",
                title: "Existing planned block",
                start: isoOffsetMinutes(45),
                end: isoOffsetMinutes(90),
                state: "PLANNED",
                gate_id: "planned_overlap",
              },
            ],
            can_proceed: true,
          }),
        );
        return;
      }
      await route.fulfill(
        json({
          task_id: "forced-wave3-block",
          created: true,
          notion_synced: false,
          severity: null,
          soft_reasons: [],
          conflicts: [],
          can_proceed: true,
        }),
      );
      return;
    }
    if (url.pathname === "/v1/brain-dump/parse") {
      await route.fulfill(
        json({
          parser_status: "heuristic_parsed",
          items: [
            {
              item_id: "failed-task",
              kind: "task",
              title: "Wave 3 failed parse item",
              description: null,
              when_local: isoOffsetMinutes(-120),
              duration_minutes: 30,
              category: "planning",
              category_source: "operator_fixture",
              duration_source: "explicit",
              duration_confidence: 1,
              duration_basis: null,
              confidence: 1,
            },
          ],
          bindings: [],
        }),
      );
      return;
    }
    if (url.pathname === "/v1/brain-dump/commit") {
      const headers = request.headers();
      commitCalls.push({
        key: headers["x-idempotency-key"] || null,
        body: request.postDataJSON(),
      });
      if (commitCalls.length === 1) {
        await route.fulfill(
          json({
            tasks_created: 0,
            deadlines_created: 0,
            bindings_applied: 0,
            task_ids: [],
            deadline_ids: [],
            failed_items: [
              {
                item_id: "failed-task",
                kind: "task",
                title: "Wave 3 failed parse item",
                reason: "past_time",
                detail: "start_in_past",
                retry_hint: "schedule_tomorrow_same_time",
              },
            ],
          }),
        );
        return;
      }
      await route.fulfill(
        json({
          tasks_created: 1,
          deadlines_created: 0,
          bindings_applied: 0,
          task_ids: ["retry-task"],
          deadline_ids: [],
          failed_items: [],
        }),
      );
      return;
    }
    await route.fulfill(json({ ok: true }));
  });

  await page.goto(`${origin}/pulse`, { waitUntil: "domcontentloaded" });
  try {
    await page.getByText("Wave 3 pressure fixture").waitFor({ timeout: 15_000 });
  } catch (error) {
    await saveScreenshot(page, "wave3-pressure-fixture-missing.png");
    await fs.writeFile(
      new URL("wave3-pressure-fixture-missing.txt", outDir),
      await page.locator("body").innerText().catch(() => "<no body text>"),
    );
    throw error;
  }
  let bodyText = await page.locator("body").innerText();
  if (bodyText.includes("Preview focus blocks") || bodyText.includes("Planning option")) {
    throw new Error("Safe-mode pressure payload exposed creation controls.");
  }
  await saveScreenshot(page, "wave3-pressure-safe-mode.png");

  pressureMode = "plan";
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByText("Planning option").waitFor({ timeout: 15_000 });
  const nextRecoveryText = await page
    .locator("text=Next recovery option")
    .locator("xpath=ancestor::div[contains(@class,'rounded-sm')][1]")
    .innerText();
  if (nextRecoveryText.includes("Preview")) {
    throw new Error("Confirm-coverage recovery card still carries preview action.");
  }
  await page.getByRole("button", { name: /^Preview$/ }).click();
  await page.getByText("Preview recovery plan").waitFor({ timeout: 15_000 });
  await page.getByRole("button", { name: /Lock in 1 block/i }).click();
  try {
    await page.getByRole("button", { name: /Create anyway/i }).waitFor({
      timeout: 15_000,
    });
  } catch (error) {
    await page.screenshot({
      path: outPath("wave3-create-anyway-missing.png"),
      fullPage: true,
    });
    await fs.writeFile(
      new URL("wave3-create-anyway-missing.txt", outDir),
      JSON.stringify(
        {
          createCalls,
          body: await page.locator("body").innerText().catch(() => "<no body text>"),
        },
        null,
        2,
      ),
    );
    throw error;
  }
  await saveScreenshot(page, "wave3-pressure-create-anyway.png");
  await page.getByRole("button", { name: /Create anyway/i }).click();
  await page.getByText("Created.").waitFor({ timeout: 15_000 });
  if (createCalls.length !== 2 || createCalls[1]?.force !== true) {
    throw new Error(`Expected forced retry create call, got ${JSON.stringify(createCalls)}`);
  }

  const dismissButton = page.getByRole("button", { name: /Dismiss/i });
  if (await dismissButton.isVisible().catch(() => false)) {
    await dismissButton.click({ timeout: 2_000 }).catch(() => {});
  }
  await page.getByPlaceholder(/Brain dump anything/i).fill("past item");
  await page.getByRole("button", { name: /Capture/i }).click();
  await page.getByRole("button", { name: /^Parse$/i }).click();
  let brainTitleInput = page.locator('[role="dialog"] input').first();
  await brainTitleInput.waitFor({ timeout: 15_000 });
  if ((await brainTitleInput.inputValue()) !== "Wave 3 failed parse item") {
    throw new Error("Parsed brain-dump title input was not visible.");
  }
  await page.getByRole("button", { name: /Lock in/i }).click();
  await page.getByText("Wave 3 failed parse item").waitFor({ timeout: 15_000 });
  await page.getByRole("button", { name: /Edit failed items/i }).click();
  brainTitleInput = page.locator('[role="dialog"] input').first();
  await brainTitleInput.waitFor({ timeout: 15_000 });
  if ((await brainTitleInput.inputValue()) !== "Wave 3 failed parse item") {
    throw new Error("Failed brain-dump item text was not preserved for retry.");
  }
  await brainTitleInput.fill("Wave 3 recovered item");
  const startInput = page.locator('input[type="datetime-local"]').first();
  const futureLocal = new Date(now.getTime() + 24 * 60 * 60_000)
    .toISOString()
    .slice(0, 16);
  await startInput.fill(futureLocal);
  await saveScreenshot(page, "wave3-brain-dump-edit-retry.png");
  await page.getByRole("button", { name: /Lock in/i }).click();
  await page.getByText(/Locked in/i).waitFor({ timeout: 15_000 });

  if (commitCalls.length !== 2) {
    throw new Error(`Expected two brain-dump commit attempts, got ${commitCalls.length}`);
  }
  if (commitCalls.some((call) => !call.key)) {
    throw new Error(`Brain-dump commit missing idempotency key: ${JSON.stringify(commitCalls)}`);
  }
  if (commitCalls[0].key === commitCalls[1].key) {
    throw new Error("Edited brain-dump retry reused the failed commit idempotency key.");
  }
  if (commitCalls[1].body.items[0].title !== "Wave 3 recovered item") {
    throw new Error(`Retry did not preserve edited title: ${JSON.stringify(commitCalls[1])}`);
  }

  bodyText = await page.locator("body").innerText();
  for (const forbidden of ["avoidance", "motivation", "discipline", "fragmentation score", "focus score"]) {
    if (bodyText.toLowerCase().includes(forbidden)) {
      throw new Error(`Forbidden copy appeared in Wave 3 flow: ${forbidden}`);
    }
  }

  await browser.close();
  await fs.writeFile(
    new URL("wave3-browser-verify-result.json", outDir),
    JSON.stringify({ ok: true, origin, createCalls, commitCalls }, null, 2),
  );
}

main().catch(async (error) => {
  await fs
    .writeFile(
      new URL("wave3-browser-verify-result.json", outDir),
      JSON.stringify({ ok: false, error: String(error?.stack || error) }, null, 2),
    )
    .catch(() => {});
  console.error(error);
  process.exit(1);
});
