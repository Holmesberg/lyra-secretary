#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { createHash, randomUUID } from "node:crypto";

import {
  apiFetch as helperApiFetch,
  frontendRequire,
  parseAndExpandCookies,
  repoRoot,
  resolveBackendTokenFromContext,
  userRef,
} from "./browser_auth_helpers.mjs";

const { chromium } = frontendRequire("playwright");

const args = new Map();
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (!arg.startsWith("--")) continue;
  const key = arg.slice(2);
  const next = process.argv[i + 1];
  if (next && !next.startsWith("--")) {
    args.set(key, next);
    i += 1;
  } else {
    args.set(key, "true");
  }
}

const topology = args.get("topology") || "local";
const frontendOrigin = args.get("frontend")
  || process.env.LYRA_FRONTEND_ORIGIN
  || (topology === "public" ? "https://lyraos.org" : "http://localhost:3000");
const apiOrigin = args.get("api")
  || process.env.LYRA_API_ORIGIN
  || (topology === "public" ? "https://api.lyraos.org" : "http://localhost:8000");
const outDir = path.resolve(
  args.get("out-dir")
  || path.join(
    repoRoot,
    "tmp",
    "browser-calendar-table-mutation",
    new Date().toISOString().replace(/[:.]/g, "-"),
  ),
);
const runId = args.get("run-id") || `calendar-table-${Date.now()}-${randomUUID().slice(0, 8)}`;
const runKey = boundedIdentifier(runId, 42);
const prefix = args.get("prefix") || `DOGFOOD CT ${randomUUID().slice(0, 8)}`;
const cleanupOnly = args.get("cleanup-only") === "true";
const calendarOnly = args.get("calendar-only") === "true";
const proxyApi = args.get("proxy-api") === "true";
const fixtureAccountReady = args.get("fixture-account-ready") === "true";
const holmesbergCookie = process.env.LYRA_COOKIE_HOLMESBERG
  || process.env.LYRA_COOKIE_MORIARTY
  || "";

const checks = [];
const issues = [];
const gated = [];
const cleanup = {
  tasks: new Set(),
  exposureSuppressions: new Set(),
};

function addCheck(name, ok, detail = null) {
  checks.push({ name, ok: Boolean(ok), detail });
  if (!ok) {
    throw Object.assign(new Error(name), { detail });
  }
}

function addIssue(name, detail = null) {
  issues.push({ name, detail });
}

function addGated(name, reason) {
  gated.push({ name, reason });
}

function boundedIdentifier(value, maxLength = 64) {
  const raw = String(value || "dogfood");
  const safe = raw.replace(/[^A-Za-z0-9_.:-]/g, "-");
  if (safe.length <= maxLength) return safe;
  const hash = createHash("sha256").update(raw).digest("hex").slice(0, 12);
  const headLength = Math.max(1, maxLength - hash.length - 1);
  const head = safe.slice(0, headLength).replace(/[-_.:]+$/g, "") || "dogfood";
  return `${head}-${hash}`.slice(0, maxLength);
}

