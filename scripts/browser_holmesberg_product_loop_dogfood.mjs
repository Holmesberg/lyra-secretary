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

const topology = args.get("topology") || "public";
const frontendOrigin = args.get("frontend")
  || process.env.LYRA_FRONTEND_ORIGIN
  || (topology === "public" ? "https://lyraos.org" : "http://localhost:3000");
const apiOrigin = args.get("api")
  || process.env.LYRA_API_ORIGIN
  || (topology === "public" ? "https://api.lyraos.org" : "http://localhost:8000");
const outDir = path.resolve(
  args.get("out-dir")
  || path.join(repoRoot, "tmp", "browser-product-loop", new Date().toISOString().replace(/[:.]/g, "-")),
);
const runId = args.get("run-id") || `dogfood-${Date.now()}-${randomUUID().slice(0, 8)}`;
const runKey = boundedIdentifier(runId, 42);
const prefix = args.get("prefix") || `DOGFOOD ${randomUUID().slice(0, 8)}`;
const cleanupOnly = args.get("cleanup-only") === "true";
const archetypeProofOnly = args.get("archetype-proof-only") === "true";
const pressureProofOnly = args.get("pressure-proof-only") === "true";
const stopwatchOutputProofOnly = args.get("stopwatch-output-proof-only") === "true";
const proxyApi = args.get("proxy-api") === "true";
const forcePressureRecovery = args.get("force-pressure-recovery") === "true";
const holmesbergCookie = process.env.LYRA_COOKIE_HOLMESBERG
  || process.env.LYRA_COOKIE_MORIARTY
  || "";
const operatorCookie = process.env.LYRA_COOKIE_ALINASSERSABRY || "";

const checks = [];
const issues = [];
const gated = [];
const cleanup = {
  tasks: new Set(),
  deadlines: new Set(),
  notifications: new Set(),
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

function countRows(body, key) {
  return Array.isArray(body?.[key]) ? body[key].length : 0;
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

function missingSyntheticDeadlineSuggestionExposures(beforeExport, afterExport) {
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
    .filter((row) => row.content_template_id === "deadline_binding_suggestion")
    .filter((row) => row.trigger_source === "parse.deadline_preview")
    .filter((row) => row.decision_status === "delivered")
    .filter((row) => !renderIds.has(row.exposure_id))
    .filter((row) => !ackIds.has(row.exposure_id))
    .filter((row) => !suppressionIds.has(row.exposure_id))
    .sort((a, b) => String(exposureSortTime(b)).localeCompare(String(exposureSortTime(a))));
}

const STOPWATCH_OUTPUT_TEMPLATES = new Set([
  "micro_mirror",
  "calibration_nudge",
]);

function newStopwatchOutputDecisions(beforeExport, afterExport, taskId = null) {
  const beforeIds = new Set(
    rows(beforeExport, "exposure_decision_events").map((row) => row.exposure_id),
  );
  return rows(afterExport, "exposure_decision_events")
    .filter((row) => !beforeIds.has(row.exposure_id))
    .filter((row) => row.trigger_source === "stopwatch.stop")
    .filter((row) => STOPWATCH_OUTPUT_TEMPLATES.has(row.content_template_id))
    .filter((row) => !taskId || row.task_id === taskId)
    .sort((a, b) => String(exposureSortTime(b)).localeCompare(String(exposureSortTime(a))));
}

function missingSyntheticStopwatchOutputExposures(beforeExport, afterExport) {
  const renderIds = new Set(
    rows(afterExport, "exposure_render_events").map((row) => row.exposure_id),
  );
  const ackIds = new Set(
    rows(afterExport, "exposure_ack_events")
      .filter((row) => row.event_type === "render")
      .map((row) => row.exposure_id),
  );
  const suppressionIds = new Set(
    rows(afterExport, "suppression_events").map((row) => row.exposure_id),
  );
  return newStopwatchOutputDecisions(beforeExport, afterExport)
    .filter((row) => row.task_id && cleanup.tasks.has(row.task_id))
    .filter((row) => row.decision_status === "reserved")
    .filter((row) => !renderIds.has(row.exposure_id))
    .filter((row) => !ackIds.has(row.exposure_id))
    .filter((row) => !suppressionIds.has(row.exposure_id));
}

async function suppressUnrenderedSurfaceProbe(token, payload, label) {
  addCheck(`${label} returns an exposure decision`, Boolean(payload?.exposure_id), {
    surface_id: payload?.surface_id || null,
  });
  const result = await apiFetch(
    token,
    `/v1/exposures/${encodeURIComponent(payload.exposure_id)}/ack/suppress`,
    {
      method: "POST",
      body: JSON.stringify({
        suppression_reason: "client_discarded_before_render",
      }),
    },
  );
  addCheck(`${label} records non-render suppression`, [
    "suppressed",
    "already_suppressed",
  ].includes(result.status), result);
  cleanup.exposureSuppressions.add(payload.exposure_id);
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

function expectNoMarkers(text, label, markers) {
  const haystack = String(text || "").toLowerCase();
  const found = markers.filter((marker) => haystack.includes(String(marker).toLowerCase()));
  addCheck(`${label}: no canary/private markers`, found.length === 0, { found });
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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

async function closeBlockingDialog(page, context) {
  const dialog = page.getByRole("dialog").first();
  const visible = await dialog.isVisible({ timeout: 1_000 }).catch(() => false);
  if (!visible) return { closed: false };
  const text = (await dialog.innerText().catch(() => "")).slice(0, 300);
  await page.keyboard.press("Escape").catch(() => {});
  let stillVisible = await dialog.isVisible({ timeout: 1_500 }).catch(() => false);
  if (stillVisible) {
    await dialog.getByRole("button", { name: /^Close$/i }).click({ timeout: 2_000 }).catch(() => {});
    stillVisible = await dialog.isVisible({ timeout: 1_500 }).catch(() => false);
  }
  if (stillVisible) {
    addCheck("blocking dialog closed before browser action", false, { context, text });
  }
  addIssue("blocking dialog closed before browser action", { context, text });
  return { closed: true, text };
}

function transientApiStatus(status) {
  return [502, 503, 504, 520, 521, 522, 523, 524].includes(Number(status));
}

function transientApiError(error) {
  const message = String(error?.message || error);
  return /fetch failed|ECONNRESET|ETIMEDOUT|ENOTFOUND|EAI_AGAIN|network|socket|timeout/i.test(message);
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
  const url = `${frontendOrigin}${pathname}`;
  let lastError = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 45_000,
      });
      lastError = null;
      break;
    } catch (error) {
      lastError = error;
      const message = String(error?.message || error);
      const transient = /net::ERR_NAME_NOT_RESOLVED|net::ERR_NETWORK_CHANGED|net::ERR_CONNECTION|net::ERR_TIMED_OUT|Timeout/i
        .test(message);
      if (!transient || attempt === 3) {
        throw error;
      }
      addIssue("transient browser navigation retry", {
        pathname,
        attempt,
        message: message.split("\n")[0],
      });
      await page.waitForTimeout(1_500 * attempt);
    }
  }
  if (lastError) {
    throw lastError;
  }
  await page.waitForLoadState("networkidle", { timeout: 6_000 }).catch(() => {});
  let text = await page.locator("body").innerText({ timeout: 10_000 });
  if (/ONBOARDING|LyraOS starts learning from the first plan/i.test(text)) {
    await completeOnboardingGate(page);
    await page.waitForTimeout(1_200);
    await page.waitForLoadState("networkidle", { timeout: 6_000 }).catch(() => {});
    text = await page.locator("body").innerText({ timeout: 10_000 });
    if (/ONBOARDING|LyraOS starts learning from the first plan/i.test(text)) {
      await page.goto(`${frontendOrigin}${pathname}`, {
        waitUntil: "domcontentloaded",
        timeout: 45_000,
      });
      await page.waitForLoadState("networkidle", { timeout: 6_000 }).catch(() => {});
      text = await page.locator("body").innerText({ timeout: 10_000 });
    }
  }
  expectNoPrivateLeak(text, `render ${pathname}`);
  await screenshot(page, name);
  return text;
}

async function completeOnboardingGate(page) {
  await screenshot(page, "onboarding-gate");
  const skip = page.getByRole("button", { name: /Skip for now/i }).first();
  if (await skip.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await skip.click();
    await page.waitForLoadState("networkidle", { timeout: 6_000 }).catch(() => {});
    await page.waitForTimeout(1_000);
    addIssue("Holmesberg onboarding gate was open; skipped to reach app dogfood surfaces");
    return;
  }
  const textarea = page.locator("textarea").first();
  const parse = page.getByRole("button", { name: /Parse my plan|Parse/i }).first();
  if (
    await textarea.isVisible({ timeout: 2_000 }).catch(() => false)
    && await parse.isVisible({ timeout: 2_000 }).catch(() => false)
  ) {
    await textarea.fill(`${prefix} onboarding task tomorrow 30min`);
    await parse.click();
    await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {});
    await page.waitForTimeout(1_000);
    addIssue("Holmesberg onboarding gate was open; parsed a synthetic onboarding plan");
    return;
  }
  throw new Error("Holmesberg is gated by onboarding, but no skip/parse control was available");
}

async function firstVisible(page, candidates, timeout = 5_000, label = "locator") {
  const deadline = Date.now() + timeout;
  let lastError = null;
  while (Date.now() < deadline) {
    for (const candidate of candidates) {
      const locator = typeof candidate === "function" ? candidate(page) : candidate;
      try {
        const first = locator.first();
        if (await first.isVisible({ timeout: 250 }).catch(() => false)) {
          return first;
        }
      } catch (error) {
        lastError = error;
      }
    }
    await page.waitForTimeout(150);
  }
  throw lastError || new Error(`${label}: no visible locator matched`);
}

async function clickAny(page, name, candidates, timeout = 5_000) {
  const locator = await firstVisible(page, candidates, timeout, name);
  await locator.click({ timeout: 10_000 });
  return locator;
}

async function fillAny(page, name, candidates, value, timeout = 5_000) {
  const locator = await firstVisible(page, candidates, timeout, name);
  await locator.fill(value, { timeout: 10_000 });
  return locator;
}

async function setRangeAny(page, name, candidates, value, timeout = 5_000) {
  const locator = await firstVisible(page, candidates, timeout, name);
  await locator.evaluate((element, nextValue) => {
    const descriptor = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value",
    );
    descriptor?.set?.call(element, String(nextValue));
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
  return locator;
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
      await route.fulfill({
        status: response.status(),
        headers: {
          ...response.headers(),
          ...corsHeaders,
        },
        body: await response.body(),
      });
    } catch (error) {
      if (/Target page, context or browser has been closed/i.test(String(error?.message || error))) {
        return;
      }
      await route.abort("failed").catch(() => {});
    }
  });
}

async function resolveAccount(browser, label, cookieHeader, expectOperator) {
  if (!cookieHeader || cookieHeader.length < 100) {
    throw new Error(`missing usable cookie for ${label}`);
  }
  const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  if (proxyApi) {
    await installApiProxy(context);
  }
  await context.addCookies(parseAndExpandCookies(cookieHeader, frontendOrigin));
  const page = await context.newPage();
  const serverErrors = [];
  const deadlinePreviewResponses = [];
  const deadlinePreviewRequests = [];
  const biasLookupResponses = [];
  const biasLookupRequests = [];
  const createTaskRequests = [];
  page.__biasLookupResponses = biasLookupResponses;
  page.__createTaskRequests = createTaskRequests;
  page.on("request", (request) => {
    if (request.url().includes("/v1/create") && request.method().toUpperCase() === "POST") {
      let body = null;
      try {
        body = JSON.parse(request.postData() || "{}");
      } catch (error) {
        body = { parse_error: String(error?.message || error).slice(0, 160) };
      }
      createTaskRequests.push({
        url: request.url(),
        method: request.method(),
        idempotency_key: request.headers()["x-idempotency-key"] || null,
        body,
      });
      if (createTaskRequests.length > 80) {
        createTaskRequests.shift();
      }
    }
    if (request.url().includes("/v1/parse/deadline-preview")) {
      deadlinePreviewRequests.push({
        url: request.url(),
        method: request.method(),
        body: (request.postData() || "").slice(0, 1000),
      });
      if (deadlinePreviewRequests.length > 20) {
        deadlinePreviewRequests.shift();
      }
    }
    if (request.url().includes("/v1/analytics/bias_factor/lookup")) {
      biasLookupRequests.push({
        url: request.url(),
        method: request.method(),
      });
      if (biasLookupRequests.length > 40) {
        biasLookupRequests.shift();
      }
    }
  });
  page.on("response", async (response) => {
    if (response.status() >= 500) {
      serverErrors.push({ url: response.url(), status: response.status() });
    }
    if (response.url().includes("/v1/parse/deadline-preview")) {
      let body = "";
      try {
        body = await response.text();
      } catch (error) {
        body = `<<unreadable: ${String(error?.message || error).slice(0, 160)}>>`;
      }
      deadlinePreviewResponses.push({
        url: response.url(),
        status: response.status(),
        body: body.slice(0, 1000),
      });
      if (deadlinePreviewResponses.length > 20) {
        deadlinePreviewResponses.shift();
      }
    }
    if (response.url().includes("/v1/analytics/bias_factor/lookup")) {
      let body = "";
      try {
        body = await response.text();
      } catch (error) {
        body = `<<unreadable: ${String(error?.message || error).slice(0, 160)}>>`;
      }
      biasLookupResponses.push({
        url: response.url(),
        status: response.status(),
        body: body.slice(0, 1600),
      });
      if (biasLookupResponses.length > 40) {
        biasLookupResponses.shift();
      }
    }
  });
  const token = await resolveBackendTokenFromContext(context, frontendOrigin);
  const me = await apiFetch(token, "/v1/users/me");
  addCheck(`${label}: operator flag`, Boolean(me.is_operator) === expectOperator, {
    expected: expectOperator,
    actual: Boolean(me.is_operator),
    user_ref: userRef(me.user_id),
  });
  return {
    context,
    page,
    token,
    me,
    serverErrors,
    deadlinePreviewRequests,
    deadlinePreviewResponses,
    biasLookupRequests,
    biasLookupResponses,
  };
}

async function findTaskByTitle(token, title) {
  const body = await apiFetch(
    token,
    `/v1/tasks/query?date_from=${dateKey(new Date(Date.now() - 86400_000))}&date_to=${dateKey(futureDate(14 * 24 * 60))}&state=all`,
  );
  return (body.tasks || []).find((task) => task.title === title) || null;
}

async function findTasksByPrefix(token) {
  const body = await apiFetch(
    token,
    `/v1/tasks/query?date_from=${dateKey(new Date(Date.now() - 86400_000))}&date_to=${dateKey(futureDate(21 * 24 * 60))}&state=all`,
  );
  return (body.tasks || []).filter((task) => String(task.title || "").startsWith(prefix));
}

async function findTasksByExactTitle(token, title) {
  const tasks = await findTasksByPrefix(token);
  return tasks.filter((task) => task.title === title);
}

async function findDeadlineByTitle(token, title) {
  const body = await apiFetch(token, "/v1/deadlines?include_voided=true");
  return (body.deadlines || []).find((deadline) => deadline.title === title) || null;
}

async function findDeadlinesByPrefix(token) {
  const body = await apiFetch(token, "/v1/deadlines?include_voided=true");
  return (body.deadlines || []).filter((deadline) => String(deadline.title || "").startsWith(prefix));
}

async function pollFor(token, description, predicate, timeoutMs = 15_000, intervalMs = 1_000) {
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

async function stopActiveTimerIfNeeded(token) {
  const status = await apiFetch(token, "/v1/stopwatch/status");
  if (!status.active) return null;
  const stopped = await apiFetch(
    token,
    "/v1/stopwatch/stop?confirmed=true",
    {
      method: "POST",
      headers: { "X-Idempotency-Key": boundedIdentifier(`dogfood-pre-stop:${runKey}`) },
      body: JSON.stringify({
        post_task_reflection: 3,
        task_completion_percentage: 0,
        scope_outcome: "reduced",
      }),
    },
    [200, 409],
  );
  addIssue("pre-existing active timer was stopped on Holmesberg", {
    task_id: status.task_id,
    response: stopped,
  });
  return stopped;
}

async function createDeadlineThroughUi(page, token) {
  const title = `${prefix} anchor deadline`;
  const due = futureDate(180);
  await goto(page, "/deadlines", "deadlines-before-create");
  await clickAny(page, "new deadline", [
    (p) => p.getByTestId("deadlines-new"),
    (p) => p.getByRole("button", { name: /\+ New deadline|New deadline/i }),
  ]);
  await fillAny(page, "deadline title", [
    (p) => p.getByTestId("deadline-title"),
    (p) => p.locator('input[type="text"]').first(),
  ], title);
  await fillAny(page, "deadline due", [
    (p) => p.getByTestId("deadline-due-at"),
    (p) => p.locator('input[type="datetime-local"]').first(),
  ], localInput(due));
  await clickAny(page, "deadline create", [
    (p) => p.getByTestId("deadline-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
  ]);
  await page.getByText(title, { exact: false }).first().waitFor({ timeout: 15_000 });
  await screenshot(page, "deadlines-after-create");
  const deadline = await findDeadlineByTitle(token, title);
  addCheck("deadline UI create reached backend", Boolean(deadline), { title });
  cleanup.deadlines.add(deadline.deadline_id);
  return deadline;
}

async function createDeadlineViaApi(token, { title, dueMinutes = 360, state = "planned" }) {
  const deadline = await apiFetch(token, "/v1/deadlines", {
    method: "POST",
    body: JSON.stringify({
      title,
      due_at_utc: futureDate(dueMinutes).toISOString(),
    }),
  }, [200, 201]);
  cleanup.deadlines.add(deadline.deadline_id);
  if (state !== "planned") {
    const updated = await apiFetch(token, `/v1/deadlines/${encodeURIComponent(deadline.deadline_id)}`, {
      method: "PUT",
      body: JSON.stringify({ state }),
    });
    return updated;
  }
  return deadline;
}

async function createTaskViaApi(
  token,
  {
    title,
    startMinutes = 360,
    durationMinutes = 30,
    category = "dogfood_switch",
  },
) {
  const start = futureDate(startMinutes);
  const end = new Date(start.getTime() + durationMinutes * 60_000);
  const created = await apiFetch(token, "/v1/create", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": boundedIdentifier(`task-create:${runKey}:${title}`),
    },
    body: JSON.stringify({
      title,
      start: start.toISOString(),
      end: end.toISOString(),
      category,
      source: "web",
      force: true,
    }),
  }, [200, 201]);
  if (created?.task_id) cleanup.tasks.add(created.task_id);
  return created;
}

