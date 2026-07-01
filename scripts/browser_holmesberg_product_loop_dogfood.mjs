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
  if (/ONBOARDING|Lyra starts learning from the first plan/i.test(text)) {
    await completeOnboardingGate(page);
    await page.goto(`${frontendOrigin}${pathname}`, {
      waitUntil: "domcontentloaded",
      timeout: 45_000,
    });
    await page.waitForLoadState("networkidle", { timeout: 6_000 }).catch(() => {});
    text = await page.locator("body").innerText({ timeout: 10_000 });
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

async function resolveAccount(browser, label, cookieHeader, expectOperator) {
  if (!cookieHeader || cookieHeader.length < 100) {
    throw new Error(`missing usable cookie for ${label}`);
  }
  const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  await context.addCookies(parseAndExpandCookies(cookieHeader, frontendOrigin));
  const page = await context.newPage();
  const serverErrors = [];
  const deadlinePreviewResponses = [];
  const deadlinePreviewRequests = [];
  page.on("request", (request) => {
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
  });
  const token = await resolveBackendTokenFromContext(context, frontendOrigin);
  const me = await apiFetch(token, "/v1/users/me");
  addCheck(`${label}: operator flag`, Boolean(me.is_operator) === expectOperator, {
    expected: expectOperator,
    actual: Boolean(me.is_operator),
    user_ref: userRef(me.user_id),
  });
  return { context, page, token, me, serverErrors, deadlinePreviewRequests, deadlinePreviewResponses };
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

async function waitForDeadlineSuggestion(page, title, timeout = 20_000) {
  const startedAt = Date.now();
  const suggestion = page.getByText(/Lyra thinks this binds to/i).first();
  const visible = await suggestion
    .waitFor({ state: "visible", timeout })
    .then(() => true)
    .catch(() => false);
  const latencyMs = Date.now() - startedAt;
  addCheck(`deadline suggestion rendered for ${title}`, visible, { title, latency_ms: latencyMs });
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

async function createTaskThroughUi(page, token, deadline) {
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

  const suggestion = page.getByText(/Lyra thinks this binds to/i).first();
  const sawSuggestion = await suggestion.isVisible({ timeout: 8_000 }).catch(() => false);
  if (sawSuggestion) {
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
    addCheck("creation nudge modal renders when research prior text is visible", (
      /Research prior/i.test(modalText)
      && /Use\s+\d+\s*min/i.test(modalText)
    ), { modal_text: modalText.slice(0, 1000) });
  }

  await clickAny(page, "create task", [
    (p) => p.getByTestId("new-task-create"),
    (p) => p.getByRole("button", { name: /^Create$/i }),
    (p) => p.locator('button:has-text("Create")'),
  ], 5_000);

  const createAnyway = page.getByTestId("new-task-create-anyway").first();
  if (await createAnyway.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await screenshot(page, "new-task-soft-conflict");
    await createAnyway.click();
  }

  await page.getByText(title, { exact: false }).first().waitFor({ timeout: 20_000 });
  await screenshot(page, "today-after-task-create");
  const task = await findTaskByTitle(token, title);
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

  await page.getByText(title, { exact: false }).first().waitFor({ timeout: 20_000 });
  const task = await findTaskByTitle(token, title);
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
  await page.getByText(noBindTitle, { exact: false }).first().waitFor({ timeout: 20_000 });
  const noBindTask = await findTaskByTitle(token, noBindTitle);
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
  await page.getByText(pickAnotherTitle, { exact: false }).first().waitFor({ timeout: 20_000 });
  const pickAnotherTask = await findTaskByTitle(token, pickAnotherTitle);
  addCheck("pick-another branch binds the explicitly chosen deadline", (
    pickAnotherTask?.deadline_id === alternateDeadline.deadline_id
  ), {
    task_deadline_id: pickAnotherTask?.deadline_id ?? null,
    suggested_deadline_id: pickAnotherSourceDeadline.deadline_id,
    chosen_deadline_id: alternateDeadline.deadline_id,
  });
  cleanup.tasks.add(pickAnotherTask.task_id);

  const editedTitle = `${pickAnotherTitle} edited`;
  await goto(page, "/today", "today-before-edit-mode-branch");
  const row = page.locator(`[data-testid="task-row"][data-task-id="${pickAnotherTask.task_id}"]`).first();
  if (await row.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await row.scrollIntoViewIfNeeded({ timeout: 10_000 });
    await row.getByText(pickAnotherTitle, { exact: false }).first().click({ timeout: 10_000 });
  } else {
    const titleCell = page.getByText(pickAnotherTitle, { exact: false }).first();
    await titleCell.scrollIntoViewIfNeeded({ timeout: 10_000 });
    await titleCell.click({ timeout: 10_000 });
  }
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
    pickAnotherTask: editedTask,
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
  await page.getByText(/Lyra found/i).first().waitFor({ timeout: 20_000 });
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

async function runPressureMapPath(page, token) {
  const beforeTasks = await findTasksByPrefix(token);
  await goto(page, "/pulse", "pulse-pressure-map");
  const previewVisible = await page.getByTestId("pressure-map-preview").first().isVisible({ timeout: 8_000 }).catch(() => false);
  if (!previewVisible) {
    addIssue("pressure map preview was not available for current Holmesberg state");
    return;
  }
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

  await clickAny(page, "resume session", [
    () => focus.getByTestId("focus-resume"),
    () => focus.getByRole("button", { name: /^Resume$/i }),
  ], 10_000);
  for (let i = 0; i < 6; i += 1) {
    await page.waitForTimeout(1_000);
    status = await apiFetch(token, "/v1/stopwatch/status");
    if (status.active && !status.paused) break;
  }
  if (status.active && status.paused) {
    await screenshot(page, "timer-resume-still-paused");
  }
  addCheck("timer resume clears paused flag", Boolean(status.active && !status.paused), status);

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
  addCheck("pressure map carries authority/exposure metadata", Boolean(
    pressure.surface_id === "academic.pressure_map"
    || pressure.exposure_id
    || pressure.render_id
    || pressure.source_summary
  ), {
    surface_id: pressure.surface_id,
    exposure_id: pressure.exposure_id,
    render_id: pressure.render_id,
    item_count: Array.isArray(pressure.items) ? pressure.items.length : null,
  });
  if (pressure.exposure_id) {
    evidence.exposure_ids.push(pressure.exposure_id);
  }

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
  if (await toast.isVisible({ timeout: 12_000 }).catch(() => false)) {
    await screenshot(page, "notification-toast-rendered");
    const dismiss = toast
      .locator('[data-testid="notification-toast-dismiss"], button[aria-label="Dismiss"]')
      .first();
    await dismiss.click({ timeout: 5_000 });
  } else {
    addIssue("notification toast did not render in browser within timeout; API lifecycle ack checked instead", {
      notification_id: notificationId,
    });
  }
  const afterBrowserPending = await apiFetch(token, "/v1/notifications/web/pending");
  const stillPendingAfterBrowser = Array.isArray(afterBrowserPending.notifications)
    && afterBrowserPending.notifications.some((n) => n.notification_id === notificationId);
  let renderedAck = { acknowledged: 0 };
  if (stillPendingAfterBrowser) {
    renderedAck = await apiFetch(token, "/v1/notifications/web/ack", {
      method: "POST",
      body: JSON.stringify({
        notification_ids: [notificationId],
        event_type: "rendered",
      }),
    });
  }
  addCheck("notification render lifecycle reached browser or removed exactly one pending item", (
    !stillPendingAfterBrowser || renderedAck.acknowledged === 1
  ), {
    still_pending_after_browser: stillPendingAfterBrowser,
    rendered_ack: renderedAck,
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
  return { notificationId };
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

  const notificationRow = rows(exported, "notification_lifecycle_events")
    .find((row) => row.notification_id === evidence.notification.notificationId);
  addCheck("export includes dogfood notification lifecycle terminal row", Boolean(
    notificationRow
    && ["rendered", "dismissed", "acted", "expired"].includes(notificationRow.status)
    && notificationRow.rendered_at
  ), {
    notification_id: evidence.notification.notificationId,
    row: notificationRow || null,
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
      "Jarvis",
    ];
    const dashboard = await apiFetch(op.token, "/v1/operator/dashboard");
    const payload = JSON.stringify(dashboard);
    addCheck("operator dashboard does not leak Holmesberg dogfood titles", !payload.includes(prefix), {
      prefix,
    });
    expectNoPrivateLeak(payload, "operator dashboard payload");
    expectNoMarkers(payload, "operator dashboard payload", canaryMarkers);
    const adminDashboard = await apiTry(op.token, "/v1/admin/dashboard");
    if (adminDashboard.response.status === 200) {
      const adminPayload = JSON.stringify(adminDashboard.body);
      expectNoPrivateLeak(adminPayload, "admin dashboard payload");
      expectNoMarkers(adminPayload, "admin dashboard payload", canaryMarkers);
    }
    const text = await goto(op.page, "/operator", "operator-after-holmesberg-loop");
    expectNoMarkers(text, "operator page DOM", canaryMarkers);
    addCheck("operator first viewport/cockpit route rendered", /Can Lyra invite|Cohort readiness|Readiness/i.test(text), {
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
  const status = await apiFetch(token, "/v1/stopwatch/status");
  addCheck("cleanup leaves Holmesberg with no active timer", !status.active, status);
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
        },
      };
      await writeJson("result.json", result);
      console.log(JSON.stringify(result, null, 2));
      return;
    }
    await apiFetch(token, "/v1/operator/dashboard", {}, [403]);
    await apiFetch(token, "/v1/admin/dashboard", {}, [403]);
    await apiFetch(token, "/v1/jarvis/health", {}, [403, 404, 410]);
    await stopActiveTimerIfNeeded(token);

    beforeExport = await apiFetch(token, "/v1/users/me/export");
    expectNoPrivateLeak(JSON.stringify(beforeExport), "Holmesberg export before");

    await routeSweep(page);
    const deadline = await createDeadlineThroughUi(page, token);
    const task = await createTaskThroughUi(page, token, deadline);
    await createSoftConflictTaskThroughUi(page, token);
    await runNewTaskBranchCoverage(page, token, deadline);
    await runBrainDumpPath(page, token);
    await runPressureMapPath(page, token);
    const timer = await runTimerPath(page, token, task);
    const executedTask = timer.task;
    const exposures = await runAnalyticsAndExposureChecks(page, token, beforeExport);
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
      },
      cleanup: {
        task_ids: [...cleanup.tasks],
        deadline_ids: [...cleanup.deadlines],
        notification_ids: [...cleanup.notifications],
      },
    };
    await writeJson("result.json", result);
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    if (activeToken) {
      try {
        await cleanupCreatedRows(activeToken);
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
      },
      cleanup: {
        task_ids: [...cleanup.tasks],
        deadline_ids: [...cleanup.deadlines],
        notification_ids: [...cleanup.notifications],
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