function dateKey(date = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function localInput(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function futureDate(minutesFromNow) {
  return new Date(Date.now() + minutesFromNow * 60_000);
}

function floorToMinute(date) {
  const next = new Date(date);
  next.setSeconds(0, 0);
  return next;
}

function calendarVisibleTaskStart(durationMinutes = 45) {
  const now = new Date();
  const candidate = new Date(now.getTime() + 10 * 60_000);
  const candidateEnd = new Date(candidate.getTime() + durationMinutes * 60_000);
  if (dateKey(candidate) === dateKey(now) && dateKey(candidateEnd) === dateKey(now)) {
    return floorToMinute(candidate);
  }
  // Keep the fixture in one day without creating a task in the past. The
  // Calendar week view includes tomorrow except at the separately tracked
  // end-of-week boundary.
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0, 0, 0);
}

function iso(date) {
  return date.toISOString();
}

function rows(body, key) {
  return Array.isArray(body?.[key]) ? body[key] : [];
}

function exposureSortTime(row) {
  return row?.delivered_at || row?.eligible_at || row?.created_at || "";
}

function missingSyntheticCreationNudgeExposures(beforeExport, afterExport) {
  const beforeIds = new Set(rows(beforeExport, "exposure_decision_events").map((row) => row.exposure_id));
  const renderIds = new Set(rows(afterExport, "exposure_render_events").map((row) => row.exposure_id));
  const ackIds = new Set(
    rows(afterExport, "exposure_ack_events")
      .filter((row) => row.event_type === "render")
      .map((row) => row.exposure_id),
  );
  const suppressionIds = new Set(rows(afterExport, "suppression_events").map((row) => row.exposure_id));
  return rows(afterExport, "exposure_decision_events")
    .filter((row) => !beforeIds.has(row.exposure_id))
    .filter((row) => row.content_template_id === "task_creation_nudge_lookup")
    .filter((row) => row.trigger_source === "analytics.bias_factor.lookup")
    .filter((row) => row.decision_status === "delivered")
    .filter((row) => !row.task_id)
    .filter((row) => !renderIds.has(row.exposure_id))
    .filter((row) => !ackIds.has(row.exposure_id))
    .filter((row) => !suppressionIds.has(row.exposure_id))
    .sort((a, b) => String(exposureSortTime(b)).localeCompare(String(exposureSortTime(a))));
}

function expectNoPrivateLeak(text, label) {
  const probes = [
    "__Secure-next-auth",
    "next-auth.session-token",
    "refresh_token",
    "access_token",
    "authtoken",
    "wstoken",
    "bearer ",
    "[object Object]",
  ];
  const lowered = String(text || "").toLowerCase();
  const found = probes.filter((probe) => lowered.includes(probe.toLowerCase()));
  addCheck(`${label}: no obvious private leak markers`, found.length === 0, { found });
}

function transientApiStatus(status) {
  return [502, 503, 504, 520, 521, 522, 523, 524].includes(Number(status));
}

function transientApiError(error) {
  const message = String(error?.message || error);
  return /fetch failed|ECONNRESET|ETIMEDOUT|ENOTFOUND|EAI_AGAIN|network|socket|timeout/i.test(message);
}

async function writeJson(name, value) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(path.join(outDir, name), JSON.stringify(value, null, 2));
}

async function screenshot(page, name) {
  await fs.mkdir(outDir, { recursive: true });
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true }).catch(() => {});
  return file;
}

async function callApiWithRetry(token, pathname, init = {}, expected = null) {
  let lastError = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const result = await helperApiFetch(apiOrigin, token, pathname, init);
      if (expected) {
        const expectedStatuses = Array.isArray(expected) ? expected : [expected];
        if (!expectedStatuses.includes(result.response.status)) {
          if (transientApiStatus(result.response.status) && attempt < 3) {
            addIssue("transient API status retry", {
              pathname,
              attempt,
              status: result.response.status,
            });
            await new Promise((resolve) => setTimeout(resolve, 1_500 * attempt));
            continue;
          }
          throw Object.assign(
            new Error(`API ${pathname} returned ${result.response.status}`),
            { detail: { pathname, status: result.response.status, body: result.body } },
          );
        }
      }
      return result;
    } catch (error) {
      lastError = error;
      if (!transientApiError(error) || attempt === 3) {
        throw error;
      }
      addIssue("transient API fetch retry", {
        pathname,
        attempt,
        message: String(error?.message || error).split("\n")[0],
      });
      await new Promise((resolve) => setTimeout(resolve, 1_500 * attempt));
    }
  }
  throw lastError || new Error(`API ${pathname} failed`);
}

async function apiFetch(token, pathname, init = {}, expected = [200]) {
  const result = await callApiWithRetry(token, pathname, init, expected);
  const expectedStatuses = Array.isArray(expected) ? expected : [expected];
  if (!expectedStatuses.includes(result.response.status)) {
    throw Object.assign(
      new Error(`API ${pathname} returned ${result.response.status}`),
      { detail: { pathname, status: result.response.status, body: result.body } },
    );
  }
  return result.body;
}