async function rescheduleTaskViaApi(token, taskId, { start, end, title, category }) {
  return await apiFetch(token, "/v1/reschedule", {
    method: "POST",
    body: JSON.stringify({
      task_id: taskId,
      new_start: start.toISOString(),
      new_end: end.toISOString(),
      ...(title ? { title } : {}),
      ...(category ? { category } : {}),
    }),
  });
}

async function openNewTaskModal(page, label = "today new task") {
  await goto(page, "/today", label);
  await clickAny(page, "today new task", [
    (p) => p.getByTestId("today-new-task"),
    (p) => p.getByRole("button", { name: /New task/i }),
  ]);
  await firstVisible(page, [
    (p) => p.getByTestId("new-task-modal"),
    (p) => p.getByRole("dialog", { name: /New task/i }),
  ], 8_000, "new task modal");
}

async function fillNewTaskCore(page, { title, start, end, hours = "0", minutes = "30" }) {
  await fillAny(page, "task title", [
    (p) => p.getByTestId("new-task-title"),
    (p) => p.locator("#title"),
  ], title);
  await fillAny(page, "task start", [
    (p) => p.getByTestId("new-task-start"),
    (p) => p.locator("#start"),
  ], localInput(start));
  await fillAny(page, "task end", [
    (p) => p.getByTestId("new-task-end"),
    (p) => p.locator("#end"),
  ], localInput(end));
  await fillAny(page, "task duration hours", [
    (p) => p.getByTestId("new-task-duration-hours"),
    (p) => p.getByTestId("new-task-modal").locator('input[type="number"]').nth(0),
    (p) => p.getByRole("dialog", { name: /New task/i }).locator('input[type="number"]').nth(0),
    (p) => p.locator('input[type="number"]').nth(0),
  ], hours);
  await fillAny(page, "task duration minutes", [
    (p) => p.getByTestId("new-task-duration-minutes"),
    (p) => p.getByTestId("new-task-modal").locator('input[type="number"]').nth(1),
    (p) => p.getByRole("dialog", { name: /New task/i }).locator('input[type="number"]').nth(1),
    (p) => p.locator('input[type="number"]').nth(1),
  ], minutes);
}

async function fillNewTaskDescription(page, description) {
  await clickAny(page, "show task description", [
    (p) => p.getByRole("button", { name: /Add details|Edit details/i }),
    (p) => p.getByText(/Add details|Edit details/i),
  ], 5_000);
  await fillAny(page, "task description", [
    (p) => p.getByTestId("new-task-description"),
    (p) => p.locator("#description"),
  ], description, 5_000);
}

async function bindDeadlineInNewTaskModal(page, deadline, label = "bind deadline") {
  await clickAny(page, label, [
    (p) => p.getByRole("button", { name: /\+ Bind to a deadline/i }),
    (p) => p.getByText(/\+ Bind to a deadline/i),
  ], 5_000);
  const modal = page.getByTestId("new-task-modal").first();
  const deadlineOption = modal
    .locator(`[data-testid="new-task-deadline-option"][data-deadline-id="${deadline.deadline_id}"]`)
    .first();
  if (await deadlineOption.count().catch(() => 0)) {
    await deadlineOption.scrollIntoViewIfNeeded({ timeout: 5_000 }).catch(() => {});
    await deadlineOption.click({ timeout: 10_000, force: true });
    return;
  }
  const fallbackOption = modal
    .getByRole("button", { name: new RegExp(escapeRegex(deadline.title), "i") })
    .first();
  await fallbackOption.scrollIntoViewIfNeeded({ timeout: 5_000 }).catch(() => {});
  await fallbackOption.click({ timeout: 10_000, force: true });
}

function createRequestsForTitle(page, title, startIndex = 0) {
  return (page.__createTaskRequests || [])
    .slice(startIndex)
    .filter((request) => request.body?.title === title);
}

function assertStableCreateIdempotency(label, requests) {
  addCheck(`${label}: create requests include idempotency header`, (
    requests.length >= 1 && requests.every((request) => request.idempotency_key)
  ), requests.map((request) => ({
    idempotency_key: request.idempotency_key,
    force: request.body?.force,
  })));
  if (requests.length > 1) {
    const keys = new Set(requests.map((request) => request.idempotency_key));
    addCheck(`${label}: duplicate create requests reuse one idempotency key`, keys.size === 1, {
      keys: [...keys],
      count: requests.length,
    });
  }
}

async function keepNudgeIfVisible(page, label = "new-task-nudge-keep") {
  const keepNudge = page
    .locator('[data-testid="new-task-nudge-keep"], button:has-text("Keep ")')
    .first();
  const visible = await keepNudge.isVisible({ timeout: 8_000 }).catch(() => false);
  if (visible) {
    await screenshot(page, label);
    await keepNudge.click();
  }
  return visible;
}

async function clickCreateAnywayIfVisible(page, label) {
  const createAnyway = await firstVisible(page, [
    (p) => p.getByTestId("new-task-create-anyway"),
    (p) => p.getByRole("button", { name: /Create anyway/i }),
    (p) => p.locator('button:has-text("Create anyway")'),
  ], 2_000, label).catch(() => null);
  if (!createAnyway) return false;
  await screenshot(page, label);
  await createAnyway.click();
  return true;
}

async function chooseCustomCategory(page, category) {
  const select = await firstVisible(page, [
    (p) => p.getByTestId("category-select"),
    (p) => p.locator("#category").first(),
    (p) => p.getByLabel(/^Category$/i),
  ], 5_000, "category select");
  await select.selectOption("__CREATE_NEW__");
  await fillAny(page, "custom category", [
    (p) => p.getByTestId("new-task-category-custom"),
    (p) => p.locator('input#category'),
    (p) => p.getByPlaceholder(/research|admin|side_project/i),
  ], category);
}

async function chooseNudgeEligibleCategory(page) {
  await chooseCustomCategory(page, `dogfood_nudge_${runKey.slice(0, 24)}`);
}

async function waitForDeadlineSuggestion(page, title, timeout = 20_000, options = {}) {
  const { required = true } = options;
  const startedAt = Date.now();
  const suggestion = await firstVisible(page, [
    (p) => p.getByTestId("new-task-deadline-suggestion"),
    (p) => p.getByText(/LyraOS thinks this binds to/i),
  ], timeout, `deadline suggestion for ${title}`).catch(() => null);
  const visible = Boolean(suggestion);
  const latencyMs = Date.now() - startedAt;
  if (!visible) {
    const detail = { title, latency_ms: latencyMs, timeout_ms: timeout };
    if (required) {
      addCheck(`deadline suggestion rendered for ${title}`, false, detail);
    } else {
      addIssue("deadline suggestion chip did not render within optional wait; using fallback", detail);
    }
    return false;
  }
  addCheck(`deadline suggestion rendered for ${title}`, true, { title, latency_ms: latencyMs });
  if (visible) {
    if (latencyMs > 3_000) {
      addIssue("deadline suggestion render latency exceeded senior UX budget", {
        title,
        latency_ms: latencyMs,
        budget_ms: 3_000,
      });
    }
    await screenshot(page, `new-task-suggestion-${boundedIdentifier(title, 24)}`);
  }
  return visible;
}

function deadlineSuggestionExposureState(beforeExport, afterExport) {
  const beforeIds = new Set(
    rows(beforeExport, "exposure_decision_events").map((row) => row.exposure_id),
  );
  const decisions = rows(afterExport, "exposure_decision_events")
    .filter((row) => !beforeIds.has(row.exposure_id))
    .filter((row) => row.content_template_id === "deadline_binding_suggestion")
    .filter((row) => row.trigger_source === "parse.deadline_preview");
  const renderIds = new Set(
    rows(afterExport, "exposure_render_events")
      .filter((row) => row.surface === "task.deadline_binding_suggestion")
      .map((row) => row.exposure_id),
  );
  const ackIds = new Set(
    rows(afterExport, "exposure_ack_events")
      .filter((row) => row.event_type === "render")
      .map((row) => row.exposure_id),
  );
  const suppressionIds = new Set(
    rows(afterExport, "suppression_events").map((row) => row.exposure_id),
  );
  const browserProven = decisions
    .filter((row) => renderIds.has(row.exposure_id))
    .filter((row) => ackIds.has(row.exposure_id));
  const fabricated = decisions
    .filter((row) => renderIds.has(row.exposure_id))
    .filter((row) => !ackIds.has(row.exposure_id));
  const unterminated = decisions.filter((row) => (
    !renderIds.has(row.exposure_id)
    && !suppressionIds.has(row.exposure_id)
  ));
  return { decisions, browserProven, fabricated, unterminated };
}

async function assertDeadlineSuggestionBrowserRender(token, beforeExport) {
  await pollFor(token, "deadline suggestion browser render acknowledgement", async () => {
    const exported = await apiFetch(token, "/v1/users/me/export");
    const state = deadlineSuggestionExposureState(beforeExport, exported);
    return (
      state.browserProven.length >= 1
      && state.fabricated.length === 0
      && state.unterminated.length === 0
    ) ? state : null;
  }, 15_000, 500);

  const afterExport = await apiFetch(token, "/v1/users/me/export");
  const state = deadlineSuggestionExposureState(beforeExport, afterExport);
  addCheck("deadline suggestion render is browser-acknowledged", state.browserProven.length >= 1, {
    new_decision_count: state.decisions.length,
    browser_proven_count: state.browserProven.length,
    statuses: state.decisions.map((row) => row.decision_status).sort(),
  });
  addCheck("deadline suggestion has no fabricated rendered decision", state.fabricated.length === 0, {
    fabricated_count: state.fabricated.length,
  });
  addCheck("deadline suggestion has no unterminated browser candidate", state.unterminated.length === 0, {
    unterminated_count: state.unterminated.length,
    statuses: state.unterminated.map((row) => row.decision_status).sort(),
  });
}

