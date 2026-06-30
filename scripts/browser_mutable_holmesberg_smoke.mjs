#!/usr/bin/env node
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  apiFetch,
  frontendRequire,
  parseAndExpandCookies,
  repoRoot,
  resolveBackendToken,
  userRef,
} from "./browser_auth_helpers.mjs";

const { chromium } = frontendRequire("playwright");

const frontendOrigin = process.env.LYRA_FRONTEND_ORIGIN || "http://localhost:3000";
const apiOrigin = process.env.LYRA_API_ORIGIN || "http://localhost:8000";
const cookieHeader =
  process.env.LYRA_COOKIE_HOLMESBERG
  || process.env.LYRA_COOKIE_MORIARTY
  || "";

const runId = `holmesberg-${new Date().toISOString().replace(/[:.]/g, "-")}`;
const titlePrefix = `S1C CHAOS ${runId}`;
const outDir = path.join(repoRoot, "tmp", "browser-smoke", runId);

function fail(message, detail = undefined) {
  const error = new Error(message);
  error.detail = detail;
  throw error;
}

function futureIso(minutesFromNow) {
  return new Date(Date.now() + minutesFromNow * 60_000).toISOString();
}

function localIso(minutesFromNow) {
  return futureIso(minutesFromNow);
}

async function apiJson(token, method, pathname, body = undefined, headers = {}) {
  const result = await apiFetch(apiOrigin, token, pathname, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!result.response.ok) {
    fail(`${method} ${pathname} failed`, {
      status: result.response.status,
      body: result.body,
    });
  }
  return result.body;
}