async function apiTry(token, pathname, init = {}) {
  return callApiWithRetry(token, pathname, init, null);
}

async function goto(page, pathname, name) {
  await page.goto(`${frontendOrigin}${pathname}`, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
  const body = await page.locator("body").innerText({ timeout: 10_000 });
  if (/ONBOARDING|LyraOS starts learning from the first plan/i.test(body)) {
    throw Object.assign(new Error(`${name}: onboarding gate blocked route proof`), {
      detail: { pathname },
    });
  }
  await screenshot(page, name);
  return body;
}

async function installApiProxy(context) {
  const apiPattern = `${apiOrigin.replace(/\/$/, "")}/**`;
  await context.route(apiPattern, async (route) => {
    const request = route.request();
    const requestHeaders = request.headers();
    const corsHeaders = {
      "access-control-allow-origin": frontendOrigin,
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
      "access-control-allow-headers": requestHeaders["access-control-request-headers"]
        || "authorization,content-type,x-idempotency-key",
      "vary": "Origin",
    };
    if (request.method().toUpperCase() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: corsHeaders,
        body: "",
      });
      return;
    }

    const headers = { ...requestHeaders };
    delete headers.host;
    delete headers.origin;
    delete headers.referer;
    delete headers["sec-fetch-dest"];
    delete headers["sec-fetch-mode"];
    delete headers["sec-fetch-site"];

    try {
      const data = request.postDataBuffer();
      const response = await context.request.fetch(request.url(), {
        method: request.method(),
        headers,
        data: data && data.length > 0 ? data : undefined,
        timeout: 45_000,
        failOnStatusCode: false,
      });
      const responseHeaders = {
        ...response.headers(),
        ...corsHeaders,
      };
      let responseBody = await response.body();
      if (
        fixtureAccountReady
        && request.method().toUpperCase() === "GET"
        && new URL(request.url()).pathname === "/v1/users/me"
        && response.ok()
      ) {
        const me = JSON.parse(responseBody.toString("utf8"));
        me.terms_accepted_at = me.terms_accepted_at || "1970-01-01T00:00:00Z";
        me.archetype_survey_eligible = false;
        me.onboarding_completed_at = me.onboarding_completed_at || "1970-01-01T00:00:00Z";
        me.has_active_task_history = true;
        responseBody = Buffer.from(JSON.stringify(me));
        delete responseHeaders["content-encoding"];
        delete responseHeaders["content-length"];
      }
      await route.fulfill({
        status: response.status(),
        headers: responseHeaders,
        body: responseBody,
      });
    } catch (error) {
      if (/Target page, context or browser has been closed/i.test(String(error?.message || error))) {
        return;
      }
      await route.abort("failed").catch(() => {});
    }
  });
}

async function bootstrapUserContext(browser) {
  if (!holmesbergCookie || holmesbergCookie.trim().length < 100) {
    throw new Error("LYRA_COOKIE_HOLMESBERG is missing or too short");
  }
  const context = await browser.newContext({ acceptDownloads: true });
  if (proxyApi) {
    await installApiProxy(context);
  }
  await context.addCookies(parseAndExpandCookies(holmesbergCookie, frontendOrigin));
  const page = await context.newPage();
  const serverErrors = [];
  page.on("response", (response) => {
    if (response.status() >= 500) {
      serverErrors.push({ url: response.url(), status: response.status() });
    }
  });
  const token = await resolveBackendTokenFromContext(context, frontendOrigin);
  const me = await apiFetch(token, "/v1/users/me");
  addCheck("Holmesberg account resolves as non-operator", !me.is_operator, {
    user_ref: userRef(me.user_id),
  });
  return { context, page, token, me, serverErrors };
}

async function queryTasks(token) {
  const from = dateKey(new Date(Date.now() - 3 * 86400_000));
  const to = dateKey(futureDate(10 * 24 * 60));
  return apiFetch(token, `/v1/tasks/query?date_from=${from}&date_to=${to}&state=all`);
}

async function findTasksByPrefix(token) {
  const body = await queryTasks(token);
  return (body.tasks || []).filter((task) => String(task.title || "").startsWith(prefix));
}