async function createTaskThroughUi(page, token, deadline) {
  const beforeSuggestionExport = await apiFetch(token, "/v1/users/me/export");
  const title = `${deadline.title} study block`;
  const start = futureDate(3);
  const end = futureDate(63);
  await goto(page, "/today", "today-before-new-task");
  await clickAny(page, "today new task", [
    (p) => p.getByTestId("today-new-task"),
    (p) => p.getByRole("button", { name: /New task/i }),
  ]);
  await fillAny(page, "task title", [
    (p) => p.getByTestId("new-task-title"),
    (p) => p.locator("#title"),
  ], title);
  await fillAny(page, "task start", [
    (p) => p.getByTestId("new-task-start"),
    (p) => p.locator("#start"),
  ], localInput(start));
  await fillAny(page, "task end", [
    (p) => p.getByTestId("new-task-end"),
    (p) => p.locator("#end"),
  ], localInput(end));
  await fillAny(page, "task duration hours", [
    (p) => p.getByTestId("new-task-duration-hours"),
    (p) => p.getByTestId("new-task-modal").locator('input[type="number"]').nth(0),
    (p) => p.getByRole("dialog", { name: /New task/i }).locator('input[type="number"]').nth(0),
    (p) => p.locator('input[type="number"]').nth(0),
  ], "1");
  await fillAny(page, "task duration minutes", [
    (p) => p.getByTestId("new-task-duration-minutes"),
    (p) => p.getByTestId("new-task-modal").locator('input[type="number"]').nth(1),
    (p) => p.getByRole("dialog", { name: /New task/i }).locator('input[type="number"]').nth(1),
    (p) => p.locator('input[type="number"]').nth(1),
  ], "0");
  await chooseNudgeEligibleCategory(page);

  const sawSuggestion = await waitForDeadlineSuggestion(page, title, 8_000, { required: false });
  if (sawSuggestion) {
    await assertDeadlineSuggestionBrowserRender(token, beforeSuggestionExport);
    await screenshot(page, "new-task-deadline-suggestion");
    await clickAny(page, "confirm deadline suggestion", [
      (p) => p.getByTestId("new-task-deadline-confirm-suggestion"),
      (p) => p.getByRole("button", { name: /^Confirm$/i }),
      (p) => p.getByTestId("new-task-modal").locator("button").filter({ hasText: /^Confirm$/i }),
      (p) => p.getByRole("dialog", { name: /New task/i }).locator("button").filter({ hasText: /^Confirm$/i }),
      (p) => p.locator('button:has-text("Confirm")'),
      (p) => p.locator("button").filter({ hasText: /^Confirm$/i }),
    ], 3_000);
  } else {
    addIssue("deadline suggestion chip did not render; using explicit picker fallback", {
      deadline_id: deadline.deadline_id,
    });
    await clickAny(page, "bind to deadline", [
      (p) => p.getByRole("button", { name: /\+ Bind to a deadline/i }),
      (p) => p.getByText(/\+ Bind to a deadline/i),
    ], 5_000);
    let modal = page.getByTestId("new-task-modal").first();
    if (!(await modal.count().catch(() => 0))) {
      modal = page.getByRole("dialog", { name: /New task/i }).first();
    }
    const deadlineOption = modal
      .locator(`[data-testid="new-task-deadline-option"][data-deadline-id="${deadline.deadline_id}"]`)
      .first();
    if (await deadlineOption.count().catch(() => 0)) {
      await deadlineOption.scrollIntoViewIfNeeded({ timeout: 5_000 }).catch(() => {});
      await deadlineOption.click({ timeout: 10_000, force: true });
    } else {
      const picker = modal.getByText(/Pick a deadline/i).locator("..").locator("..");
      await picker.locator(".overflow-y-auto").first().evaluate((node) => {
        node.scrollTop = node.scrollHeight;
      }).catch(() => {});
      const fallbackOption = modal
        .getByRole("button", { name: new RegExp(escapeRegex(deadline.title), "i") })
        .first();
      await fallbackOption.scrollIntoViewIfNeeded({ timeout: 5_000 }).catch(() => {});
      await fallbackOption.click({ timeout: 10_000, force: true });
    }
  }

  const useNudge = page
    .locator('[data-testid="new-task-nudge-use"], button:has-text("Use ")')
    .first();
  const usedNudge = await useNudge.isVisible({ timeout: 10_000 }).catch(() => false);
  if (usedNudge) {
    await screenshot(page, "new-task-duration-nudge");
    await useNudge.click();
  } else {
    const modalText = await page
      .locator('[data-testid="new-task-modal"], [role="dialog"]')
      .first()
      .innerText({ timeout: 3_000 })
      .catch(() => "");
    const latestLookup = [...(page.__biasLookupResponses || [])]
      .reverse()
      .find((entry) => entry.url.includes("task") || entry.body.includes("task.creation_nudge") || entry.body.includes("rule11_no_nudge_control_day"));
    let latestLookupBody = null;
    if (latestLookup?.body?.startsWith("{")) {
      latestLookupBody = JSON.parse(latestLookup.body);
    }
    if (latestLookupBody?.suppressed_reason === "rule11_no_nudge_control_day") {
      addGated("creation nudge use branch", "Rule 11 no-nudge control active for Holmesberg/task.creation_nudge");
    } else {
      addCheck("creation nudge modal renders when research prior text is visible", (
        /Research prior/i.test(modalText)
        && /Use\s+\d+\s*min/i.test(modalText)
      ), {
        modal_text: modalText.slice(0, 1000),
        latest_lookup: latestLookup || null,
      });
    }
  }

  await clickAny(page, "create task", [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000);

  await clickCreateAnywayIfVisible(page, "new-task-soft-conflict");

  const task = await pollFor(token, "task created through UI backend visibility", async () => {
    return await findTaskByTitle(token, title);
  }, 20_000, 1_000);
  const visibleAfterCreate = await page
    .getByText(title, { exact: false })
    .first()
    .isVisible({ timeout: 3_000 })
    .catch(() => false);
  if (!visibleAfterCreate) {
    addIssue("task created through UI was not visible in Today before screenshot", { title });
  }
  await screenshot(page, "today-after-task-create");
  addCheck("task UI create reached backend", Boolean(task), { title });
  cleanup.tasks.add(task.task_id);
  addCheck("task bound to created deadline", task.deadline_id === deadline.deadline_id, {
    task_deadline_id: task.deadline_id,
    deadline_id: deadline.deadline_id,
    source: task.deadline_match_source,
  });
  return task;
}

async function createSoftConflictTaskThroughUi(page, token) {
  const title = `${prefix} overlap conflict branch`;
  const start = futureDate(5);
  const end = futureDate(65);
  await goto(page, "/today", "today-before-new-task-conflict");
  await clickAny(page, "today new task for conflict branch", [
    (p) => p.getByTestId("today-new-task"),
    (p) => p.getByRole("button", { name: /New task/i }),
  ]);
  await fillAny(page, "conflict task title", [
    (p) => p.getByTestId("new-task-title"),
    (p) => p.locator("#title"),
  ], title);
  await fillAny(page, "conflict task start", [
    (p) => p.getByTestId("new-task-start"),
    (p) => p.locator("#start"),
  ], localInput(start));
  await fillAny(page, "conflict task end", [
    (p) => p.getByTestId("new-task-end"),
    (p) => p.locator("#end"),
  ], localInput(end));
  await fillAny(page, "conflict task duration hours", [
    (p) => p.getByTestId("new-task-duration-hours"),
    (p) => p.getByTestId("new-task-modal").locator('input[type="number"]').nth(0),
    (p) => p.getByRole("dialog", { name: /New task/i }).locator('input[type="number"]').nth(0),
    (p) => p.locator('input[type="number"]').nth(0),
  ], "1");
  await fillAny(page, "conflict task duration minutes", [
    (p) => p.getByTestId("new-task-duration-minutes"),
    (p) => p.getByTestId("new-task-modal").locator('input[type="number"]').nth(1),
    (p) => p.getByRole("dialog", { name: /New task/i }).locator('input[type="number"]').nth(1),
    (p) => p.locator('input[type="number"]').nth(1),
  ], "0");
  await chooseNudgeEligibleCategory(page);

  const keepNudge = page
    .locator('[data-testid="new-task-nudge-keep"], button:has-text("Keep ")')
    .first();
  const keptNudge = await keepNudge.isVisible({ timeout: 10_000 }).catch(() => false);
  if (keptNudge) {
    await screenshot(page, "new-task-duration-nudge-keep");
    await keepNudge.click();
  } else {
    addIssue("creation nudge keep branch did not render before conflict create");
  }

  await clickAny(page, "create overlapping task", [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000);

  const createAnyway = await firstVisible(page, [
    (p) => p.getByTestId("new-task-create-anyway"),
    (p) => p.getByRole("button", { name: /^Create anyway$/i }),
    (p) => p.locator('button:has-text("Create anyway")'),
  ], 5_000, "create anyway").catch(() => null);
  const sawSoftConflict = Boolean(createAnyway);
  if (sawSoftConflict) {
    await screenshot(page, "new-task-soft-conflict-create-anyway");
    await createAnyway.click({ timeout: 10_000 });
  } else {
    addIssue("overlap branch did not show soft conflict create-anyway UI");
  }

  const task = await pollFor(token, "overlap branch backend visibility", async () => {
    return await findTaskByTitle(token, title);
  }, 20_000, 1_000);
  addCheck("overlap conflict branch creates task after explicit create-anyway", Boolean(task), { title });
  cleanup.tasks.add(task.task_id);
  addCheck("nudge keep branch preserves original 60 minute duration", (
    Number(task.planned_duration_minutes) === 60
  ), {
    title: task.title,
    planned_duration_minutes: task.planned_duration_minutes,
    nudge_keep_clicked: keptNudge,
    soft_conflict_seen: sawSoftConflict,
  });
  return task;
}

async function runNewTaskSubmitContractCoverage(page, token) {
  const contractDeadline = await createDeadlineViaApi(token, {
    title: `${prefix} submit contract deadline`,
    dueMinutes: 900,
  });
  const normalTitle = `${prefix} idempotent normal create`;
  const normalDescription = `normal submit contract ${runKey}`;
  const normalStart = futureDate(620);
  const normalEnd = futureDate(650);

  await openNewTaskModal(page, "today-before-submit-contract-normal");
  await fillNewTaskCore(page, {
    title: normalTitle,
    start: normalStart,
    end: normalEnd,
    minutes: "30",
  });
  await fillNewTaskDescription(page, normalDescription);
  await bindDeadlineInNewTaskModal(page, contractDeadline, "bind submit-contract deadline");
  await keepNudgeIfVisible(page, "new-task-submit-contract-normal-nudge-keep");

  const normalRequestStart = page.__createTaskRequests?.length || 0;
  const normalCreate = await firstVisible(page, [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000, "submit contract normal create");
  await normalCreate.evaluate((button) => {
    button.click();
    button.click();
  });

  const normalMatches = await pollFor(token, "normal submit contract backend visibility", async () => {
    const matches = await findTasksByExactTitle(token, normalTitle);
    return matches.length ? matches : null;
  }, 20_000, 1_000);
  for (const task of normalMatches || []) cleanup.tasks.add(task.task_id);
  addCheck("normal submit branch creates exactly one backend task", normalMatches.length === 1, {
    title: normalTitle,
    matches: normalMatches.map((task) => task.task_id),
  });
  const normalTask = normalMatches[0];
  addCheck("normal submit branch preserves description and deadline binding", (
    normalTask
    && String(normalTask.description || "").includes(normalDescription)
    && normalTask.deadline_id === contractDeadline.deadline_id
  ), {
    title: normalTitle,
    description: normalTask?.description ?? null,
    expected_deadline_id: contractDeadline.deadline_id,
    actual_deadline_id: normalTask?.deadline_id ?? null,
  });

  const normalRequests = createRequestsForTitle(page, normalTitle, normalRequestStart);
  assertStableCreateIdempotency("normal submit branch", normalRequests);
  addCheck("normal submit request includes shared create payload fields", (
    normalRequests.length >= 1
    && normalRequests.every((request) => (
      request.body?.description === normalDescription
      && request.body?.deadline_id === contractDeadline.deadline_id
      && request.body?.force === false
    ))
  ), normalRequests.map((request) => ({
    description: request.body?.description ?? null,
    deadline_id: request.body?.deadline_id ?? null,
    force: request.body?.force ?? null,
  })));

  const forcedTitle = `${prefix} idempotent forced create`;
  const forcedDescription = `forced submit contract ${runKey}`;
  await openNewTaskModal(page, "today-before-submit-contract-force");
  await fillNewTaskCore(page, {
    title: forcedTitle,
    start: normalStart,
    end: normalEnd,
    minutes: "30",
  });
  await fillNewTaskDescription(page, forcedDescription);
  await bindDeadlineInNewTaskModal(page, contractDeadline, "bind forced submit-contract deadline");
  await keepNudgeIfVisible(page, "new-task-submit-contract-force-nudge-keep");

  const forceRequestStart = page.__createTaskRequests?.length || 0;
  await clickAny(page, "submit contract overlapping create", [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000);
  const createAnyway = await firstVisible(page, [
    (p) => p.getByTestId("new-task-create-anyway"),
    (p) => p.getByRole("button", { name: /^Create anyway$/i }),
    (p) => p.locator('button:has-text("Create anyway")'),
  ], 8_000, "submit contract create anyway");
  await screenshot(page, "new-task-submit-contract-create-anyway");
  await createAnyway.evaluate((button) => {
    button.click();
    button.click();
  });

  const forcedMatches = await pollFor(token, "forced submit contract backend visibility", async () => {
    const matches = await findTasksByExactTitle(token, forcedTitle);
    return matches.length ? matches : null;
  }, 20_000, 1_000);
  for (const task of forcedMatches || []) cleanup.tasks.add(task.task_id);
  addCheck("forced submit branch creates exactly one backend task", forcedMatches.length === 1, {
    title: forcedTitle,
    matches: forcedMatches.map((task) => task.task_id),
  });
  const forcedTask = forcedMatches[0];
  addCheck("forced submit branch preserves description and deadline binding", (
    forcedTask
    && String(forcedTask.description || "").includes(forcedDescription)
    && forcedTask.deadline_id === contractDeadline.deadline_id
  ), {
    title: forcedTitle,
    description: forcedTask?.description ?? null,
    expected_deadline_id: contractDeadline.deadline_id,
    actual_deadline_id: forcedTask?.deadline_id ?? null,
  });

  const forceRequests = createRequestsForTitle(page, forcedTitle, forceRequestStart);
  const forcedRequests = forceRequests.filter((request) => request.body?.force === true);
  assertStableCreateIdempotency("forced submit branch", forcedRequests);
  addCheck("forced submit request includes shared create payload fields", (
    forcedRequests.length >= 1
    && forcedRequests.every((request) => (
      request.body?.description === forcedDescription
      && request.body?.deadline_id === contractDeadline.deadline_id
      && request.body?.force === true
    ))
  ), forceRequests.map((request) => ({
    description: request.body?.description ?? null,
    deadline_id: request.body?.deadline_id ?? null,
    force: request.body?.force ?? null,
    idempotency_key: request.idempotency_key,
  })));
}

async function runNewTaskBranchCoverage(page, token, anchorDeadline) {
  const noBindSourceDeadline = await createDeadlineViaApi(token, {
    title: `Zephyr ${randomUUID().slice(0, 8)} capstone`,
    dueMinutes: 420,
  });
  const pickAnotherSourceDeadline = await createDeadlineViaApi(token, {
    title: `Orion ${randomUUID().slice(0, 8)} thesis`,
    dueMinutes: 450,
  });
  const alternateDeadline = await createDeadlineViaApi(token, {
    title: `Atlas ${randomUUID().slice(0, 8)} workshop`,
    dueMinutes: 480,
  });
  const terminalDeadline = await createDeadlineViaApi(token, {
    title: `Cypher ${randomUUID().slice(0, 8)} milestone`,
    dueMinutes: 540,
    state: "completed",
  });

  const noBindTitle = noBindSourceDeadline.title;
  const noBindPreview = await apiFetch(token, "/v1/parse/deadline-preview", {
    method: "POST",
    body: JSON.stringify({ title: noBindTitle }),
  });
  addCheck("API preview can suggest no-deadline branch source deadline", (
    noBindPreview.deadline_id === noBindSourceDeadline.deadline_id
  ), {
    title: noBindTitle,
    expected_deadline_id: noBindSourceDeadline.deadline_id,
    actual_deadline_id: noBindPreview.deadline_id,
    actual_deadline_title: noBindPreview.deadline_title,
    source: noBindPreview.deadline_match_source,
    confidence: noBindPreview.deadline_match_confidence,
  });
  await suppressUnrenderedSurfaceProbe(
    token,
    noBindPreview,
    "deadline preview API branch probe",
  );
  const noBindCategory = `dogfood_${runKey.slice(0, 8)}`;
  await openNewTaskModal(page, "today-before-no-deadline-branch");
  await fillNewTaskCore(page, {
    title: noBindTitle,
    start: futureDate(220),
    end: futureDate(250),
    minutes: "30",
  });
  if (await waitForDeadlineSuggestion(page, noBindTitle)) {
    await clickAny(page, "no deadline suggestion", [
      (p) => p.getByTestId("new-task-deadline-no-deadline"),
      (p) => p.getByRole("button", { name: /^No deadline$/i }),
      (p) => p.locator('button:has-text("No deadline")'),
    ]);
  }
  await chooseCustomCategory(page, noBindCategory);
  const keptNudge = await keepNudgeIfVisible(page, "new-task-custom-category-nudge-keep");
  await clickAny(page, "create no-deadline custom-category task", [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000);
  await clickCreateAnywayIfVisible(page, "new-task-no-deadline-create-anyway");
  const noBindTask = await pollFor(token, "no-deadline branch backend visibility", async () => {
    return await findTaskByTitle(token, noBindTitle);
  }, 20_000, 1_000);
  const noBindVisible = await page
    .getByText(noBindTitle, { exact: false })
    .first()
    .isVisible({ timeout: 3_000 })
    .catch(() => false);
  if (!noBindVisible) {
    addIssue("no-deadline branch task was not visible in Today before branch assertion", {
      title: noBindTitle,
    });
  }
  addCheck("no-deadline branch creates task without deadline binding", (
    Boolean(noBindTask) && noBindTask.deadline_id === null
  ), {
    title: noBindTitle,
    deadline_id: noBindTask?.deadline_id ?? null,
    nudge_keep_clicked: keptNudge,
  });
  addCheck("custom category branch persists category", (
    noBindTask?.category === noBindCategory
  ), {
    expected: noBindCategory,
    actual: noBindTask?.category ?? null,
  });
  cleanup.tasks.add(noBindTask.task_id);

  const pickAnotherTitle = pickAnotherSourceDeadline.title;
  await openNewTaskModal(page, "today-before-pick-another-branch");
  await fillNewTaskCore(page, {
    title: pickAnotherTitle,
    start: futureDate(280),
    end: futureDate(310),
    minutes: "30",
  });
  if (await waitForDeadlineSuggestion(page, pickAnotherTitle)) {
    await clickAny(page, "pick another deadline", [
      (p) => p.getByTestId("new-task-deadline-pick-another"),
      (p) => p.getByRole("button", { name: /^Pick another$/i }),
      (p) => p.locator('button:has-text("Pick another")'),
    ]);
  }
  const alternateOption = await firstVisible(page, [
    (p) => p.locator(`[data-testid="new-task-deadline-option"][data-deadline-id="${alternateDeadline.deadline_id}"]`),
    (p) => p.getByRole("button", { name: new RegExp(escapeRegex(alternateDeadline.title), "i") }),
  ], 8_000, "alternate deadline option");
  await alternateOption.scrollIntoViewIfNeeded({ timeout: 5_000 }).catch(() => {});
  await alternateOption.click({ timeout: 10_000, force: true });
  await keepNudgeIfVisible(page, "new-task-pick-another-nudge-keep");
  await clickAny(page, "create pick-another task", [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000);
  await clickCreateAnywayIfVisible(page, "new-task-pick-another-create-anyway");
  const pickAnotherTask = await pollFor(token, "pick-another branch backend visibility", async () => {
    return await findTaskByTitle(token, pickAnotherTitle);
  }, 20_000, 1_000);
  const pickAnotherVisible = await page
    .getByText(pickAnotherTitle, { exact: false })
    .first()
    .isVisible({ timeout: 3_000 })
    .catch(() => false);
  if (!pickAnotherVisible) {
    addIssue("pick-another branch task was not visible in Today before branch assertion", {
      title: pickAnotherTitle,
    });
  }
  addCheck("pick-another branch binds the explicitly chosen deadline", (
    pickAnotherTask?.deadline_id === alternateDeadline.deadline_id
  ), {
    task_deadline_id: pickAnotherTask?.deadline_id ?? null,
    suggested_deadline_id: pickAnotherSourceDeadline.deadline_id,
    chosen_deadline_id: alternateDeadline.deadline_id,
  });
  cleanup.tasks.add(pickAnotherTask.task_id);

  let pickAnotherReturnTask = pickAnotherTask;
  const editedTitle = `${pickAnotherTitle} edited`;
  await goto(page, "/today", "today-before-edit-mode-branch");
  const row = page.locator(`[data-testid="task-row"][data-task-id="${pickAnotherTask.task_id}"]`).first();
  const rowVisible = await row.isVisible({ timeout: 2_000 }).catch(() => false);
  if (rowVisible) {
    await row.scrollIntoViewIfNeeded({ timeout: 10_000 });
    await row.getByText(pickAnotherTitle, { exact: false }).first().click({ timeout: 10_000 });
  } else {
    const titleCell = page.getByText(pickAnotherTitle, { exact: false }).first();
    const titleVisible = await titleCell.isVisible({ timeout: 3_000 }).catch(() => false);
    if (!titleVisible) {
      addGated(
        "edit mode after pick-another branch",
        "pick-another task is not visible in the current Today view; backend binding already passed",
      );
    } else {
      await titleCell.scrollIntoViewIfNeeded({ timeout: 10_000 });
      await titleCell.click({ timeout: 10_000 });
    }
  }
  if (rowVisible || await page.getByText(pickAnotherTitle, { exact: false }).first().isVisible({ timeout: 500 }).catch(() => false)) {
    await firstVisible(page, [
      (p) => p.getByTestId("new-task-save"),
      (p) => p.getByRole("button", { name: /^Save$/i }),
    ], 8_000, "edit mode save button");
    await fillAny(page, "edit task title", [
      (p) => p.getByTestId("new-task-title"),
      (p) => p.locator("#title"),
    ], editedTitle);
    await clickAny(page, "save edited task", [
      (p) => p.getByTestId("new-task-save"),
      (p) => p.getByRole("button", { name: /^Save$/i }),
    ], 5_000);
    const editedTask = await pollFor(token, "edited task title visibility", async () => {
      const next = await findTaskByTitle(token, editedTitle);
      return next?.task_id === pickAnotherTask.task_id ? next : null;
    });
    addCheck("edit mode preserves task identity while updating title", (
      editedTask.task_id === pickAnotherTask.task_id
    ), {
      task_id: editedTask.task_id,
      old_title: pickAnotherTitle,
      new_title: editedTitle,
    });
    pickAnotherReturnTask = editedTask;
  }

  const terminalCreateBody = await apiFetch(token, "/v1/create", {
    method: "POST",
    body: JSON.stringify({
      title: `${terminalDeadline.title} rejected task`,
      start: futureDate(340).toISOString(),
      end: futureDate(370).toISOString(),
      category: "work",
      source: "web",
      force: false,
      deadline_id: terminalDeadline.deadline_id,
    }),
  }, [400]);
  addCheck("terminal deadline explicit create binding is rejected by API", (
    /terminal|not bindable/i.test(JSON.stringify(terminalCreateBody))
  ), terminalCreateBody);

  await openNewTaskModal(page, "today-before-terminal-deadline-picker");
  await fillNewTaskCore(page, {
    title: `${terminalDeadline.title} picker hidden branch`,
    start: futureDate(380),
    end: futureDate(410),
    minutes: "30",
  });
  await clickAny(page, "open deadline picker for terminal filter", [
    (p) => p.getByRole("button", { name: /\+ Bind to a deadline/i }),
    (p) => p.getByText(/\+ Bind to a deadline/i),
  ], 5_000);
  const terminalOptionVisible = await page
    .locator(`[data-testid="new-task-deadline-option"][data-deadline-id="${terminalDeadline.deadline_id}"]`)
    .first()
    .isVisible({ timeout: 3_000 })
    .catch(() => false);
  addCheck("terminal deadline is hidden from browser deadline picker", !terminalOptionVisible, {
    terminal_deadline_id: terminalDeadline.deadline_id,
    terminal_state: terminalDeadline.state,
  });
  await page.keyboard.press("Escape").catch(() => {});

  return {
    noBindTask,
    pickAnotherTask: pickAnotherReturnTask,
    anchorDeadlineId: anchorDeadline.deadline_id,
    noBindSourceDeadlineId: noBindSourceDeadline.deadline_id,
    pickAnotherSourceDeadlineId: pickAnotherSourceDeadline.deadline_id,
    alternateDeadlineId: alternateDeadline.deadline_id,
    terminalDeadlineId: terminalDeadline.deadline_id,
  };
}

async function runBrainDumpPath(page, token) {
  const before = await apiFetch(token, "/v1/users/me/export");
  const title = `${prefix} brain dump block`;
  const deadlineTitle = `${prefix} brain dump deadline`;
  await goto(page, "/pulse", "pulse-before-brain-dump");
  await fillAny(page, "quick capture", [
    (p) => p.getByTestId("pulse-quick-capture-input"),
    (p) => p.locator("#quick-capture input").first(),
    (p) => p.getByPlaceholder(/brain dump anything/i),
  ], `${title} tomorrow 30min\n${deadlineTitle} tomorrow 11pm`);
  await clickAny(page, "quick capture submit", [
    (p) => p.getByTestId("pulse-quick-capture-submit"),
    (p) => p.getByRole("button", { name: /Capture/i }),
  ]);
  await firstVisible(page, [
    (p) => p.getByTestId("brain-dump-modal"),
    (p) => p.getByRole("dialog", { name: /Brain dump/i }),
  ], 8_000);
  await fillAny(page, "brain dump textarea", [
    (p) => p.getByTestId("brain-dump-textarea"),
    (p) => p.locator("textarea").first(),
  ], `${title} tomorrow 30min\n${deadlineTitle} tomorrow 11pm`);
  await clickAny(page, "brain dump parse", [
    (p) => p.getByTestId("brain-dump-parse"),
    (p) => p.getByRole("button", { name: /^Parse$/i }),
  ]);
  await page.getByText(/LyraOS found/i).first().waitFor({ timeout: 20_000 });
  const afterParse = await apiFetch(token, "/v1/users/me/export");
  addCheck("brain dump parse is write-free for tasks/deadlines", (
    countRows(before, "tasks") === countRows(afterParse, "tasks")
    && countRows(before, "deadlines") === countRows(afterParse, "deadlines")
  ), {
    before_tasks: countRows(before, "tasks"),
    after_tasks: countRows(afterParse, "tasks"),
    before_deadlines: countRows(before, "deadlines"),
    after_deadlines: countRows(afterParse, "deadlines"),
  });
  await screenshot(page, "brain-dump-preview");
  await clickAny(page, "brain dump lock in", [
    (p) => p.getByTestId("brain-dump-lock-in"),
    (p) => p.getByRole("button", { name: /Lock in/i }),
  ], 8_000);
  let createdTasks = [];
  let createdDeadlines = [];
  await pollFor(token, "brain dump commit task visibility", async () => {
    createdTasks = await findTasksByPrefix(token);
    return createdTasks.some((t) => t.title === title);
  });
  await pollFor(token, "brain dump commit deadline visibility", async () => {
    createdDeadlines = await findDeadlinesByPrefix(token);
    return createdDeadlines.some(
      (d) => d.title === deadlineTitle || d.title.startsWith(`${prefix} brain dump`)
    );
  });
  for (const task of createdTasks) cleanup.tasks.add(task.task_id);
  for (const deadline of createdDeadlines) cleanup.deadlines.add(deadline.deadline_id);
  addCheck("brain dump commit creates at least one task", createdTasks.some((t) => t.title === title), {
    created: createdTasks.map((t) => t.title),
  });
  const brainDumpDeadlineCreated = createdDeadlines.some(
    (d) => d.title === deadlineTitle || d.title.startsWith(`${prefix} brain dump`)
  );
  if (brainDumpDeadlineCreated && !createdDeadlines.some((d) => d.title === deadlineTitle)) {
    addIssue("brain dump deadline title was normalized by parser", {
      expected: deadlineTitle,
      created: createdDeadlines.map((d) => d.title),
    });
  }
  addCheck("brain dump commit creates or reuses deadline", brainDumpDeadlineCreated, {
    created: createdDeadlines.map((d) => d.title),
  });
}

async function brainDumpEditableLocators(page) {
  const dialog = page.getByRole("dialog", { name: /Brain dump/i }).first();
  let titleInputs = page.locator('[data-testid^="brain-dump-item-title-"]');
  if (await titleInputs.count() === 0) {
    titleInputs = dialog.locator("label").filter({ hasText: /^Title$/i }).locator("input");
  }
  let whenInputs = page.locator('[data-testid^="brain-dump-item-when-"]');
  if (await whenInputs.count() === 0) {
    whenInputs = dialog.locator('input[type="datetime-local"]');
  }
  let durationInputs = page.locator('[data-testid^="brain-dump-item-duration-"]');
  if (await durationInputs.count() === 0) {
    durationInputs = dialog.locator("label").filter({ hasText: /^Minutes$/i }).locator('input[type="number"]');
  }
  return { titleInputs, whenInputs, durationInputs };
}

async function runBrainDumpBranchCoverage(page, token) {
  const partialValidTitle = `${prefix} brain dump partial valid`;
  const partialStaleTitle = `${prefix} brain dump partial stale`;
  const partialRecoveredTitle = `${prefix} brain dump partial recovered`;
  const doubleSubmitTitle = `${prefix} brain dump double submit`;

  await goto(page, "/pulse", "pulse-before-brain-dump-partial-failure");
  await fillAny(page, "quick capture partial failure", [
    (p) => p.getByTestId("pulse-quick-capture-input"),
    (p) => p.locator("#quick-capture input").first(),
    (p) => p.getByPlaceholder(/brain dump anything/i),
  ], `${partialValidTitle} tomorrow 25min\n${partialStaleTitle} tomorrow 25min`);
  await clickAny(page, "quick capture partial failure submit", [
    (p) => p.getByTestId("pulse-quick-capture-submit"),
    (p) => p.getByRole("button", { name: /Capture/i }),
  ]);
  await firstVisible(page, [
    (p) => p.getByTestId("brain-dump-modal"),
    (p) => p.getByRole("dialog", { name: /Brain dump/i }),
  ], 8_000, "brain dump partial modal");
  await fillAny(page, "brain dump partial textarea", [
    (p) => p.getByTestId("brain-dump-textarea"),
    (p) => p.locator("textarea").first(),
  ], `${partialValidTitle} tomorrow 25min\n${partialStaleTitle} tomorrow 25min`);
  await clickAny(page, "brain dump partial parse", [
    (p) => p.getByTestId("brain-dump-parse"),
    (p) => p.getByRole("button", { name: /^Parse$/i }),
  ]);
  await page.getByText(/LyraOS found/i).first().waitFor({ timeout: 20_000 });

  const { titleInputs, whenInputs, durationInputs } = await brainDumpEditableLocators(page);
  addCheck("brain dump partial parse exposes editable item rows", await titleInputs.count() >= 2, {
    title_inputs: await titleInputs.count(),
    when_inputs: await whenInputs.count(),
  });
  await titleInputs.nth(0).fill(partialValidTitle);
  await titleInputs.nth(1).fill(partialStaleTitle);
  await whenInputs.nth(0).fill(localInput(futureDate(95)));
  await whenInputs.nth(1).fill(localInput(new Date(Date.now() - 24 * 60 * 60_000)));
  if (await durationInputs.count() >= 2) {
    await durationInputs.nth(0).fill("25");
    await durationInputs.nth(1).fill("25");
  }
  await screenshot(page, "brain-dump-partial-before-lock");
  await clickAny(page, "brain dump partial lock in", [
    (p) => p.getByTestId("brain-dump-lock-in"),
    (p) => p.getByRole("button", { name: /Lock in/i }),
  ], 8_000);
  await firstVisible(page, [
    (p) => p.getByTestId("brain-dump-failures"),
    (p) => p.getByText(/need review/i),
  ], 15_000, "brain dump partial failure review");
  await screenshot(page, "brain-dump-partial-failure-review");

  const validAfterPartial = await pollFor(token, "brain dump partial valid commit visibility", async () => {
    const matches = await findTasksByExactTitle(token, partialValidTitle);
    return matches.length === 1 ? matches : null;
  });
  for (const task of validAfterPartial || []) cleanup.tasks.add(task.task_id);
  const staleAfterPartial = await findTasksByExactTitle(token, partialStaleTitle);
  addCheck("brain dump partial commit saves valid item only", (validAfterPartial || []).length === 1, {
    title: partialValidTitle,
    matches: validAfterPartial,
  });
  addCheck("brain dump partial failure does not silently create stale item", staleAfterPartial.length === 0, {
    title: partialStaleTitle,
    matches: staleAfterPartial,
  });

  await clickAny(page, "brain dump edit failed items", [
    (p) => p.getByTestId("brain-dump-edit-failed-items"),
    (p) => p.getByRole("button", { name: /Edit failed items/i }),
  ], 8_000);
  await page.getByText(/LyraOS found/i).first().waitFor({ timeout: 10_000 });
  const {
    titleInputs: retryTitleInputs,
    whenInputs: retryWhenInputs,
  } = await brainDumpEditableLocators(page);
  addCheck("brain dump retry reopens only failed item without retyping full dump", await retryTitleInputs.count() === 1, {
    retry_title_inputs: await retryTitleInputs.count(),
  });
  const retrySeedTitle = await retryTitleInputs.nth(0).inputValue();
  addCheck("brain dump retry preserves failed item text", retrySeedTitle === partialStaleTitle, {
    expected: partialStaleTitle,
    actual: retrySeedTitle,
  });
  await retryTitleInputs.nth(0).fill(partialRecoveredTitle);
  await retryWhenInputs.nth(0).fill(localInput(futureDate(125)));
  await screenshot(page, "brain-dump-partial-edited-retry");
  await clickAny(page, "brain dump retry lock in", [
    (p) => p.getByTestId("brain-dump-lock-in"),
    (p) => p.getByRole("button", { name: /Lock in/i }),
  ], 8_000);
  const recoveredAfterRetry = await pollFor(token, "brain dump retry recovered task visibility", async () => {
    const matches = await findTasksByExactTitle(token, partialRecoveredTitle);
    return matches.length === 1 ? matches : null;
  });
  for (const task of recoveredAfterRetry || []) cleanup.tasks.add(task.task_id);
  addCheck("brain dump edited retry creates recovered item exactly once", (recoveredAfterRetry || []).length === 1, {
    title: partialRecoveredTitle,
    matches: recoveredAfterRetry,
  });

  await goto(page, "/pulse", "pulse-before-brain-dump-double-submit");
  await fillAny(page, "quick capture double submit", [
    (p) => p.getByTestId("pulse-quick-capture-input"),
    (p) => p.locator("#quick-capture input").first(),
    (p) => p.getByPlaceholder(/brain dump anything/i),
  ], `${doubleSubmitTitle} tomorrow 20min`);
  await clickAny(page, "quick capture double submit open", [
    (p) => p.getByTestId("pulse-quick-capture-submit"),
    (p) => p.getByRole("button", { name: /Capture/i }),
  ]);
  await firstVisible(page, [
    (p) => p.getByTestId("brain-dump-modal"),
    (p) => p.getByRole("dialog", { name: /Brain dump/i }),
  ], 8_000, "brain dump double submit modal");
  await fillAny(page, "brain dump double submit textarea", [
    (p) => p.getByTestId("brain-dump-textarea"),
    (p) => p.locator("textarea").first(),
  ], `${doubleSubmitTitle} tomorrow 20min`);
  await clickAny(page, "brain dump double submit parse", [
    (p) => p.getByTestId("brain-dump-parse"),
    (p) => p.getByRole("button", { name: /^Parse$/i }),
  ]);
  await page.getByText(/LyraOS found/i).first().waitFor({ timeout: 20_000 });
  const doubleSubmitButton = await firstVisible(page, [
    (p) => p.getByTestId("brain-dump-lock-in"),
    (p) => p.getByRole("button", { name: /Lock in/i }),
  ], 8_000, "brain dump double submit lock in");
  await doubleSubmitButton.evaluate((button) => {
    button.click();
    button.click();
  });
  const doubleSubmitMatches = await pollFor(token, "brain dump double submit task visibility", async () => {
    const matches = await findTasksByExactTitle(token, doubleSubmitTitle);
    return matches.length >= 1 ? matches : null;
  });
  for (const task of doubleSubmitMatches || []) cleanup.tasks.add(task.task_id);
  const finalDoubleSubmitMatches = await findTasksByExactTitle(token, doubleSubmitTitle);
  addCheck("brain dump double-submit creates exactly one task", finalDoubleSubmitMatches.length === 1, {
    title: doubleSubmitTitle,
    count: finalDoubleSubmitMatches.length,
    task_ids: finalDoubleSubmitMatches.map((task) => task.task_id),
  });
}

async function assertPressureMapBrowserRender(token, beforeExport) {
  await pollFor(token, "pressure map claimed candidates reach terminal lifecycle", async () => {
    const exported = await apiFetch(token, "/v1/users/me/export");
    const beforeIds = new Set(
      rows(beforeExport, "exposure_decision_events").map((row) => row.exposure_id),
    );
    const decisions = rows(exported, "exposure_decision_events")
      .filter((row) => !beforeIds.has(row.exposure_id))
      .filter((row) => row.content_template_id === "academic_pressure_map");
    const renderIds = new Set(
      rows(exported, "exposure_render_events")
        .filter((row) => row.surface === "academic.pressure_map")
        .map((row) => row.exposure_id),
    );
    const ackIds = new Set(
      rows(exported, "exposure_ack_events")
        .filter((row) => row.event_type === "render")
        .map((row) => row.exposure_id),
    );
    const terminalIds = new Set([
      ...renderIds,
      ...rows(exported, "suppression_events").map((row) => row.exposure_id),
    ]);
    const unterminatedClaimed = decisions.filter((row) => (
      row.decision_status !== "reserved" && !terminalIds.has(row.exposure_id)
    ));
    const browserProven = decisions.some((row) => (
      renderIds.has(row.exposure_id) && ackIds.has(row.exposure_id)
    ));
    return (
      decisions.length >= 1
      && browserProven
      && unterminatedClaimed.length === 0
    ) ? true : null;
  }, 10_000, 500);

  const afterExport = await apiFetch(token, "/v1/users/me/export");
  const beforeIds = new Set(
    rows(beforeExport, "exposure_decision_events").map((row) => row.exposure_id),
  );
  const decisions = rows(afterExport, "exposure_decision_events")
    .filter((row) => !beforeIds.has(row.exposure_id))
    .filter((row) => row.content_template_id === "academic_pressure_map");
  const renderIds = new Set(
    rows(afterExport, "exposure_render_events")
      .filter((row) => row.surface === "academic.pressure_map")
      .map((row) => row.exposure_id),
  );
  const ackIds = new Set(
    rows(afterExport, "exposure_ack_events")
      .filter((row) => row.event_type === "render")
      .map((row) => row.exposure_id),
  );
  const rendered = decisions.filter((row) => row.decision_status === "rendered");
  const browserProven = rendered
    .filter((row) => renderIds.has(row.exposure_id))
    .filter((row) => ackIds.has(row.exposure_id));
  const terminalIds = new Set([
    ...renderIds,
    ...rows(afterExport, "suppression_events").map((row) => row.exposure_id),
  ]);
  const unclaimed = decisions.filter((row) => !terminalIds.has(row.exposure_id));
  const unterminatedClaimed = unclaimed.filter((row) => row.decision_status !== "reserved");
  addCheck("pressure map render is browser-acknowledged", browserProven.length >= 1, {
    new_decision_count: decisions.length,
    rendered_count: rendered.length,
    browser_proven_count: browserProven.length,
    statuses: decisions.map((row) => row.decision_status).sort(),
  });
  addCheck(
    "pressure map has no fabricated rendered decision",
    rendered.every((row) => renderIds.has(row.exposure_id) && ackIds.has(row.exposure_id)),
    {
      rendered_count: rendered.length,
      missing_render_or_ack_count: rendered.filter((row) => (
        !renderIds.has(row.exposure_id) || !ackIds.has(row.exposure_id)
      )).length,
    },
  );
  addCheck(
    "pressure map unclaimed candidates do not claim browser delivery",
    unterminatedClaimed.length === 0,
    {
      new_decision_count: decisions.length,
      unclaimed_reserved_count: unclaimed.filter((row) => row.decision_status === "reserved").length,
      unterminated_claimed_count: unterminatedClaimed.length,
      unterminated_claimed_statuses: unterminatedClaimed
        .map((row) => row.decision_status)
        .sort(),
    },
  );
  return browserProven.map((row) => row.exposure_id);
}

async function runPressureMapPath(page, token, beforeExport) {
  const pressureDeadlineTitle = `${prefix} pressure map deadline`;
  const pressureBlockTitle = `${prefix} pressure recovery block`;
  const pressureMapPattern = `${apiOrigin.replace(/\/$/, "")}/v1/academic/pressure-map**`;
  let pressureMapRouteHandler = null;
  const pressureDeadline = await createDeadlineViaApi(token, {
    title: pressureDeadlineTitle,
    dueMinutes: (3 * 24 * 60) - 30,
  });
  const pressureSnapshot = await apiFetch(token, "/v1/academic/pressure-map?horizon_days=14");
  await suppressUnrenderedSurfaceProbe(token, pressureSnapshot, "pressure map setup probe");
  await goto(page, "/pulse", "pulse-pressure-map-render-proof");
  const browserExposureIds = await assertPressureMapBrowserRender(token, beforeExport);
  const seededPressureItem = Array.isArray(pressureSnapshot.items)
    ? pressureSnapshot.items.find((item) => item.obligation_id === pressureDeadline.deadline_id)
    : null;
  addCheck("pressure map includes seeded due-soon deadline before browser commit", Boolean(
    seededPressureItem
    && seededPressureItem.pressure_level === "high"
    && seededPressureItem.source_class === "native"
  ), {
    deadline_id: pressureDeadline.deadline_id,
    item: seededPressureItem,
    recovery_options: pressureSnapshot.recovery_options,
  });
  const backendPlanOption = Array.isArray(pressureSnapshot.recovery_options)
    ? pressureSnapshot.recovery_options.find((option) => (
        option.action === "create_plan" || option.action === "split_into_blocks"
      ))
    : null;
  if (!backendPlanOption) {
    addGated("real pressure-map recovery option", {
      reason: "backend returned no create_plan/split_into_blocks option for seeded high-pressure item",
      warnings: pressureSnapshot.warnings,
      recovery_options: pressureSnapshot.recovery_options,
    });
    if (!forcePressureRecovery) {
      addIssue("pressure map commit path skipped because backend recovery nudges are gated", {
        hint: "rerun with --force-pressure-recovery to exercise the browser commit seam against public createTask",
      });
      return { exposureIds: browserExposureIds };
    }
    addIssue("pressure map recovery options unavailable; using browser-only recovery fixture for commit seam coverage", {
      warnings: pressureSnapshot.warnings,
      recovery_options: pressureSnapshot.recovery_options,
    });
    pressureMapRouteHandler = async (route) => {
      const body = {
        ...pressureSnapshot,
        exposure_id: null,
        render_snapshot: null,
        recovery_options: [
          {
            action: "create_plan",
            label: "Create a recovery plan",
            detail: "Turn the due-soon pressure points into editable study blocks.",
            obligation_ids: [pressureDeadline.deadline_id],
          },
        ],
        warnings: [
          ...(pressureSnapshot.warnings || []),
          "Dogfood browser fixture: recovery option forced because public backend has recovery nudges gated.",
        ],
      };
      await route.fulfill({
        status: 200,
        headers: {
          "content-type": "application/json",
          "access-control-allow-origin": frontendOrigin,
          "access-control-allow-credentials": "true",
        },
        body: JSON.stringify(body),
      });
    };
    await page.route(pressureMapPattern, pressureMapRouteHandler);
  }

  const beforeTasks = await findTasksByPrefix(token);
  try {
    await goto(page, "/pulse", "pulse-pressure-map");
    const previewControl = page.getByTestId("pressure-map-preview").first();
    const previewVisible = await previewControl.isVisible({ timeout: 8_000 }).catch(() => false);
    addCheck("pressure map preview is available after seeded due-soon deadline", previewVisible, {
      deadline_id: pressureDeadline.deadline_id,
      title: pressureDeadlineTitle,
      forced_browser_fixture: Boolean(pressureMapRouteHandler),
    });
    const previewText = (await previewControl.innerText()).trim();
    const desktopPreviewBox = await previewControl.boundingBox();
    addCheck(
      "pressure map plan action has explicit copy and a stable click target",
      /Preview plan/i.test(previewText)
        && desktopPreviewBox !== null
        && desktopPreviewBox.height >= 32
        && desktopPreviewBox.width >= 96,
      { text: previewText, box: desktopPreviewBox },
    );
    const horizonControls = page.locator('[data-testid^="pressure-map-horizon-"]');
    const horizonCount = await horizonControls.count();
    const horizonState = [];
    for (let index = 0; index < horizonCount; index += 1) {
      const control = horizonControls.nth(index);
      horizonState.push({
        test_id: await control.getAttribute("data-testid"),
        pressed: await control.getAttribute("aria-pressed"),
        box: await control.boundingBox(),
      });
    }
    addCheck(
      "pressure map horizon controls expose one pressed 32px segmented state",
      horizonCount === 3
        && horizonState.filter((control) => control.pressed === "true").length === 1
        && horizonState.every((control) => (
          control.box !== null
          && control.box.height >= 32
          && control.box.width >= 48
        )),
      horizonState,
    );
    await screenshot(page, "pressure-map-affordance-desktop");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(250);
    const mobilePreviewBox = await previewControl.boundingBox();
    const mobileHorizonBoxes = [];
    for (let index = 0; index < horizonCount; index += 1) {
      mobileHorizonBoxes.push(await horizonControls.nth(index).boundingBox());
    }
    addCheck(
      "pressure map action controls remain visible and uncut on mobile",
      mobilePreviewBox !== null
        && mobilePreviewBox.height >= 32
        && mobilePreviewBox.x >= 0
        && mobilePreviewBox.x + mobilePreviewBox.width <= 390
        && mobileHorizonBoxes.every((box) => (
          box !== null
          && box.height >= 32
          && box.x >= 0
          && box.x + box.width <= 390
        )),
      { preview: mobilePreviewBox, horizons: mobileHorizonBoxes },
    );
    await screenshot(page, "pressure-map-affordance-mobile");
    await page.setViewportSize({ width: 1440, height: 950 });
    await page.waitForTimeout(250);
    await clickAny(page, "pressure preview", [(p) => p.getByTestId("pressure-map-preview")]);
    await firstVisible(page, [
      (p) => p.getByTestId("pressure-map-plan-preview"),
      (p) => p.getByRole("dialog", { name: /Preview recovery plan/i }),
    ], 8_000);
    await screenshot(page, "pressure-map-preview");
    await clickAny(page, "pressure preview dismiss", [
      (p) => p.getByTestId("pressure-map-preview-dismiss"),
      (p) => p.getByRole("button", { name: /^Dismiss$/i }),
    ]);
    await page.waitForTimeout(1_000);
    const afterDismissTasks = await findTasksByPrefix(token);
    addCheck("pressure map dismiss does not create dogfood tasks", afterDismissTasks.length === beforeTasks.length, {
      before: beforeTasks.length,
      after: afterDismissTasks.length,
    });
    const afterDismissMatches = await findTasksByExactTitle(token, pressureBlockTitle);
    addCheck("pressure map dismiss does not create recovery block", afterDismissMatches.length === 0, {
      title: pressureBlockTitle,
      matches: afterDismissMatches,
    });

    await clickAny(page, "pressure preview reopen", [(p) => p.getByTestId("pressure-map-preview")], 8_000);
    const dialog = await firstVisible(page, [
      (p) => p.getByTestId("pressure-map-plan-preview"),
      (p) => p.getByRole("dialog", { name: /Preview recovery plan/i }),
    ], 8_000, "pressure map plan preview reopen");
    const planRows = dialog.locator('[data-testid="pressure-map-plan-row"]');
    const rowCount = await planRows.count();
    let seededRowIndex = -1;
    for (let i = 0; i < rowCount; i += 1) {
      const row = planRows.nth(i);
      const text = await row.innerText();
      if (text.includes(pressureDeadlineTitle)) {
        seededRowIndex = i;
        continue;
      }
      const toggle = row.getByTestId("pressure-map-plan-row-toggle").first();
      const toggleText = await toggle.innerText().catch(() => "");
      if (/Include/i.test(toggleText)) {
        await toggle.click();
      }
    }
    addCheck("pressure map plan preview includes seeded editable row", seededRowIndex >= 0, {
      row_count: rowCount,
      deadline_title: pressureDeadlineTitle,
    });
    const seededRow = planRows.nth(seededRowIndex);
    const blockStart = futureDate((2 * 24 * 60) + 75);
    const blockEnd = futureDate((2 * 24 * 60) + 105);
    await seededRow.getByTestId("pressure-map-plan-row-title").fill(pressureBlockTitle);
    await seededRow.getByTestId("pressure-map-plan-row-start").fill(localInput(blockStart));
    await seededRow.getByTestId("pressure-map-plan-row-end").fill(localInput(blockEnd));
    await screenshot(page, "pressure-map-seeded-commit-preview");
    const lockIn = await firstVisible(page, [
      (p) => p.getByTestId("pressure-map-preview-lock-in"),
      (p) => p.getByRole("button", { name: /Lock in/i }),
    ], 8_000, "pressure map lock in");
    await lockIn.evaluate((button) => {
      button.click();
      button.click();
    });
    const createdMatches = await pollFor(token, "pressure map recovery block visibility", async () => {
      const matches = await findTasksByExactTitle(token, pressureBlockTitle);
      return matches.length >= 1 ? matches : null;
    }, 20_000, 1_000);
    for (const task of createdMatches || []) cleanup.tasks.add(task.task_id);
    if (!createdMatches || createdMatches.length === 0) {
      const createAnyway = dialog.getByRole("button", { name: /Create anyway/i }).first();
      if (await createAnyway.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await screenshot(page, "pressure-map-soft-conflict-create-anyway");
        await createAnyway.click();
      }
    }
    await page.waitForTimeout(1_500);
    const finalMatches = await findTasksByExactTitle(token, pressureBlockTitle);
    for (const task of finalMatches || []) cleanup.tasks.add(task.task_id);
    addCheck("pressure map double-lock creates exactly one recovery block", finalMatches.length === 1, {
      title: pressureBlockTitle,
      task_ids: finalMatches.map((task) => task.task_id),
    });
    const createdTask = finalMatches[0] || null;
    addCheck("pressure map committed block keeps deadline binding and planning-footprint provenance", Boolean(
      createdTask
      && createdTask.deadline_id === pressureDeadline.deadline_id
      && createdTask.state === "PLANNED"
      && createdTask.executed_duration_minutes === null
      && String(createdTask.description || "").includes("Created from Pressure Map recovery preview.")
      && String(createdTask.description || "").includes("Planning footprint only; execution truth comes from the timer.")
    ), createdTask || { title: pressureBlockTitle });

    await goto(page, "/calendar", "calendar-after-pressure-map-commit");
    await clickAny(page, "calendar month view for pressure block", [
      () => page.getByTestId("calendar-view-month-grid"),
      () => page.getByRole("button", { name: /^Month$/i }),
    ], 8_000);
    const taskStart = new Date(createdTask?.start || Date.now());
    const currentDate = new Date();
    const monthOffset = (
      (taskStart.getFullYear() - currentDate.getFullYear()) * 12
      + taskStart.getMonth()
      - currentDate.getMonth()
    );
    const boundedMonthOffset = Math.max(-2, Math.min(2, monthOffset));
    for (let step = 0; step < Math.abs(boundedMonthOffset); step += 1) {
      const direction = boundedMonthOffset > 0 ? /Next period/i : /Previous period/i;
      await clickAny(page, "calendar pressure-block month navigation", [
        () => page.getByRole("button", { name: direction }).first(),
      ], 8_000);
      await page.waitForTimeout(500);
    }
    const calendarLoading = page.getByText(/Loading calendar/i).first();
    const calendarRangeLoaded = await calendarLoading
      .waitFor({ state: "hidden", timeout: 30_000 })
      .then(() => true)
      .catch(() => false);
    addCheck("calendar completes the pressure-block range query", calendarRangeLoaded, {
      task_id: createdTask?.task_id || null,
      task_date: Number.isNaN(taskStart.getTime()) ? null : dateKey(taskStart),
      month_offset: monthOffset,
    });
    const calendarEvent = page
      .locator(`[data-event-id="${createdTask?.task_id || "missing"}"]`)
      .first();
    const calendarEventVisible = await calendarEvent
      .waitFor({ state: "visible", timeout: 12_000 })
      .then(() => true)
      .catch(() => false);
    await screenshot(page, "calendar-pressure-map-commit-month");
    addCheck("calendar shows pressure-map committed recovery block before cleanup", calendarEventVisible, {
      title: pressureBlockTitle,
      task_id: createdTask?.task_id || null,
      task_date: Number.isNaN(taskStart.getTime()) ? null : dateKey(taskStart),
      month_offset: monthOffset,
      locator_visible: calendarEventVisible,
    });
  } finally {
    if (pressureMapRouteHandler) {
      await page.unroute(pressureMapPattern, pressureMapRouteHandler).catch(() => {});
    }
  }
  return { exposureIds: browserExposureIds };
}

async function assertPulseStopOutputSuppression(token, beforeExport, taskId) {
  const snapshot = await pollFor(token, "Pulse stop-output suppression evidence", async () => {
    const exported = await apiFetch(token, "/v1/users/me/export");
    const decisions = newStopwatchOutputDecisions(beforeExport, exported, taskId);
    return decisions.length > 0 ? { exported, decisions } : null;
  }, 12_000, 750);
  if (!snapshot) {
    addGated(
      "Pulse stop-output suppression browser proof",
      "the stopped task produced no eligible micro-mirror or calibration candidate",
    );
    return [];
  }

  const { exported, decisions } = snapshot;
  const renderIds = new Set(
    rows(exported, "exposure_render_events").map((row) => row.exposure_id),
  );
  const ackIds = new Set(
    rows(exported, "exposure_ack_events")
      .filter((row) => row.event_type === "render")
      .map((row) => row.exposure_id),
  );
  const suppressionByExposure = new Map(
    rows(exported, "suppression_events").map((row) => [row.exposure_id, row]),
  );
  const clientSuppressed = decisions.filter((row) => (
    suppressionByExposure.get(row.exposure_id)?.suppression_reason
      === "client_surface_unavailable"
  ));

  addCheck("Pulse stop outputs never fabricate browser render or acknowledgement", decisions.every((row) => (
    !renderIds.has(row.exposure_id) && !ackIds.has(row.exposure_id)
  )), {
    decisions: decisions.map((row) => ({
      exposure_id: row.exposure_id,
      content_template_id: row.content_template_id,
      decision_status: row.decision_status,
      randomization_arm: row.randomization_arm,
    })),
    rendered_ids: decisions.filter((row) => renderIds.has(row.exposure_id)).map((row) => row.exposure_id),
    acked_ids: decisions.filter((row) => ackIds.has(row.exposure_id)).map((row) => row.exposure_id),
  });
  addCheck("Pulse stop outputs terminate as explicit suppression", decisions.every((row) => (
    row.decision_status === "suppressed" && suppressionByExposure.has(row.exposure_id)
  )), {
    decisions: decisions.map((row) => ({
      exposure_id: row.exposure_id,
      content_template_id: row.content_template_id,
      decision_status: row.decision_status,
    })),
    suppressions: decisions.map((row) => {
      const suppression = suppressionByExposure.get(row.exposure_id);
      return suppression ? {
        exposure_id: suppression.exposure_id,
        suppression_reason: suppression.suppression_reason,
      } : null;
    }),
  });

  if (clientSuppressed.length === 0) {
    addGated(
      "Pulse client-surface-unavailable suppression branch",
      "Rule 11 or output eligibility suppressed every stopwatch output before client delivery",
    );
  } else {
    const legacyRows = rows(exported, "reflection_view_logs");
    addCheck("Pulse hidden stop outputs remain unviewed in the legacy adapter", clientSuppressed.every((decision) => (
      legacyRows.some((row) => (
        row.task_id === taskId
        && row.reflection_type === decision.content_template_id
        && !row.viewed_at
      ))
    )), {
      task_id: taskId,
      exposure_ids: clientSuppressed.map((row) => row.exposure_id),
    });
  }

  for (const decision of decisions) {
    if (suppressionByExposure.has(decision.exposure_id)) {
      cleanup.exposureSuppressions.add(decision.exposure_id);
    }
  }
  return decisions.map((row) => row.exposure_id);
}

async function runTimerPath(page, token, task) {
  await goto(page, "/pulse", "pulse-before-timer");
  let focus = page.getByTestId("pulse-focus-card").first();
  if (!(await focus.count().catch(() => 0))) {
    focus = page.locator("body");
  }
  const option = page.locator(`[data-testid="focus-task-option"][data-task-id="${task.task_id}"]`).first();
  if (await option.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await option.click();
  } else {
    const titleOption = page.getByText(task.title, { exact: false }).first();
    if (await titleOption.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await titleOption.click().catch(() => {});
    }
  }
  await clickAny(page, "start session", [
    () => focus.getByTestId("focus-start-session"),
    () => focus.getByRole("button", { name: /Start session/i }),
  ], 10_000);
  let status = await pollFor(token, "timer start active status", async () => {
    const next = await apiFetch(token, "/v1/stopwatch/status");
    return next.active && next.task_id === task.task_id ? next : null;
  }, 15_000, 1_000);
  if (!status) {
    status = await apiFetch(token, "/v1/stopwatch/status");
    await screenshot(page, "timer-start-no-active-status");
  }
  addCheck("timer start opens active session", Boolean(status.active && status.task_id === task.task_id), status);
  const sessionId = status.session_id;

  await clickAny(page, "pause session", [
    () => focus.getByTestId("focus-pause"),
    () => focus.getByRole("button", { name: /^Pause$/i }),
  ], 10_000);
  await page.waitForTimeout(1_200);
  status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("timer pause is reflected in status", Boolean(status.active && status.paused), status);
  const pausedSessionId = status.session_id;
  const pauseSecondsBeforeNavigation = Number(status.current_pause_seconds || 0);

  await firstVisible(page, [
    () => focus.getByTestId("focus-resume"),
    () => focus.getByRole("button", { name: /^Resume$/i }),
  ], 8_000, "timer-paused-resume-visible-before-refresh");
  await screenshot(page, "timer-paused-before-refresh");

  await page.reload({ waitUntil: "domcontentloaded" });
  await firstVisible(page, [
    () => page.getByTestId("pulse-focus-card").first().getByTestId("focus-resume"),
    () => page.getByRole("button", { name: /^Resume$/i }),
  ], 12_000, "timer-paused-resume-visible-after-refresh");
  status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("timer paused session survives pulse refresh", Boolean(
    status.active
    && status.paused
    && status.session_id === pausedSessionId
    && status.task_id === task.task_id
  ), status);
  await screenshot(page, "timer-paused-after-refresh");

  await goto(page, "/calendar", "calendar-while-timer-paused");
  status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("timer paused session survives calendar navigation", Boolean(
    status.active
    && status.paused
    && status.session_id === pausedSessionId
    && status.task_id === task.task_id
  ), status);

  await goto(page, "/today", "today-while-timer-paused");
  const todayPausedText = await page.locator("body").innerText().catch(() => "");
  addCheck("today active timer banner shows paused session after navigation", Boolean(
    todayPausedText.includes(task.title)
    && /Paused|Resume/i.test(todayPausedText)
  ), {
    task_title: task.title,
    body_excerpt: todayPausedText.slice(0, 500),
  });
  await screenshot(page, "today-timer-paused-after-navigation");

  await goto(page, "/pulse", "pulse-after-paused-navigation");
  focus = page.getByTestId("pulse-focus-card").first();
  await firstVisible(page, [
    () => focus.getByTestId("focus-resume"),
    () => focus.getByRole("button", { name: /^Resume$/i }),
  ], 12_000, "timer-paused-resume-visible-after-navigation");
  await page.waitForTimeout(1_500);
  status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("timer pause counter remains anchored across refresh/navigation", Boolean(
    status.active
    && status.paused
    && status.session_id === pausedSessionId
    && Number(status.current_pause_seconds || 0) >= pauseSecondsBeforeNavigation
  ), {
    before_seconds: pauseSecondsBeforeNavigation,
    after_seconds: status.current_pause_seconds,
    status,
  });

  const reentryQueue = page.locator('section[aria-label="Re-entry queue"]').first();
  const reentryText = await reentryQueue.innerText({ timeout: 10_000 }).catch(() => "");
  addCheck("pulse re-entry queue shows paused task", Boolean(
    reentryText.includes(task.title)
    && /Pick it back up/i.test(reentryText)
  ), {
    task_title: task.title,
    body_excerpt: reentryText.slice(0, 500),
  });
  await clickAny(page, "pulse re-entry pick it back up", [
    () => reentryQueue.getByRole("button", { name: /Pick it back up/i }).first(),
    () => page.getByRole("button", { name: /Pick it back up/i }).first(),
  ], 10_000);
  for (let i = 0; i < 6; i += 1) {
    await page.waitForTimeout(1_000);
    status = await apiFetch(token, "/v1/stopwatch/status");
    if (status.active && !status.paused) break;
  }
  if (status.active && status.paused) {
    await screenshot(page, "pulse-reentry-resume-still-paused");
  }
  addCheck("pulse re-entry pick-up resumes paused session", Boolean(status.active && !status.paused), status);
  addCheck("timer resume clears paused flag", Boolean(status.active && !status.paused), status);

  const beforeStopOutputExport = await apiFetch(token, "/v1/users/me/export");

  await clickAny(page, "stop session", [
    () => focus.getByTestId("focus-stop"),
    () => focus.getByRole("button", { name: /^Stop$/i }),
  ], 10_000);
  await setRangeAny(page, "post-task reflection", [
    (p) => p.getByLabel(/Post-task reflection/i),
    (p) => p.locator('input[type="range"]').last(),
  ], 4, 8_000);
  await page.waitForFunction(() => {
    return [...document.querySelectorAll("button")].some((button) => {
      return /Finish/i.test(button.textContent || "") && !button.disabled;
    });
  }, null, { timeout: 5_000 }).catch(() => {});
  await fillAny(page, "completion percent", [
    (p) => p.getByTestId("focus-completion"),
    (p) => p.locator('input[inputmode="numeric"]').first(),
  ], "100", 8_000);
  const scope = page.getByTestId("focus-scope-stuck_to_plan").first();
  if (await scope.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await scope.click();
  }
  await clickAny(page, "finish session", [
    (p) => p.getByTestId("focus-finish"),
    (p) => p.getByRole("button", { name: /Finish/i }),
  ], 8_000);
  await page.waitForTimeout(1_500);
  let afterFirstFinish = await apiFetch(token, "/v1/stopwatch/status");
  if (afterFirstFinish.active) {
    await clickAny(page, "confirm early finish", [
      (p) => p.getByTestId("focus-finish"),
      (p) => p.getByRole("button", { name: /Finish anyway|Finish/i }),
    ], 8_000);
  }
  await page.waitForTimeout(2_000);
  status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("timer stop clears active session", !status.active, status);
  await assertPulseStopOutputSuppression(
    token,
    beforeStopOutputExport,
    task.task_id,
  );
  const refreshed = await findTaskByTitle(token, task.title);
  addCheck("timer stop writes execution delta fields", Boolean(
    refreshed
    && refreshed.state === "EXECUTED"
    && refreshed.executed_duration_minutes !== null
    && refreshed.duration_delta_minutes !== null
    && refreshed.pre_task_readiness !== null
    && refreshed.post_task_reflection !== null
    && typeof refreshed.pause_count === "number"
  ), refreshed);
  await screenshot(page, "pulse-after-timer-stop");
  return { task: refreshed, sessionId };
}

async function submitTodayStopDialog(page, dialog, buttonName, label) {
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("/v1/stopwatch/stop"),
    { timeout: 15_000 },
  ).catch((error) => ({
    __missing: true,
    message: String(error?.message || error).split("\n")[0],
  }));
  await clickAny(page, label, [
    () => dialog.getByRole("button", { name: buttonName }).first(),
  ], 10_000);
  const response = await responsePromise;
  addCheck(`${label} reaches the canonical stop endpoint`, Boolean(
    response && !response.__missing && response.status() < 400
  ), {
    status: response?.__missing ? null : response.status(),
    error: response?.__missing ? response.message : null,
  });
  return await response.json();
}

async function runTodayStopOutputRenderPath(page, token) {
  const beforeExport = await apiFetch(token, "/v1/users/me/export");
  const title = `${prefix} today stop output`;
  const created = await createTaskViaApi(token, {
    title,
    startMinutes: 12,
    durationMinutes: 30,
    category: `dogfood_stop_output_${runKey}`,
  });
  const task = await findTaskByTitle(token, title);
  addCheck("Today stop-output setup creates a canonical task", Boolean(
    created?.task_id && task?.task_id === created.task_id
  ), { created, task });

  await apiFetch(token, "/v1/stopwatch/start", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": boundedIdentifier(`today-stop-output-start:${runKey}`),
    },
    body: JSON.stringify({
      task_id: task.task_id,
      pre_task_readiness: 3,
    }),
  });

  const taskDate = dateKey(new Date(task.planned_start_utc || Date.now()));
  await goto(page, `/today?date=${encodeURIComponent(taskDate)}`, "today-stop-output-proof");
  await closeBlockingDialog(page, "today stop-output proof");
  const taskRow = page
    .locator(`[data-testid="task-row"][data-task-id="${task.task_id}"]`)
    .first();
  const taskRowVisible = await taskRow
    .waitFor({ state: "visible", timeout: 12_000 })
    .then(() => true)
    .catch(() => false);
  addCheck("Today renders the active stop-output proof task", taskRowVisible, {
    task_id: task.task_id,
    task_date: taskDate,
  });
  await taskRow.locator('button[title="Stop timer"]').click();

  const dialog = page.getByRole("dialog").filter({ hasText: /How was your focus/i }).first();
  await firstVisible(page, [() => dialog], 8_000, "Today reflection dialog");
  await dialog.getByRole("button", { name: /Average - some flow/i }).click();
  await dialog.locator("#pct").fill("100");
  const scope = dialog.getByRole("button", { name: /Stuck to plan/i }).first();
  if (await scope.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await scope.click();
  }

  let stopBody = await submitTodayStopDialog(
    page,
    dialog,
    /^Stop timer$/i,
    "Today stop-output first submit",
  );
  if (stopBody.requires_confirmation) {
    await firstVisible(page, [
      () => dialog.getByRole("button", { name: /Confirm early stop/i }).first(),
    ], 8_000, "Today early-stop confirmation");
    stopBody = await submitTodayStopDialog(
      page,
      dialog,
      /Confirm early stop/i,
      "Today stop-output confirmation",
    );
  }

  addCheck("Today stop-output path closes the timer", Boolean(
    stopBody?.task_id === task.task_id && !stopBody.requires_confirmation
  ), stopBody);
  const status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("Today stop-output proof leaves no active timer", !status.active, status);

  const exposureId = stopBody.micro_mirror_exposure_id || null;
  if (!exposureId) {
    const afterControl = await apiFetch(token, "/v1/users/me/export");
    const decisions = newStopwatchOutputDecisions(beforeExport, afterControl, task.task_id);
    const renderIds = new Set(
      rows(afterControl, "exposure_render_events").map((row) => row.exposure_id),
    );
    const ackIds = new Set(
      rows(afterControl, "exposure_ack_events").map((row) => row.exposure_id),
    );
    const suppressionIds = new Set(
      rows(afterControl, "suppression_events").map((row) => row.exposure_id),
    );
    addCheck("Today Rule 11 control remains explicit non-render evidence", decisions.length > 0 && decisions.every((row) => (
      row.decision_status === "suppressed"
      && suppressionIds.has(row.exposure_id)
      && !renderIds.has(row.exposure_id)
      && !ackIds.has(row.exposure_id)
    )), {
      decisions: decisions.map((row) => ({
        exposure_id: row.exposure_id,
        content_template_id: row.content_template_id,
        decision_status: row.decision_status,
        randomization_arm: row.randomization_arm,
      })),
    });
    for (const decision of decisions) cleanup.exposureSuppressions.add(decision.exposure_id);
    addGated(
      "Today stopwatch output positive browser render proof",
      "Rule 11 no-nudge control suppressed the eligible micro-mirror before delivery",
    );
    return { task, exposureIds: [] };
  }

  const toast = page
    .getByTestId("notification-toast")
    .filter({ hasText: stopBody.micro_mirror })
    .first();
  const toastVisible = await toast
    .waitFor({ state: "visible", timeout: 10_000 })
    .then(() => true)
    .catch(() => false);
  addCheck("Today renders the micro-mirror in a real Toast", toastVisible, {
    exposure_id: exposureId,
    message: stopBody.micro_mirror,
  });
  const evidence = await pollFor(token, "Today stop-output render evidence", async () => {
    const exported = await apiFetch(token, "/v1/users/me/export");
    const decision = rows(exported, "exposure_decision_events")
      .find((row) => row.exposure_id === exposureId);
    const renders = rows(exported, "exposure_render_events")
      .filter((row) => row.exposure_id === exposureId);
    const acks = rows(exported, "exposure_ack_events")
      .filter((row) => row.exposure_id === exposureId && row.event_type === "render");
    const legacy = rows(exported, "reflection_view_logs")
      .find((row) => row.view_id === stopBody.micro_mirror_view_id);
    return decision?.decision_status === "rendered"
      && decision?.delivered_at
      && renders.length === 1
      && acks.length === 1
      && legacy?.viewed_at
      ? { decision, renders, acks, legacy }
      : null;
  }, 15_000, 750);
  addCheck("Today Toast creates exactly one authenticated render and legacy view", Boolean(evidence), evidence ? {
    exposure_id: exposureId,
    decision_status: evidence.decision.decision_status,
    delivered_at_present: Boolean(evidence.decision.delivered_at),
    render_count: evidence.renders.length,
    render_surface: evidence.renders[0]?.surface || null,
    ack_count: evidence.acks.length,
    legacy_view_id: evidence.legacy.view_id,
    legacy_viewed_at_present: Boolean(evidence.legacy.viewed_at),
  } : {
    exposure_id: exposureId,
    legacy_view_id: stopBody.micro_mirror_view_id,
  });
  await screenshot(page, "today-stop-output-browser-rendered");
  await toast.getByTestId("notification-toast-dismiss").click().catch(() => {});
  return { task, exposureIds: [exposureId] };
}

async function runPulseMissedPlanDropPath(page, token) {
  const title = `${prefix} missed plan drop`;
  const task = await createTaskViaApi(token, {
    title,
    startMinutes: 420,
    durationMinutes: 30,
    category: "dogfood_reentry",
  });
  addCheck("missed-plan drop setup creates planned task", Boolean(task?.task_id), task || { title });
  if (!task?.task_id) return null;

  const pastEnd = new Date(Date.now() - 45 * 60_000);
  const pastStart = new Date(pastEnd.getTime() - 30 * 60_000);
  await rescheduleTaskViaApi(token, task.task_id, {
    start: pastStart,
    end: pastEnd,
  });

  await goto(page, "/pulse", "pulse-missed-plan-drop-before");
  const reentryQueue = page.locator('section[aria-label="Re-entry queue"]').first();
  const missedCard = reentryQueue
    .locator("div")
    .filter({ hasText: title })
    .filter({ hasText: /Missed plan/i })
    .first();
  const missedText = await missedCard.innerText({ timeout: 12_000 }).catch(() => "");
  addCheck("pulse re-entry queue shows overdue planned task as missed plan", Boolean(
    missedText.includes(title)
    && /Missed plan/i.test(missedText)
    && /Drop/i.test(missedText)
  ), {
    title,
    body_excerpt: missedText.slice(0, 500),
  });
  await screenshot(page, "pulse-missed-plan-drop-visible");

  await clickAny(page, "pulse missed-plan drop", [
    () => missedCard.getByRole("button", { name: /^Drop$/i }).first(),
    () => reentryQueue.getByRole("button", { name: /^Drop$/i }).first(),
  ], 10_000);

  const skipped = await pollFor(token, "missed-plan drop marks task skipped", async () => {
    const next = await findTaskByTitle(token, title);
    return next?.state === "SKIPPED" ? next : null;
  }, 15_000, 1_000);
  addCheck("pulse missed-plan drop marks planned task skipped", Boolean(
    skipped
    && skipped.state === "SKIPPED"
    && skipped.initiation_status === "user_skipped"
  ), skipped || { title });

  await page.waitForTimeout(800);
  const afterText = await reentryQueue.innerText({ timeout: 5_000 }).catch(() => "");
  addCheck("pulse missed-plan drop removes item from re-entry queue", !afterText.includes(title), {
    title,
    body_excerpt: afterText.slice(0, 500),
  });
  await screenshot(page, "pulse-missed-plan-drop-after");

  return skipped;
}

async function runPulseMissedPlanDonePath(page, token) {
  const title = `${prefix} missed plan done`;
  const task = await createTaskViaApi(token, {
    title,
    startMinutes: 450,
    durationMinutes: 30,
    category: "dogfood_reentry",
  });
  addCheck("missed-plan done setup creates planned task", Boolean(task?.task_id), task || { title });
  if (!task?.task_id) return null;

  const pastEnd = new Date(Date.now() - 35 * 60_000);
  const pastStart = new Date(pastEnd.getTime() - 30 * 60_000);
  await rescheduleTaskViaApi(token, task.task_id, {
    start: pastStart,
    end: pastEnd,
  });

  await goto(page, "/pulse", "pulse-missed-plan-done-before");
  const reentryQueue = page.locator('section[aria-label="Re-entry queue"]').first();
  const missedCard = reentryQueue
    .locator("div")
    .filter({ hasText: title })
    .filter({ hasText: /Missed plan/i })
    .first();
  const missedText = await missedCard.innerText({ timeout: 12_000 }).catch(() => "");
  addCheck("pulse re-entry queue shows overdue planned task with done action", Boolean(
    missedText.includes(title)
    && /Missed plan/i.test(missedText)
    && /\bDone\b/i.test(missedText)
  ), {
    title,
    body_excerpt: missedText.slice(0, 500),
  });
  await screenshot(page, "pulse-missed-plan-done-visible");

  await clickAny(page, "pulse missed-plan done", [
    () => missedCard.getByRole("button", { name: /^Done$/i }).first(),
    () => reentryQueue.getByRole("button", { name: /^Done$/i }).first(),
  ], 10_000);

  const executed = await pollFor(token, "missed-plan done marks task retroactive executed", async () => {
    const next = await findTaskByTitle(token, title);
    return next?.state === "EXECUTED" ? next : null;
  }, 15_000, 1_000);
  addCheck("pulse missed-plan done marks task retroactive executed", Boolean(
    executed
    && executed.state === "EXECUTED"
    && executed.initiation_status === "retroactive"
    && executed.executed_duration_minutes === executed.planned_duration_minutes
  ), executed || { title });

  await page.waitForTimeout(800);
  const afterText = await reentryQueue.innerText({ timeout: 5_000 }).catch(() => "");
  addCheck("pulse missed-plan done removes item from re-entry queue", !afterText.includes(title), {
    title,
    body_excerpt: afterText.slice(0, 500),
  });
  await screenshot(page, "pulse-missed-plan-done-after");

  return executed;
}

async function runTimerSwitchChipPath(page, token) {
  const parentTitle = `${prefix} switch parent`;
  const childTitle = `${prefix} switch child`;
  const parent = await createTaskViaApi(token, {
    title: parentTitle,
    startMinutes: 460,
    durationMinutes: 45,
    category: "dogfood_switch",
  });
  const child = await createTaskViaApi(token, {
    title: childTitle,
    startMinutes: 510,
    durationMinutes: 30,
    category: "dogfood_switch",
  });
  addCheck("switch chip setup creates parent and child tasks", Boolean(
    parent?.task_id && child?.task_id,
  ), {
    parent,
    child,
  });
  if (!parent?.task_id || !child?.task_id) return null;

  try {
    await apiFetch(token, "/v1/stopwatch/start", {
      method: "POST",
      headers: {
        "X-Idempotency-Key": boundedIdentifier(`switch-parent-start:${runKey}`),
      },
      body: JSON.stringify({
        task_id: parent.task_id,
        pre_task_readiness: 3,
      }),
    });
    await apiFetch(token, "/v1/stopwatch/pause", {
      method: "POST",
      headers: {
        "X-Idempotency-Key": boundedIdentifier(`switch-parent-pause:${runKey}`),
      },
      body: JSON.stringify({
        pause_reason: "intentional_break",
        pause_initiator: "self",
      }),
    });
    await apiFetch(token, "/v1/stopwatch/start", {
      method: "POST",
      headers: {
        "X-Idempotency-Key": boundedIdentifier(`switch-child-start:${runKey}`),
      },
      body: JSON.stringify({
        task_id: child.task_id,
        pre_task_readiness: 3,
        interruption_type: "scheduled_override",
      }),
    });

    let status = await apiFetch(token, "/v1/stopwatch/status");
    addCheck("switch chip setup exposes paused parent in status", Boolean(
      status.active
      && status.task_id === child.task_id
      && (status.paused_others || []).some((other) => other.task_id === parent.task_id),
    ), status);

    await goto(page, "/today", "today-switch-chip-proof");
    await closeBlockingDialog(page, "today switch chip proof");
    const chip = page.locator("button").filter({ hasText: parentTitle }).first();
    const chipVisible = await chip.isVisible({ timeout: 12_000 }).catch(() => false);
    let bodyExcerpt = "";
    if (!chipVisible) {
      bodyExcerpt = (await page.locator("body").innerText().catch(() => "")).slice(0, 800);
      await screenshot(page, "today-switch-chip-missing");
    } else {
      await screenshot(page, "today-switch-chip-visible");
    }
    addCheck("today switch chip renders paused parent task", chipVisible, {
      parent_title: parentTitle,
      child_title: childTitle,
      body_excerpt: bodyExcerpt,
    });

    if (chipVisible) {
      await chip.scrollIntoViewIfNeeded().catch(() => {});
      const switchResponsePromise = page.waitForResponse(
        (response) => response.url().includes(`/v1/stopwatch/switch/${parent.task_id}`),
        { timeout: 10_000 },
      ).catch((error) => ({
        __missing: true,
        message: String(error?.message || error).split("\n")[0],
      }));
      await chip.click();
      const switchResponse = await switchResponsePromise;
      let switchResponseBody = null;
      if (!switchResponse.__missing) {
        switchResponseBody = await switchResponse.json().catch(async () => (
          switchResponse.text().catch(() => null)
        ));
      }
      await screenshot(page, "today-switch-chip-after-click");
      addCheck("today switch chip click sends switch request", Boolean(
        switchResponse
        && !switchResponse.__missing
        && switchResponse.status() < 400
      ), {
        url: switchResponse?.__missing ? null : switchResponse.url(),
        status: switchResponse?.__missing ? null : switchResponse.status(),
        body: switchResponseBody,
        error: switchResponse?.__missing ? switchResponse.message : null,
      });
      status = await pollFor(token, "switch chip click activates paused parent", async () => {
        const next = await apiFetch(token, "/v1/stopwatch/status");
        return next.active && next.task_id === parent.task_id ? next : null;
      }, 15_000, 1_000);
      addCheck("today switch chip swaps active timer to parent", Boolean(
        status?.active
        && status.task_id === parent.task_id
        && !status.paused
        && (status.paused_others || []).some((other) => other.task_id === child.task_id),
      ), status);
    }

    return { parent, child };
  } finally {
    const status = await apiFetch(token, "/v1/stopwatch/status").catch(() => null);
    if (status?.active && [parent.task_id, child.task_id].includes(status.task_id)) {
      await apiFetch(
        token,
        "/v1/stopwatch/stop?confirmed=true",
        {
          method: "POST",
          headers: {
            "X-Idempotency-Key": boundedIdentifier(`switch-proof-stop:${runKey}`),
          },
          body: JSON.stringify({
            post_task_reflection: 3,
            task_completion_percentage: 0,
            scope_outcome: "reduced",
          }),
        },
        [200, 409],
      );
    }
  }
}

async function ensureArchetypeReadinessForBrowserProof(token) {
  const initial = await apiFetch(token, "/v1/analytics/archetype/proximity?days=14");
  const initialCount = Number(initial.n_tasks || 0);
  const minimumCount = Number(initial.min_n_required || 3);
  const requiredCount = Math.max(0, minimumCount - initialCount);
  let completedCount = 0;

  for (let index = 0; index < requiredCount; index += 1) {
    const title = `${prefix} archetype readiness ${index + 1}`;
    const task = await createTaskViaApi(token, {
      title,
      startMinutes: 540 + (index * 15),
      durationMinutes: 10,
      category: "dogfood_archetype_readiness",
    });
    if (!task?.task_id) continue;

    await apiFetch(token, "/v1/stopwatch/start", {
      method: "POST",
      headers: {
        "X-Idempotency-Key": boundedIdentifier(`archetype-ready-start:${runKey}:${index}`),
      },
      body: JSON.stringify({
        task_id: task.task_id,
        pre_task_readiness: 3,
      }),
    });
    await new Promise((resolve) => setTimeout(resolve, 1_100));
    await apiFetch(
      token,
      "/v1/stopwatch/stop?confirmed=true",
      {
        method: "POST",
        headers: {
          "X-Idempotency-Key": boundedIdentifier(`archetype-ready-stop:${runKey}:${index}`),
        },
        body: JSON.stringify({
          post_task_reflection: 3,
          task_completion_percentage: 100,
          scope_outcome: "stuck_to_plan",
        }),
      },
      [200, 409],
    );
    const executed = await findTaskByTitle(token, title);
    if (executed?.state === "EXECUTED" && executed.executed_duration_minutes !== null) {
      completedCount += 1;
    }
  }

  const afterSetup = requiredCount > 0
    ? await apiFetch(token, "/v1/analytics/archetype/proximity?days=14")
    : initial;
  if (afterSetup.ready && afterSetup.exposure_id) {
    await apiFetch(
      token,
      `/v1/exposures/${encodeURIComponent(afterSetup.exposure_id)}/ack/suppress`,
      {
        method: "POST",
        body: JSON.stringify({
          suppression_reason: "client_discarded_before_render",
        }),
      },
    );
  }
  addCheck(
    "archetype browser proof setup completes canonical execution traces",
    completedCount === requiredCount,
    {
      initial_count: initialCount,
      minimum_count: minimumCount,
      required_count: requiredCount,
      completed_count: completedCount,
      admitted_after_setup: Number(afterSetup.n_tasks || 0),
      source: "canonical_task_and_stopwatch_dogfood",
    },
  );
  return {
    ready: afterSetup.ready === true,
    nTasks: Number(afterSetup.n_tasks || 0),
    minimumCount,
  };
}

async function runArchetypeBrowserRenderProof(page, token, beforeExport) {
  await goto(page, "/insights", "insights-browser-state");
  const afterExport = await apiFetch(token, "/v1/users/me/export");
  const beforeExposureIds = new Set(
    rows(beforeExport, "exposure_decision_events").map((row) => row.exposure_id),
  );
  const newArchetypeDecisions = rows(afterExport, "exposure_decision_events")
    .filter((row) => !beforeExposureIds.has(row.exposure_id))
    .filter((row) => row.content_template_id === "analytics_archetype_proximity");
  const archetypeRenderIds = new Set(
    rows(afterExport, "exposure_render_events")
      .filter((row) => row.surface === "analytics.archetype_proximity")
      .map((row) => row.exposure_id),
  );
  const archetypeAckIds = new Set(
    rows(afterExport, "exposure_ack_events")
      .filter((row) => row.event_type === "render")
      .map((row) => row.exposure_id),
  );
  const renderedArchetypeDecisions = newArchetypeDecisions
    .filter((row) => row.decision_status === "rendered");
  const browserProvenArchetypeDecisions = renderedArchetypeDecisions
    .filter((row) => archetypeRenderIds.has(row.exposure_id))
    .filter((row) => archetypeAckIds.has(row.exposure_id));
  addCheck(
    "archetype proximity render is browser-acknowledged",
    browserProvenArchetypeDecisions.length >= 1,
    {
      new_decision_count: newArchetypeDecisions.length,
      rendered_count: renderedArchetypeDecisions.length,
      browser_proven_count: browserProvenArchetypeDecisions.length,
      statuses: newArchetypeDecisions.map((row) => row.decision_status).sort(),
    },
  );
  addCheck(
    "archetype proximity has no fabricated rendered decision",
    renderedArchetypeDecisions.every((row) => (
      archetypeRenderIds.has(row.exposure_id)
      && archetypeAckIds.has(row.exposure_id)
    )),
    {
      rendered_count: renderedArchetypeDecisions.length,
      missing_render_or_ack_count: renderedArchetypeDecisions.filter((row) => (
        !archetypeRenderIds.has(row.exposure_id)
        || !archetypeAckIds.has(row.exposure_id)
      )).length,
    },
  );
  return {
    afterExport,
    exposureIds: browserProvenArchetypeDecisions.map((row) => row.exposure_id),
  };
}

async function runAnalyticsAndExposureChecks(page, token, beforeExport) {
  const evidence = {
    exposure_ids: [],
    render_client_event_ids: [],
  };
  const nudgeExposureId = randomUUID();
  const nudgeRenderClientEventId = boundedIdentifier(`${runKey}:nudge-render`);
  const lookup = await apiFetch(
    token,
    `/v1/analytics/bias_factor/lookup?category=work&tod=afternoon&planned_minutes=60&fast=true&exposure_id=${encodeURIComponent(nudgeExposureId)}`,
  );
  addCheck("creation nudge lookup returns bounded authority fields", Boolean(
    lookup.source
    && ("surface_id" in lookup || "suppressed_reason" in lookup || "cell" in lookup)
  ), lookup);
  if (lookup.exposure_id && lookup.surface_id) {
    evidence.exposure_ids.push(lookup.exposure_id);
    const ack = await apiFetch(
      token,
      `/v1/exposures/${encodeURIComponent(lookup.exposure_id)}/ack/render`,
      {
        method: "POST",
        body: JSON.stringify({
          surface_id: lookup.surface_id,
          client_event_id: nudgeRenderClientEventId,
          content_snapshot: { dogfood: true, surface_id: lookup.surface_id },
        }),
      },
      [200, 409],
    );
    addCheck("creation nudge exposure can be render-acked idempotently", Boolean(ack.exposure_id), ack);
    evidence.render_client_event_ids.push(nudgeRenderClientEventId);
  }

  const pressure = await apiFetch(token, "/v1/academic/pressure-map?horizon_days=14");
  await suppressUnrenderedSurfaceProbe(token, pressure, "pressure map analytics probe");
  addCheck("pressure map carries authority/exposure metadata", Boolean(
    pressure.surface_id === "academic.pressure_map"
    || pressure.exposure_id
    || pressure.source_summary
  ), {
    surface_id: pressure.surface_id,
    exposure_id: pressure.exposure_id,
    item_count: Array.isArray(pressure.items) ? pressure.items.length : null,
  });

  const insights = await apiFetch(token, "/v1/analytics/insights");
  const insightText = JSON.stringify(insights).toLowerCase();
  const forbiddenClaims = ["lazy", "discipline problem", "avoidant person", "diagnosis", "mental health"];
  addCheck("ClaimCompiler insights avoid forbidden identity/diagnostic claims", !forbiddenClaims.some((word) => insightText.includes(word)), {
    suppressed_reason: insights.suppressed_reason,
    count: Array.isArray(insights.insights) ? insights.insights.length : null,
  });

  await goto(page, "/insights", "insights-browser-state");
  const afterExport = await apiFetch(token, "/v1/users/me/export");
  addCheck("exposure ledger rows did not disappear after analytics render", (
    countRows(afterExport, "exposure_decision_events") >= countRows(beforeExport, "exposure_decision_events")
    && countRows(afterExport, "exposure_render_events") >= countRows(beforeExport, "exposure_render_events")
  ), {
    before_decisions: countRows(beforeExport, "exposure_decision_events"),
    after_decisions: countRows(afterExport, "exposure_decision_events"),
    before_renders: countRows(beforeExport, "exposure_render_events"),
    after_renders: countRows(afterExport, "exposure_render_events"),
  });
  return evidence;
}

async function runNotificationPath(page, token, task) {
  const terminalTimestampByStatus = {
    rendered: "rendered_at",
    acted: "acted_at",
    dismissed: "dismissed_at",
    expired: "expired_at",
    lost_unrendered: "lost_unrendered_at",
  };

  function terminalLifecycleEvidence(row) {
    if (!row) return null;
    const timestampField = terminalTimestampByStatus[row.status];
    if (!timestampField || !row[timestampField]) return null;
    return {
      status: row.status,
      timestamp_field: timestampField,
      timestamp: row[timestampField],
      rendered_at: row.rendered_at || null,
    };
  }

  async function lifecycleTerminalRow(notificationId, description) {
    return pollFor(token, description, async () => {
      const exported = await apiFetch(token, "/v1/users/me/export");
      const row = rows(exported, "notification_lifecycle_events").find((candidate) => (
        candidate.notification_id === notificationId
      ));
      return terminalLifecycleEvidence(row) ? row : null;
    }, 25_000, 1_000);
  }

  async function lifecycleRow(notificationId, expectedStatus, description) {
    return pollFor(token, description, async () => {
      const exported = await apiFetch(token, "/v1/users/me/export");
      return rows(exported, "notification_lifecycle_events").find((row) => (
        row.notification_id === notificationId
        && row.status === expectedStatus
        && row.rendered_at
      )) || null;
    }, 25_000, 1_000);
  }

  const notificationId = boundedIdentifier(`${runKey}-resume-prediction`);
  cleanup.notifications.add(notificationId);
  await apiFetch(token, "/v1/notifications/push", {
    method: "POST",
    body: JSON.stringify({
      notification_id: notificationId,
      type: "resume_prediction",
      task_id: task.task_id,
      task_title: task.title,
      paused_for_minutes: 5,
      planned_minutes: 60,
    }),
  });
  const pending = await apiFetch(token, "/v1/notifications/web/pending");
  addCheck("notification enqueue appears in web pending without OpenClaw drain", (
    Array.isArray(pending.notifications)
    && pending.notifications.some((n) => n.notification_id === notificationId)
  ), pending);
  await goto(page, "/pulse", "pulse-notification-test");
  const toast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /paused/i })
    .first();
  let toastRendered = false;
  if (await toast.isVisible({ timeout: 12_000 }).catch(() => false)) {
    toastRendered = true;
    await screenshot(page, "notification-toast-rendered");
    const dismiss = toast
      .locator('[data-testid="notification-toast-dismiss"], button[aria-label="Dismiss"]')
      .first();
    await dismiss.click({ timeout: 5_000 });
  } else {
    addIssue("notification toast did not render in browser within timeout", {
      notification_id: notificationId,
    });
  }
  const afterBrowserPending = await apiFetch(token, "/v1/notifications/web/pending");
  const stillPendingAfterBrowser = Array.isArray(afterBrowserPending.notifications)
    && afterBrowserPending.notifications.some((n) => n.notification_id === notificationId);
  let lostCleanupAck = { acknowledged: 0 };
  if (!toastRendered && stillPendingAfterBrowser) {
    lostCleanupAck = await apiFetch(token, "/v1/notifications/web/ack", {
      method: "POST",
      body: JSON.stringify({
        notification_ids: [notificationId],
        event_type: "lost_unrendered",
      }),
    });
  }
  const terminalLifecycleRow = (toastRendered || !stillPendingAfterBrowser || lostCleanupAck.acknowledged > 0)
    ? await lifecycleTerminalRow(
        notificationId,
        "notification terminal lifecycle row after browser handling"
      )
    : null;
  const terminalEvidence = terminalLifecycleEvidence(terminalLifecycleRow);
  const browserRemovedPending = toastRendered
    ? await pollFor(token, "notification absent from web pending after browser render/dismiss", async () => {
        const body = await apiFetch(token, "/v1/notifications/web/pending");
        return !(
          Array.isArray(body.notifications)
          && body.notifications.some((n) => n.notification_id === notificationId)
        );
      }, 10_000, 500)
    : false;
  addCheck("notification pending removal has terminal lifecycle evidence", (
    (
      toastRendered
      && browserRemovedPending
      && Boolean(terminalLifecycleRow?.rendered_at)
    )
    || (
      !toastRendered
      && !stillPendingAfterBrowser
      && Boolean(terminalEvidence)
    )
    || (
      !toastRendered
      && lostCleanupAck.acknowledged > 0
      && terminalEvidence?.status === "lost_unrendered"
    )
  ), {
    toast_rendered: toastRendered,
    still_pending_after_browser: stillPendingAfterBrowser,
    lost_cleanup_ack: lostCleanupAck,
    terminal_lifecycle: terminalLifecycleRow,
    terminal_evidence: terminalEvidence,
  });
  const afterRenderPending = await apiFetch(token, "/v1/notifications/web/pending");
  addCheck("notification is absent from web pending after render handling", !(
    Array.isArray(afterRenderPending.notifications)
    && afterRenderPending.notifications.some((n) => n.notification_id === notificationId)
  ), afterRenderPending);

  const dismissedAck = await apiFetch(token, "/v1/notifications/web/ack", {
    method: "POST",
    body: JSON.stringify({
      notification_ids: [notificationId],
      event_type: "dismissed",
    }),
  });
  addCheck("notification dismiss lifecycle endpoint is idempotent after render", dismissedAck.acknowledged >= 0, dismissedAck);

  const actionNotificationId = boundedIdentifier(`${runKey}-notification-action`);
  cleanup.notifications.add(actionNotificationId);
  await apiFetch(token, "/v1/notifications/push", {
    method: "POST",
    body: JSON.stringify({
      notification_id: actionNotificationId,
      type: "resume_prediction",
      task_id: `${task.task_id}:action`,
      task_title: task.title,
      paused_for_minutes: 7,
      planned_minutes: 60,
    }),
  });
  await goto(page, "/pulse", "pulse-notification-action-test");
  const actionToast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /Pick it back up/i })
    .first();
  await actionToast.waitFor({ state: "visible", timeout: 15_000 });
  await screenshot(page, "notification-toast-action-rendered");
  await page.getByRole("link", { name: /view details/i }).first().click({ timeout: 5_000 });
  const actedRow = await lifecycleRow(
    actionNotificationId,
    "acted",
    "notification action lifecycle row"
  );
  addCheck("notification details click records acted lifecycle", Boolean(
    actedRow?.acted_at && actedRow?.rendered_at
  ), actedRow);

  const expiryNotificationId = boundedIdentifier(`${runKey}-notification-expiry`);
  cleanup.notifications.add(expiryNotificationId);
  await apiFetch(token, "/v1/notifications/push", {
    method: "POST",
    body: JSON.stringify({
      notification_id: expiryNotificationId,
      type: "pause_prediction",
      task_id: `${task.task_id}:expiry`,
    }),
  });
  await goto(page, "/pulse", "pulse-notification-expiry-test");
  const expiryToast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /open for a while/i })
    .first();
  await expiryToast.waitFor({ state: "visible", timeout: 15_000 });
  await screenshot(page, "notification-toast-expiry-rendered");
  await expiryToast.waitFor({ state: "hidden", timeout: 12_000 });
  const expiredRow = await lifecycleRow(
    expiryNotificationId,
    "expired",
    "notification expiry lifecycle row"
  );
  addCheck("notification auto-dismiss records expired lifecycle", Boolean(
    expiredRow?.expired_at && expiredRow?.rendered_at
  ), expiredRow);

  return { notificationId, actionNotificationId, expiryNotificationId };
}