async function apiMaybe(token, method, pathname, body = undefined, headers = {}) {
  return apiFetch(apiOrigin, token, pathname, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function cleanupArtifacts(token, created) {
  const cleanup = {
    stopped_active_timer: false,
    voided_tasks: [],
    void_task_errors: [],
    voided_deadlines: [],
    void_deadline_errors: [],
  };

  const status = await apiMaybe(token, "GET", "/v1/stopwatch/status");
  if (status.response.ok && status.body?.active) {
    const stopped = await apiMaybe(
      token,
      "POST",
      "/v1/stopwatch/stop?confirmed=true",
      {
        post_task_reflection: 3,
        task_completion_percentage: 0,
        scope_outcome: "reduced",
      },
      { "X-Idempotency-Key": `${runId}-cleanup-stop` },
    );
    cleanup.stopped_active_timer = stopped.response.ok;
  }

  for (const taskId of [...created.taskIds].reverse()) {
    const result = await apiMaybe(
      token,
      "POST",
      `/v1/tasks/${taskId}/void`,
      {
        voided_reason: "test_contamination",
        void_reason_detail: `Mutable Holmesberg browser smoke cleanup ${runId}`,
      },
    );
    if (result.response.ok) {
      cleanup.voided_tasks.push(taskId);
    } else {
      cleanup.void_task_errors.push({
        task_id: taskId,
        status: result.response.status,
        body: result.body,
      });
    }
  }

  for (const deadlineId of [...created.deadlineIds].reverse()) {
    const result = await apiMaybe(token, "DELETE", `/v1/deadlines/${deadlineId}`);
    if (result.response.status === 204) {
      cleanup.voided_deadlines.push(deadlineId);
    } else {
      cleanup.void_deadline_errors.push({
        deadline_id: deadlineId,
        status: result.response.status,
        body: result.body,
      });
    }
  }

  return cleanup;
}

async function screenshotRuntimeSurfaces(page, issues) {
  const routes = [
    ["/pulse", "pulse"],
    ["/today", "today"],
    ["/calendar", "calendar"],
    ["/deadlines", "deadlines"],
    ["/table", "table"],
    ["/insights", "insights"],
    ["/settings", "settings"],
  ];

  for (const [route, name] of routes) {
    await page.goto(`${frontendOrigin}${route}`, {
      waitUntil: "domcontentloaded",
      timeout: 45_000,
    });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    const text = await page.locator("body").innerText({ timeout: 10_000 });
    if (!text.trim()) {
      issues.push(`${route} rendered empty body`);
    }
    if (text.includes("[object Object]")) {
      issues.push(`${route} rendered [object Object]`);
    }
    if (/internal server error/i.test(text)) {
      issues.push(`${route} rendered internal server error text`);
    }
    await page.screenshot({
      path: path.join(outDir, `${name}.png`),
      fullPage: true,
    });
  }
}

async function main() {
  if (!cookieHeader.trim()) {
    fail("LYRA_COOKIE_HOLMESBERG is missing");
  }

  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const created = { taskIds: [], deadlineIds: [] };
  const evidence = {
    run_id: runId,
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
    created,
    checks: [],
    issues: [],
    cleanup: null,
  };

  try {
    const cookies = parseAndExpandCookies(cookieHeader, frontendOrigin);
    if (!cookies.length) {
      fail("no Holmesberg cookie pairs parsed");
    }
    await context.addCookies(cookies);

    const page = await context.newPage();
    const failedResponses = [];
    const consoleErrors = [];
    page.on("response", (response) => {
      if (response.status() >= 500) {
        failedResponses.push({ url: response.url(), status: response.status() });
      }
    });
    page.on("console", (message) => {
      if (message.type() === "error") {
        const text = message.text();
        if (!text.includes("static.cloudflareinsights.com")) {
          consoleErrors.push(text.slice(0, 300));
        }
      }
    });

    await page.goto(`${frontendOrigin}/pulse`, {
      waitUntil: "domcontentloaded",
      timeout: 45_000,
    });
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    const token = await resolveBackendToken(page);
    const me = await apiJson(token, "GET", "/v1/users/me");
    if (me.is_operator) {
      fail("Holmesberg cookie resolved as operator; mutable smoke refused", {
        user_ref: userRef(me.user_id),
      });
    }
    evidence.user_ref = userRef(me.user_id);
    evidence.checks.push("non_operator_identity_confirmed");

    const operatorGate = await apiMaybe(token, "GET", "/v1/operator/dashboard");
    if (operatorGate.response.status !== 403) {
      fail("Holmesberg account can access operator dashboard", {
        status: operatorGate.response.status,
        body: operatorGate.body,
      });
    }
    evidence.checks.push("operator_route_forbidden");

    const start = futureIso(20);
    const end = futureIso(35);
    const secondStart = futureIso(25);
    const secondEnd = futureIso(40);

    const deadline = await apiJson(token, "POST", "/v1/deadlines", {
      title: `${titlePrefix} deadline`,
      description: "Synthetic mutable browser smoke deadline.",
      due_at_utc: futureIso(180),
      category_hint: "s1c-chaos",
      force_duplicate: true,
    });
    created.deadlineIds.push(deadline.deadline_id);
    evidence.checks.push("deadline_create");

    const task = await apiJson(
      token,
      "POST",
      "/v1/create",
      {
        title: `${titlePrefix} timer task`,
        start,
        end,
        category: "s1c-chaos",
        description: "Synthetic mutable browser smoke timer task.",
        force: true,
        deadline_id: deadline.deadline_id,
      },
      { "X-Idempotency-Key": `${runId}-create-timer-task` },
    );
    if (!task.created || !task.task_id) {
      fail("timer task create returned non-created response", task);
    }
    created.taskIds.push(task.task_id);
    evidence.checks.push("task_create_bound_to_deadline");

    const secondTask = await apiJson(
      token,
      "POST",
      "/v1/create",
      {
        title: `${titlePrefix} second timer guard`,
        start: secondStart,
        end: secondEnd,
        category: "s1c-chaos",
        description: "Synthetic mutable browser smoke parallel-timer guard.",
        force: true,
      },
      { "X-Idempotency-Key": `${runId}-create-second-task` },
    );
    if (!secondTask.created || !secondTask.task_id) {
      fail("second task create returned non-created response", secondTask);
    }
    created.taskIds.push(secondTask.task_id);
    evidence.checks.push("second_task_create");

    const startTimer = await apiJson(
      token,
      "POST",
      "/v1/stopwatch/start",
      {
        task_id: task.task_id,
        pre_task_readiness: 3,
        interruption_type: null,
      },
      { "X-Idempotency-Key": `${runId}-start` },
    );
    if (startTimer.task_id !== task.task_id) {
      fail("stopwatch started unexpected task", startTimer);
    }
    evidence.checks.push("stopwatch_start");

    const blockedSecondStart = await apiMaybe(
      token,
      "POST",
      "/v1/stopwatch/start",
      {
        task_id: secondTask.task_id,
        pre_task_readiness: 3,
        interruption_type: null,
      },
      { "X-Idempotency-Key": `${runId}-blocked-start` },
    );
    if (blockedSecondStart.response.status !== 400) {
      fail("parallel active timer was not rejected", {
        status: blockedSecondStart.response.status,
        body: blockedSecondStart.body,
      });
    }
    evidence.checks.push("parallel_active_timer_rejected");

    await apiJson(
      token,
      "POST",
      "/v1/stopwatch/pause",
      {
        pause_reason: "intentional_break",
        pause_initiator: "self",
      },
      { "X-Idempotency-Key": `${runId}-pause` },
    );
    const pausedStatus = await apiJson(token, "GET", "/v1/stopwatch/status");
    if (!pausedStatus.active || !pausedStatus.paused) {
      fail("stopwatch status did not show active paused timer", pausedStatus);
    }
    evidence.checks.push("stopwatch_pause_status");

    await apiJson(
      token,
      "POST",
      "/v1/stopwatch/resume",
      undefined,
      { "X-Idempotency-Key": `${runId}-resume` },
    );
    const resumedStatus = await apiJson(token, "GET", "/v1/stopwatch/status");
    if (!resumedStatus.active || resumedStatus.paused) {
      fail("stopwatch status did not show active resumed timer", resumedStatus);
    }
    evidence.checks.push("stopwatch_resume_status");

    await apiJson(token, "POST", "/v1/stopwatch/update-completion", {
      task_completion_percentage: 60,
    });
    evidence.checks.push("stopwatch_update_completion");

    const stopped = await apiJson(
      token,
      "POST",
      "/v1/stopwatch/stop?confirmed=true",
      {
        post_task_reflection: 3,
        task_completion_percentage: 70,
        scope_outcome: "stuck_to_plan",
      },
      { "X-Idempotency-Key": `${runId}-stop` },
    );
    if (stopped.task_id !== task.task_id) {
      fail("stopwatch stopped unexpected task", stopped);
    }
    evidence.checks.push("stopwatch_stop_clean");

    const parse = await apiJson(token, "POST", "/v1/brain-dump/parse", {
      raw_text: [
        `${titlePrefix} brain task tomorrow 11am 20min`,
        `${titlePrefix} brain deadline tomorrow 7pm`,
      ].join("\n"),
      current_local_iso: localIso(0),
    });
    if (!Array.isArray(parse.items) || parse.items.length < 2) {
      fail("brain dump parse did not produce expected preview items", parse);
    }
    evidence.checks.push("brain_dump_parse");

    const commit = await apiJson(
      token,
      "POST",
      "/v1/brain-dump/commit",
      {
        items: parse.items,
        bindings: parse.bindings || [],
      },
      { "X-Idempotency-Key": `${runId}-brain-commit` },
    );
    for (const taskId of commit.task_ids || []) created.taskIds.push(taskId);
    for (const deadlineId of commit.deadline_ids || []) created.deadlineIds.push(deadlineId);
    if ((commit.tasks_created || 0) < 1) {
      fail("brain dump commit did not create a task", commit);
    }
    evidence.checks.push("brain_dump_commit");

    await screenshotRuntimeSurfaces(page, evidence.issues);

    if (failedResponses.length) {
      evidence.issues.push(`server errors: ${JSON.stringify(failedResponses)}`);
    }
    if (consoleErrors.length) {
      evidence.issues.push(`console errors: ${JSON.stringify(consoleErrors)}`);
    }

    evidence.cleanup = await cleanupArtifacts(token, created);
    if (evidence.cleanup.void_task_errors.length || evidence.cleanup.void_deadline_errors.length) {
      fail("cleanup had errors", evidence.cleanup);
    }
    evidence.checks.push("synthetic_artifacts_cleaned");

    if (evidence.issues.length) {
      fail("browser mutable smoke found runtime issues", evidence.issues);
    }

    await writeFile(
      path.join(outDir, "result.json"),
      JSON.stringify({ ok: true, ...evidence }, null, 2),
    );
    console.log(JSON.stringify({ ok: true, outDir, ...evidence }, null, 2));
  } catch (error) {
    try {
      const page = context.pages()[0];
      if (page && !page.isClosed()) {
        await page.screenshot({
          path: path.join(outDir, "failure.png"),
          fullPage: true,
        });
      }
    } catch {
      // Best-effort failure screenshot only.
    }
    const token = context.pages()[0] && !context.pages()[0].isClosed()
      ? await resolveBackendToken(context.pages()[0]).catch(() => null)
      : null;
    if (token) {
      evidence.cleanup = await cleanupArtifacts(token, created).catch((cleanupError) => ({
        cleanup_error: cleanupError.message,
        detail: cleanupError.detail ?? null,
      }));
    }
    await writeFile(
      path.join(outDir, "result.json"),
      JSON.stringify({
        ok: false,
        error: error.message,
        detail: error.detail ?? null,
        ...evidence,
      }, null, 2),
    );
    console.error(JSON.stringify({
      ok: false,
      error: error.message,
      detail: error.detail ?? null,
      outDir,
    }, null, 2));
    process.exitCode = 1;
  } finally {
    await context.close();
    await browser.close();
  }
}

await main();