async function findTaskByTitle(token, title) {
  const body = await queryTasks(token);
  return (body.tasks || []).find((task) => task.title === title) || null;
}

async function pollFor(description, predicate, timeoutMs = 15_000, intervalMs = 750) {
  const started = Date.now();
  let lastValue = null;
  while (Date.now() - started <= timeoutMs) {
    lastValue = await predicate();
    if (lastValue) return lastValue;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  addIssue(`${description} did not satisfy condition before timeout`, { timeout_ms: timeoutMs });
  return lastValue;
}

async function createPlannedTask(token, title, startDate, durationMinutes) {
  const endDate = new Date(startDate.getTime() + durationMinutes * 60_000);
  const body = await apiFetch(token, "/v1/create", {
    method: "POST",
    body: JSON.stringify({
      title,
      start: localInput(startDate),
      end: localInput(endDate),
      category: "study",
      description: `calendar/table dogfood ${runId}`,
      source: "web",
      force: true,
    }),
  }, [200, 201, 409]);
  const task = await findTaskByTitle(token, title);
  addCheck("planned task created and queryable", Boolean(task?.task_id), {
    title,
    response: body,
    task,
  });
  cleanup.tasks.add(task.task_id);
  return task;
}

async function createRetroactiveTask(token, title, startDate, durationMinutes, plannedDurationMinutes) {
  const endDate = new Date(startDate.getTime() + durationMinutes * 60_000);
  const body = await apiFetch(token, "/v1/stopwatch/retroactive", {
    method: "POST",
    body: JSON.stringify({
      title,
      start_time: iso(startDate),
      end_time: iso(endDate),
      post_task_reflection: 4,
      total_paused_minutes: 0,
      unplanned_reason: "forgot_to_log",
      pre_task_readiness: 3,
      category: "study",
      planned_duration_minutes: plannedDurationMinutes,
    }),
  });
  cleanup.tasks.add(body.task_id);
  const task = await findTaskByTitle(token, title);
  addCheck("retroactive executed task created and queryable", Boolean(task?.task_id), {
    title,
    body,
    task,
  });
  return task;
}

async function assertTaskInExport(token, taskId, label) {
  const exported = await apiFetch(token, "/v1/users/me/export");
  expectNoPrivateLeak(JSON.stringify(exported), `${label} export`);
  addCheck(`${label}: export includes task row`, rows(exported, "tasks").some((row) => row.task_id === taskId), {
    task_id: taskId,
  });
  return exported;
}

async function cleanupCreatedRows(token) {
  const tasks = await findTasksByPrefix(token);
  for (const task of tasks) cleanup.tasks.add(task.task_id);
  for (const taskId of cleanup.tasks) {
    await apiTry(token, `/v1/tasks/${encodeURIComponent(taskId)}/void`, {
      method: "POST",
      body: JSON.stringify({
        voided_reason: "test_contamination",
        void_reason_detail: `calendar/table dogfood cleanup ${runId}`,
      }),
    });
  }
  const status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("cleanup leaves Holmesberg with no active timer", !status.active, status);
}

async function cleanupSyntheticExposureDebt(token, beforeExport) {
  if (!beforeExport) return;
  const exported = await apiFetch(token, "/v1/users/me/export");
  const candidates = missingSyntheticCreationNudgeExposures(beforeExport, exported);
  for (const row of candidates) {
    const res = await apiFetch(token, `/v1/exposures/${encodeURIComponent(row.exposure_id)}/ack/suppress`, {
      method: "POST",
      body: JSON.stringify({
        surface: "calendar_table_mutation_dogfood_cleanup",
        suppression_reason: "dogfood_synthetic_cleanup",
      }),
    });
    if (!res?.suppressed) {
      addCheck("synthetic exposure cleanup reached terminal suppression state", false, {
        exposure_id: row.exposure_id,
        response: res,
      });
    }
    cleanup.exposureSuppressions.add(row.exposure_id);
  }
  const after = await apiFetch(token, "/v1/users/me/export");
  const remaining = missingSyntheticCreationNudgeExposures(beforeExport, after);
  addCheck("cleanup leaves no unrendered synthetic creation-nudge exposures", remaining.length === 0, {
    remaining: remaining.map((row) => row.exposure_id),
  });
}

async function gotoCalendarTaskWeek(page, start, name) {
  let body = await goto(page, "/calendar", name);
  if (new Date().getDay() === 0 && start.getDay() === 1) {
    await page.getByRole("button", { name: "Next period", exact: true }).click();
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
    await page.waitForTimeout(750);
    body = await page.locator("body").innerText({ timeout: 10_000 });
    await screenshot(page, `${name}-next-week`);
  }
  return body;
}

async function runCalendarPath(page, token) {
  const title = `${prefix} calendar movable ${runKey}`;
  const start = calendarVisibleTaskStart();
  const task = await createPlannedTask(token, title, start, 45);

  const calendarBefore = await gotoCalendarTaskWeek(page, start, "calendar-before-reschedule");
  addCheck("calendar route renders planned synthetic task", calendarBefore.includes(title), {
    title,
  });

  const newStart = new Date(start.getTime() + 5 * 60_000);
  const newEnd = new Date(newStart.getTime() + 45 * 60_000);
  const calendarEvent = page.locator(`[data-event-id="${task.task_id}"]`).first();
  await calendarEvent.waitFor({ state: "visible", timeout: 10_000 });
  await calendarEvent.click();
  await page.getByTestId("new-task-modal").waitFor({ state: "visible", timeout: 10_000 });
  await page.getByTestId("new-task-start").fill(localInput(newStart));
  await page.getByTestId("new-task-end").fill(localInput(newEnd));
  const rescheduleResponse = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && new URL(response.url()).pathname === "/v1/reschedule"
  ), { timeout: 15_000 });
  const taskRefetch = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && new URL(response.url()).pathname === "/v1/tasks/query"
    && response.status() === 200
  ), { timeout: 15_000 });
  await page.getByTestId("new-task-save").click();
  const rescheduled = await rescheduleResponse;
  addCheck("calendar edit modal accepts planned task reschedule", rescheduled.ok(), {
    status: rescheduled.status(),
  });
  await taskRefetch;
  addCheck("calendar edit invalidates and refetches task projections", true);

  const updated = await findTaskByTitle(token, title);
  addCheck("reschedule updates canonical planned task times", (
    updated?.task_id === task.task_id
    && String(updated?.start || "").slice(0, 16) !== String(task.start || "").slice(0, 16)
  ), {
    before: { start: task.start, end: task.end },
    after: updated,
  });

  const calendarAfter = await gotoCalendarTaskWeek(page, newStart, "calendar-after-reschedule");
  addCheck("calendar route renders rescheduled task after reload", calendarAfter.includes(title), {
    title,
  });

  const executed = await createRetroactiveTask(
    token,
    `${prefix} calendar executed immutable ${runKey}`,
    floorToMinute(new Date(Date.now() - 5 * 60 * 60_000)),
    30,
    40,
  );
  const rejected = await callApiWithRetry(token, "/v1/reschedule", {
    method: "POST",
    body: JSON.stringify({
      task_id: executed.task_id,
      new_start: localInput(futureDate(28 * 60)),
      new_end: localInput(futureDate(28 * 60 + 30)),
    }),
  }, [400, 409]);
  addCheck("calendar mutation authority rejects executed task reschedule", [400, 409].includes(rejected.response.status), {
    status: rejected.response.status,
    body: rejected.body,
  });

  addGated(
    "Schedule-X physical drag/resize gesture",
    "This proof exercises the same reschedule authority and browser rendering, but does not synthesize low-level drag/resize DOM gestures.",
  );
}