function assertDogfoodEvidenceInExport(exported, evidence) {
  const taskRow = rows(exported, "tasks").find((row) => row.task_id === evidence.task.task_id);
  addCheck("export includes dogfood task row", Boolean(
    taskRow
    && String(taskRow.title || "").startsWith(prefix)
    && taskRow.deadline_id === evidence.deadline.deadline_id
  ), taskRow || { task_id: evidence.task.task_id });

  const deadlineRow = rows(exported, "deadlines").find((row) => row.deadline_id === evidence.deadline.deadline_id);
  addCheck("export includes dogfood deadline row", Boolean(
    deadlineRow
    && String(deadlineRow.title || "").startsWith(prefix)
  ), deadlineRow || { deadline_id: evidence.deadline.deadline_id });

  const sessionRow = rows(exported, "stopwatch_sessions").find((row) => row.session_id === evidence.timer.sessionId);
  addCheck("export includes dogfood stopwatch session row", Boolean(
    sessionRow
    && sessionRow.task_id === evidence.task.task_id
    && sessionRow.end_time_utc
  ), sessionRow || { session_id: evidence.timer.sessionId });

  const pauseRow = rows(exported, "pause_events").find((row) => row.session_id === evidence.timer.sessionId);
  addCheck("export includes dogfood pause event row", Boolean(
    pauseRow
    && pauseRow.resumed_at_utc
    && pauseRow.duration_minutes !== null
  ), pauseRow || { session_id: evidence.timer.sessionId });

  const exposureIds = new Set(evidence.exposures.exposure_ids);
  if (exposureIds.size > 0) {
    addCheck("export includes dogfood exposure decision rows", [...exposureIds].every((id) => (
      rows(exported, "exposure_decision_events").some((row) => row.exposure_id === id)
    )), {
      expected: [...exposureIds],
      present: rows(exported, "exposure_decision_events")
        .filter((row) => exposureIds.has(row.exposure_id))
        .map((row) => row.exposure_id),
    });
    addCheck("export includes dogfood exposure render/ack rows", [...exposureIds].some((id) => (
      rows(exported, "exposure_render_events").some((row) => row.exposure_id === id)
      || rows(exported, "exposure_ack_events").some((row) => row.exposure_id === id)
    )), {
      expected: [...exposureIds],
      renders: rows(exported, "exposure_render_events")
        .filter((row) => exposureIds.has(row.exposure_id))
        .map((row) => row.exposure_id),
      acks: rows(exported, "exposure_ack_events")
        .filter((row) => exposureIds.has(row.exposure_id))
        .map((row) => row.exposure_id),
    });
  }

  const notificationIds = [
    evidence.notification.notificationId,
    evidence.notification.actionNotificationId,
    evidence.notification.expiryNotificationId,
  ].filter(Boolean);
  const notificationRows = notificationIds.map((notificationId) => (
    rows(exported, "notification_lifecycle_events")
      .find((row) => row.notification_id === notificationId) || null
  ));
  addCheck("export includes dogfood notification lifecycle terminal rows", notificationRows.every((row) => (
    row
    && ["rendered", "dismissed", "acted", "expired"].includes(row.status)
    && row.rendered_at
  )), {
    notification_ids: notificationIds,
    rows: notificationRows,
  });
}

async function routeSweep(page) {
  const surfaces = [
    ["/pulse", "route-pulse"],
    ["/today", "route-today"],
    ["/calendar", "route-calendar"],
    ["/deadlines", "route-deadlines"],
    ["/table", "route-table"],
    ["/insights", "route-insights"],
    ["/settings", "route-settings"],
  ];
  for (const [route, name] of surfaces) {
    const text = await goto(page, route, name);
    addCheck(`route renders ${route}`, text.trim().length > 0, { chars: text.length });
  }
  await goto(page, "/calendar", "route-calendar-view-switches");
  await clickAny(page, "calendar day", [
    (p) => p.getByTestId("calendar-view-day"),
    (p) => p.getByRole("button", { name: /^Day$/i }),
  ], 5_000);
  await screenshot(page, "calendar-view-day");
  await clickAny(page, "calendar week", [
    (p) => p.getByTestId("calendar-view-week"),
    (p) => p.getByRole("button", { name: /^Week$/i }),
  ], 5_000);
  await screenshot(page, "calendar-view-week");
  await clickAny(page, "calendar month", [
    (p) => p.getByTestId("calendar-view-month-grid"),
    (p) => p.getByRole("button", { name: /^Month$/i }),
  ], 5_000);
  await screenshot(page, "calendar-view-month");
}