async function runTablePath(page, token) {
  const correctionTitle = `${prefix} table correction ${runKey}`;
  const originalStart = floorToMinute(new Date(Date.now() - 3 * 60 * 60_000));
  const originalDuration = 60;
  const correctionTask = await createRetroactiveTask(token, correctionTitle, originalStart, originalDuration, 90);
  const correctedEnd = new Date(originalStart.getTime() + 45 * 60_000);

  const tableBefore = await goto(page, "/table", "table-before-correction");
  addCheck("table route renders executed synthetic row", tableBefore.includes(correctionTitle), {
    title: correctionTitle,
  });

  await page.getByText(correctionTitle, { exact: false }).first().click();
  await page.locator('input[type="datetime-local"]').fill(localInput(correctedEnd));
  const correctionResponsePromise = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && response.url().includes(`/v1/tasks/${encodeURIComponent(correctionTask.task_id)}/execution-correction`)
  ), { timeout: 20_000 }).catch((error) => ({ error: String(error?.message || error) }));
  await page.getByRole("button", { name: /save correction/i }).click();
  const correctionResponse = await correctionResponsePromise;
  if (correctionResponse?.error) {
    addCheck("table correction request reaches backend", false, correctionResponse);
  }
  const correctionStatus = correctionResponse.status();
  let correctionBody = "";
  try {
    correctionBody = await correctionResponse.text();
  } catch {
    correctionBody = "<<unreadable>>";
  }
  let correctionPayload = null;
  try {
    correctionPayload = JSON.parse(correctionBody);
  } catch {
    correctionPayload = null;
  }
  addCheck("table correction backend response is successful", correctionStatus === 200, {
    status: correctionStatus,
    body: correctionBody.slice(0, 1000),
  });
  const expectedCorrectedMinutes = Number(correctionPayload?.corrected_executed_duration_minutes);
  addCheck("table correction response exposes corrected duration", Number.isFinite(expectedCorrectedMinutes), {
    correctionPayload,
  });
  await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
  await page.waitForTimeout(500);
  await screenshot(page, "table-after-correction-save");

  const corrected = await pollFor("table correction effective duration", async () => {
    const candidate = await findTaskByTitle(token, correctionTitle);
    return (
      candidate?.task_id === correctionTask.task_id
      && candidate?.execution_duration_provenance === "retroactive"
      && Number(candidate?.effective_executed_duration_minutes) === expectedCorrectedMinutes
    ) ? candidate : null;
  });
  addCheck("table correction updates effective executed duration", (
    corrected?.task_id === correctionTask.task_id
    && corrected?.execution_duration_provenance === "retroactive"
    && Number(corrected?.effective_executed_duration_minutes) === expectedCorrectedMinutes
  ), {
    corrected,
    expectedCorrectedMinutes,
  });

  const exported = await assertTaskInExport(token, correctionTask.task_id, "table correction");
  addCheck("export includes execution correction row", rows(exported, "task_execution_corrections").some((row) => (
    row.task_id === correctionTask.task_id
    && Number(row.corrected_executed_duration_minutes) === expectedCorrectedMinutes
  )), {
    task_id: correctionTask.task_id,
    expectedCorrectedMinutes,
  });

  const voidedTitle = `${prefix} table voided ${runKey}`;
  const voidedTask = await createPlannedTask(token, voidedTitle, calendarVisibleTaskStart(30), 30);
  await apiFetch(token, `/v1/tasks/${encodeURIComponent(voidedTask.task_id)}/void`, {
    method: "POST",
    body: JSON.stringify({
      voided_reason: "test_contamination",
      void_reason_detail: `table show-voided proof ${runId}`,
    }),
  });

  const tableDefault = await goto(page, "/table", "table-default-after-void");
  addCheck("table hides voided synthetic row by default", !tableDefault.includes(voidedTitle), {
    title: voidedTitle,
  });
  await page.getByLabel(/show voided/i).check();
  await page.waitForTimeout(500);
  const tableVoided = await page.locator("body").innerText();
  await screenshot(page, "table-show-voided");
  addCheck("table show-voided control reveals voided row", tableVoided.includes(voidedTitle), {
    title: voidedTitle,
  });

  const downloadPromise = page.waitForEvent("download", { timeout: 15_000 });
  await page.getByRole("button", { name: /export csv/i }).click();
  const download = await downloadPromise;
  const csvPath = path.join(outDir, download.suggestedFilename());
  await download.saveAs(csvPath);
  const csv = await fs.readFile(csvPath, "utf8");
  addCheck("table CSV export includes expected headers", (
    csv.includes("task_id")
    && csv.includes("actual_duration_minutes")
    && csv.includes("voided_reason")
  ), {
    first_line: csv.split(/\r?\n/)[0],
  });
  addCheck("table CSV export includes corrected and voided synthetic rows", (
    csv.includes(correctionTitle)
    && csv.includes(voidedTitle)
  ), {
    csv_path: csvPath,
  });
  const correctedCsvRow = csv.split(/\r?\n/).find((line) => line.includes(correctionTitle)) || "";
  addCheck("table CSV export uses corrected actual duration", (
    correctedCsvRow.includes(`,${expectedCorrectedMinutes},`)
  ), {
    correctedCsvRow,
    expectedCorrectedMinutes,
  });
  expectNoPrivateLeak(csv, "table CSV export");
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  let ctx = null;
  let beforeExport = null;
  try {
    ctx = await bootstrapUserContext(browser);
    beforeExport = await apiFetch(ctx.token, "/v1/users/me/export");
    expectNoPrivateLeak(JSON.stringify(beforeExport), "before export");

    if (cleanupOnly) {
      await cleanupCreatedRows(ctx.token);
      await cleanupSyntheticExposureDebt(ctx.token, beforeExport);
      const result = {
        ok: true,
        cleanup_only: true,
        run_id: runId,
        prefix,
        cleanup: {
          task_ids: [...cleanup.tasks],
          exposure_suppression_ids: [...cleanup.exposureSuppressions],
        },
        checks,
        issues,
        gated,
      };
      await writeJson("result.json", result);
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    await apiFetch(ctx.token, "/v1/operator/dashboard", {}, [403]);
    await runCalendarPath(ctx.page, ctx.token);
    if (!calendarOnly) {
      await runTablePath(ctx.page, ctx.token);
    }

    await cleanupCreatedRows(ctx.token);
    await cleanupSyntheticExposureDebt(ctx.token, beforeExport);
    const afterCleanup = await findTasksByPrefix(ctx.token);
    addCheck("cleanup leaves no non-voided synthetic tasks", afterCleanup.every((task) => task.voided_at), {
      remaining: afterCleanup.map((task) => ({
        task_id: task.task_id,
        title: task.title,
        voided_at: task.voided_at,
      })),
    });

    const result = {
      ok: true,
      topology,
      frontendOrigin,
      apiOrigin,
      fixture_account_ready: fixtureAccountReady,
      calendar_only: calendarOnly,
      run_id: runId,
      prefix,
      user_ref: userRef(ctx.me.user_id),
      checks,
      issues,
      gated,
      server_errors: ctx.serverErrors,
      cleanup: {
        task_ids: [...cleanup.tasks],
        exposure_suppression_ids: [...cleanup.exposureSuppressions],
      },
    };
    addCheck("browser observed no server 500 responses", ctx.serverErrors.length === 0, ctx.serverErrors);
    await writeJson("result.json", result);
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    const result = {
      ok: false,
      topology,
      frontendOrigin,
      apiOrigin,
      run_id: runId,
      prefix,
      error: String(error?.message || error),
      detail: error?.detail || null,
      checks,
      issues,
      gated,
      cleanup: {
        task_ids: [...cleanup.tasks],
        exposure_suppression_ids: [...cleanup.exposureSuppressions],
      },
    };
    await writeJson("result.json", result);
    if (ctx?.token) {
      try {
        await cleanupCreatedRows(ctx.token);
        await cleanupSyntheticExposureDebt(ctx.token, beforeExport);
      } catch (cleanupError) {
        addIssue("cleanup after failure failed", String(cleanupError?.message || cleanupError));
      }
    }
    await writeJson("result.json", { ...result, issues });
    console.error(JSON.stringify({ ...result, issues }, null, 2));
    process.exitCode = 1;
  } finally {
    if (ctx?.context) {
      await ctx.context.close().catch(() => {});
    }
    await browser.close().catch(() => {});
  }
}

main();