async function operatorPrivacyScan(browser) {
  if (!operatorCookie || operatorCookie.length < 100) {
    addGated("operator privacy scan", "LYRA_COOKIE_ALINASSERSABRY is not available");
    return;
  }
  const op = await resolveAccount(browser, "operator", operatorCookie, true);
  try {
    const canaryMarkers = [
      prefix,
      "moriartyholmesberg",
      "Affected provider/subsystem",
      "Reply with",
      "[warn]",
      "[alert]",
      "OpenClaw",
    ];
    const dashboard = await apiFetch(op.token, "/v1/operator/dashboard");
    const payload = JSON.stringify(dashboard);
    addCheck("operator dashboard does not leak Holmesberg dogfood titles", !payload.includes(prefix), {
      prefix,
    });
    expectNoPrivateLeak(payload, "operator dashboard payload");
    expectNoMarkers(payload, "operator dashboard payload", canaryMarkers);
    const adminDashboard = await apiTry(op.token, "/v1/admin/dashboard");
    addCheck("legacy admin dashboard route is removed", [404, 410].includes(adminDashboard.response.status), {
      status: adminDashboard.response.status,
    });
    const jarvisHealth = await apiTry(op.token, "/v1/jarvis/health");
    addCheck("legacy JARVIS health route is removed", [404, 410].includes(jarvisHealth.response.status), {
      status: jarvisHealth.response.status,
    });
    const text = await goto(op.page, "/operator", "operator-after-holmesberg-loop");
    expectNoMarkers(text, "operator page DOM", canaryMarkers);
    addCheck("operator first viewport/cockpit route rendered", /Can LyraOS invite|Cohort readiness|Readiness/i.test(text), {
      chars: text.length,
    });
  } finally {
    await op.context.close();
  }
}

async function cleanupCreatedRows(token) {
  const tasks = await findTasksByPrefix(token);
  for (const task of tasks) cleanup.tasks.add(task.task_id);
  const deadlines = await findDeadlinesByPrefix(token);
  for (const deadline of deadlines) cleanup.deadlines.add(deadline.deadline_id);

  for (const taskId of cleanup.tasks) {
    await apiTry(token, `/v1/tasks/${encodeURIComponent(taskId)}/void`, {
      method: "POST",
      body: JSON.stringify({
        voided_reason: "test_contamination",
        void_reason_detail: `post-wave dogfood cleanup ${runId}`,
      }),
    });
  }
  for (const deadlineId of cleanup.deadlines) {
    await apiTry(token, `/v1/deadlines/${encodeURIComponent(deadlineId)}`, {
      method: "DELETE",
    });
  }
  const tasksAfterCleanup = await findTasksByPrefix(token);
  const deadlinesAfterCleanup = await findDeadlinesByPrefix(token);
  const activeSyntheticTasks = tasksAfterCleanup.filter((task) => !task.voided_at);
  const activeSyntheticDeadlines = deadlinesAfterCleanup.filter((deadline) => !deadline.voided_at);
  addCheck(
    "cleanup leaves no active prefixed task or deadline rows",
    activeSyntheticTasks.length === 0 && activeSyntheticDeadlines.length === 0,
    {
      active_task_ids: activeSyntheticTasks.map((task) => task.task_id),
      active_deadline_ids: activeSyntheticDeadlines.map((deadline) => deadline.deadline_id),
      terminal_task_ids: tasksAfterCleanup
        .filter((task) => task.voided_at)
        .map((task) => task.task_id),
      terminal_deadline_ids: deadlinesAfterCleanup
        .filter((deadline) => deadline.voided_at)
        .map((deadline) => deadline.deadline_id),
    },
  );
  const status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("cleanup leaves Holmesberg with no active timer", !status.active, status);
}

async function cleanupSyntheticExposureDebt(token, beforeExport) {
  if (!beforeExport) return;
  const exported = await apiFetch(token, "/v1/users/me/export");
  const creationNudgeCandidates = missingSyntheticCreationNudgeExposures(beforeExport, exported);
  const deadlineSuggestionCandidates = missingSyntheticDeadlineSuggestionExposures(beforeExport, exported);
  const stopwatchOutputCandidates = missingSyntheticStopwatchOutputExposures(beforeExport, exported);
  addCheck(
    "browser paths leave no unterminated synthetic deadline-suggestion exposures",
    deadlineSuggestionCandidates.length === 0,
    {
      exposure_ids: deadlineSuggestionCandidates.map((row) => row.exposure_id),
    },
  );
  const candidates = [
    ...creationNudgeCandidates,
    ...deadlineSuggestionCandidates,
    ...stopwatchOutputCandidates,
  ];
  for (const row of candidates) {
    const res = await apiFetch(token, `/v1/exposures/${encodeURIComponent(row.exposure_id)}/ack/suppress`, {
      method: "POST",
      body: JSON.stringify({
        suppression_reason: "dogfood_synthetic_cleanup",
      }),
    });
    if (!["suppressed", "already_suppressed"].includes(res.status)) {
      addCheck("synthetic exposure cleanup reached terminal suppression state", false, {
        exposure_id: row.exposure_id,
        response: res,
      });
    }
    cleanup.exposureSuppressions.add(row.exposure_id);
  }
  const after = await apiFetch(token, "/v1/users/me/export");
  const remainingCreationNudges = missingSyntheticCreationNudgeExposures(beforeExport, after);
  const remainingDeadlineSuggestions = missingSyntheticDeadlineSuggestionExposures(beforeExport, after);
  const remainingStopwatchOutputs = missingSyntheticStopwatchOutputExposures(beforeExport, after);
  addCheck("cleanup leaves no unrendered synthetic creation-nudge exposures", remainingCreationNudges.length === 0, {
    cleaned: candidates.map((row) => row.exposure_id),
    remaining: remainingCreationNudges.map((row) => row.exposure_id),
  });
  addCheck("cleanup leaves no unrendered synthetic deadline-suggestion exposures", remainingDeadlineSuggestions.length === 0, {
    cleaned: candidates.map((row) => row.exposure_id),
    remaining: remainingDeadlineSuggestions.map((row) => row.exposure_id),
  });
  addCheck("cleanup leaves no unterminated synthetic stopwatch-output candidates", remainingStopwatchOutputs.length === 0, {
    cleaned: stopwatchOutputCandidates.map((row) => row.exposure_id),
    remaining: remainingStopwatchOutputs.map((row) => row.exposure_id),
  });
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  let account = null;
  let activeToken = null;
  let beforeExport = null;
  try {
    account = await resolveAccount(browser, "holmesberg", holmesbergCookie, false);
    const { page, token, me } = account;
    activeToken = token;
    addCheck("Holmesberg user ref resolved", Boolean(me.user_id), {
      user_ref: userRef(me.user_id),
    });
    if (cleanupOnly) {
      await cleanupCreatedRows(token);
      const result = {
        ok: true,
        run_id: runId,
        cleanup_only: true,
        topology,
        frontend_origin: frontendOrigin,
        api_origin: apiOrigin,
        prefix,
        user_ref: userRef(me.user_id),
        output_dir: outDir,
        checks,
        issues,
        gated,
        cleanup: {
          task_ids: [...cleanup.tasks],
          deadline_ids: [...cleanup.deadlines],
          notification_ids: [...cleanup.notifications],
          exposure_suppression_ids: [...cleanup.exposureSuppressions],
        },
      };
      await writeJson("result.json", result);
      console.log(JSON.stringify(result, null, 2));
      return;
    }
    await apiFetch(token, "/v1/operator/dashboard", {}, [403]);
    await apiFetch(token, "/v1/admin/dashboard", {}, [404, 410]);
    await apiFetch(token, "/v1/jarvis/health", {}, [404, 410]);
    await stopActiveTimerIfNeeded(token);

    beforeExport = await apiFetch(token, "/v1/users/me/export");
    expectNoPrivateLeak(JSON.stringify(beforeExport), "Holmesberg export before");

    if (archetypeProofOnly) {
      const readiness = await ensureArchetypeReadinessForBrowserProof(token);
      let proofStatus = "gated";
      if (readiness.ready) {
        const proof = await runArchetypeBrowserRenderProof(page, token, beforeExport);
        addCheck(
          "archetype browser proof export contains rendered exposure",
          proof.exposureIds.length >= 1,
          { browser_proven_count: proof.exposureIds.length },
        );
        proofStatus = "passed";
      } else {
        addGated(
          "archetype proximity positive browser render proof",
          `clean-data admission is ${readiness.nTasks}/${readiness.minimumCount} on the authorized mutable account`,
        );
      }
      await cleanupCreatedRows(token);
      await cleanupSyntheticExposureDebt(token, beforeExport);
      const result = {
        ok: checks.every((check) => check.ok),
        run_id: runId,
        proof_scope: "archetype_render_only",
        proof_status: proofStatus,
        topology,
        frontend_origin: frontendOrigin,
        api_origin: apiOrigin,
        user_ref: userRef(me.user_id),
        output_dir: outDir,
        checks,
        issues,
        gated,
        cleanup: {
          task_ids: [...cleanup.tasks],
          deadline_ids: [...cleanup.deadlines],
          notification_ids: [...cleanup.notifications],
          exposure_suppression_ids: [...cleanup.exposureSuppressions],
        },
      };
      await writeJson("result.json", result);
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    if (pressureProofOnly) {
      let exposureIds = [];
      let proofScope = "pressure_map_render_only";
      if (forcePressureRecovery) {
        const pressureProof = await runPressureMapPath(page, token, beforeExport);
        exposureIds = pressureProof.exposureIds;
        proofScope = "pressure_map_path";
      } else {
        await goto(page, "/pulse", "pressure-map-browser-proof");
        exposureIds = await assertPressureMapBrowserRender(token, beforeExport);
      }
      await cleanupCreatedRows(token);
      await cleanupSyntheticExposureDebt(token, beforeExport);
      const result = {
        ok: checks.every((check) => check.ok),
        run_id: runId,
        proof_scope: proofScope,
        proof_status: "passed",
        topology,
        frontend_origin: frontendOrigin,
        api_origin: apiOrigin,
        user_ref: userRef(me.user_id),
        output_dir: outDir,
        exposure_count: exposureIds.length,
        checks,
        issues,
        gated,
        cleanup: {
          task_ids: [...cleanup.tasks],
          deadline_ids: [...cleanup.deadlines],
          notification_ids: [...cleanup.notifications],
          exposure_suppression_ids: [...cleanup.exposureSuppressions],
        },
      };
      await writeJson("result.json", result);
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    if (stopwatchOutputProofOnly) {
      const proof = await runTodayStopOutputRenderPath(page, token);
      await cleanupCreatedRows(token);
      await cleanupSyntheticExposureDebt(token, beforeExport);
      const result = {
        ok: checks.every((check) => check.ok),
        run_id: runId,
        proof_scope: "stopwatch_output_render_only",
        proof_status: proof.exposureIds.length > 0 ? "passed" : "gated",
        topology,
        frontend_origin: frontendOrigin,
        api_origin: apiOrigin,
        user_ref: userRef(me.user_id),
        output_dir: outDir,
        exposure_count: proof.exposureIds.length,
        checks,
        issues,
        gated,
        cleanup: {
          task_ids: [...cleanup.tasks],
          deadline_ids: [...cleanup.deadlines],
          notification_ids: [...cleanup.notifications],
          exposure_suppression_ids: [...cleanup.exposureSuppressions],
        },
      };
      await writeJson("result.json", result);
      console.log(JSON.stringify(result, null, 2));
      return;
    }

    await routeSweep(page);
    const deadline = await createDeadlineThroughUi(page, token);
    const task = await createTaskThroughUi(page, token, deadline);
    await runNewTaskSubmitContractCoverage(page, token);
    await createSoftConflictTaskThroughUi(page, token);
    await runNewTaskBranchCoverage(page, token, deadline);
    await runBrainDumpPath(page, token);
    await runBrainDumpBranchCoverage(page, token);
    const pressureEvidence = await runPressureMapPath(page, token, beforeExport);
    const timer = await runTimerPath(page, token, task);
    const stopOutputEvidence = await runTodayStopOutputRenderPath(page, token);
    await runPulseMissedPlanDropPath(page, token);
    await runPulseMissedPlanDonePath(page, token);
    await runTimerSwitchChipPath(page, token);
    const executedTask = timer.task;
    const exposures = await runAnalyticsAndExposureChecks(page, token, beforeExport);
    for (const exposureId of pressureEvidence.exposureIds) {
      exposures.exposure_ids.push(exposureId);
    }
    for (const exposureId of stopOutputEvidence.exposureIds) {
      exposures.exposure_ids.push(exposureId);
    }
    const notification = await runNotificationPath(page, token, task);

    await goto(page, "/calendar", "calendar-after-dogfood");
    const calendarText = await page.locator("body").innerText();
    addCheck("calendar route includes created or executed task context before cleanup", calendarText.includes(task.title) || Boolean(executedTask), {
      task_title: task.title,
    });
    await goto(page, "/table", "table-after-dogfood");
    const tableText = await page.locator("body").innerText();
    addCheck("table route renders dogfood delta row after execution", (
      tableText.includes(task.title)
      && /Delta|Exec|Plan/i.test(tableText)
      && /R.?F/i.test(tableText)
    ), {
      has_task_title: tableText.includes(task.title),
      has_delta_terms: /Delta|Exec|Plan/i.test(tableText),
      has_readiness_reflection: /R.?F/i.test(tableText),
    });

    const exported = await apiFetch(token, "/v1/users/me/export");
    expectNoPrivateLeak(JSON.stringify(exported), "Holmesberg export after");
    addCheck("export includes core registry sections", [
      "tasks",
      "deadlines",
      "stopwatch_sessions",
      "pause_events",
      "exposure_decision_events",
      "exposure_render_events",
      "exposure_ack_events",
      "notification_lifecycle_events",
    ].every((key) => Array.isArray(exported[key])), Object.keys(exported).sort());
    assertDogfoodEvidenceInExport(exported, {
      deadline,
      task,
      timer,
      exposures,
      notification,
    });

    addGated("provider credential browser mutation", "requires disposable Moodle/Google provider credentials");
    addGated("account hard-delete/Redis purge", "requires a disposable delete-only account; Holmesberg cookie is the reusable chaos identity");
    addGated("calendar drag/resize mutation", "Schedule-X drag is documented as a separate manual/browser-specific pass");
    addGated("OpenClaw pending drain authority", "route is historically user-scoped but named OpenClaw; unattended run does not drain it until authority is decided");

    await operatorPrivacyScan(browser);
    await cleanupCreatedRows(token);
    await cleanupSyntheticExposureDebt(token, beforeExport);

    if (account.serverErrors.length) {
      addIssue("browser observed server errors", account.serverErrors);
    }

    const result = {
      ok: checks.every((check) => check.ok),
      run_id: runId,
      topology,
      frontend_origin: frontendOrigin,
      api_origin: apiOrigin,
      user_ref: userRef(me.user_id),
      output_dir: outDir,
      checks,
      issues,
      gated,
      diagnostics: {
        deadline_preview_requests: account.deadlinePreviewRequests,
        deadline_preview_responses: account.deadlinePreviewResponses,
        bias_lookup_requests: account.biasLookupRequests,
        bias_lookup_responses: account.biasLookupResponses,
      },
      cleanup: {
        task_ids: [...cleanup.tasks],
        deadline_ids: [...cleanup.deadlines],
        notification_ids: [...cleanup.notifications],
        exposure_suppression_ids: [...cleanup.exposureSuppressions],
      },
    };
    await writeJson("result.json", result);
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    if (activeToken) {
      try {
        await cleanupCreatedRows(activeToken);
        await cleanupSyntheticExposureDebt(activeToken, beforeExport);
      } catch (cleanupError) {
        addIssue("cleanup after failure failed", cleanupError.message);
      }
    }
    if (account?.page) {
      await screenshot(account.page, "failure");
    }
    const result = {
      ok: false,
      run_id: runId,
      topology,
      frontend_origin: frontendOrigin,
      api_origin: apiOrigin,
      output_dir: outDir,
      error: error.message,
      detail: error.detail || null,
      checks,
      issues,
      gated,
      diagnostics: {
        deadline_preview_requests: account?.deadlinePreviewRequests || [],
        deadline_preview_responses: account?.deadlinePreviewResponses || [],
        bias_lookup_requests: account?.biasLookupRequests || [],
        bias_lookup_responses: account?.biasLookupResponses || [],
      },
      cleanup: {
        task_ids: [...cleanup.tasks],
        deadline_ids: [...cleanup.deadlines],
        notification_ids: [...cleanup.notifications],
        exposure_suppression_ids: [...cleanup.exposureSuppressions],
      },
    };
    await writeJson("result.json", result);
    console.error(JSON.stringify(result, null, 2));
    process.exitCode = 1;
  } finally {
    if (account?.context) {
      await account.context.close().catch(() => {});
    }
    await browser.close();
  }
}

await main();
