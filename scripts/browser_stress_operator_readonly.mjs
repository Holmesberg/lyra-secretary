#!/usr/bin/env node
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  apiFetch,
  assertCookieHeaderLooksUsable,
  frontendRequire,
  parseAndExpandCookies,
  repoRoot,
  resolveBackendToken,
  userRef,
} from "./browser_auth_helpers.mjs";

const { chromium } = frontendRequire("playwright");

const frontendOrigin = process.env.LYRA_FRONTEND_ORIGIN || "https://lyraos.org";
const apiOrigin = process.env.LYRA_API_ORIGIN || "https://api.lyraos.org";
const cookieHeader = process.env.LYRA_COOKIE_ALINASSERSABRY || "";
const runId = process.env.LYRA_BROWSER_STRESS_RUN_ID || new Date().toISOString().replace(/[:.]/g, "-");
const outDir = path.join(repoRoot, "tmp", `operator-readonly-stress-${runId}`);

const routes = [
  { path: "/pulse", name: "pulse", maxMs: 12_000 },
  { path: "/today", name: "today", maxMs: 12_000 },
  { path: "/calendar", name: "calendar", maxMs: 12_000 },
  { path: "/deadlines", name: "deadlines", maxMs: 12_000 },
  { path: "/table", name: "table", maxMs: 12_000 },
  { path: "/insights", name: "insights", maxMs: 15_000 },
  { path: "/settings", name: "settings", maxMs: 12_000 },
  { path: "/operator", name: "operator", maxMs: 12_000 },
];

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "mobile", width: 390, height: 844 },
];

const forbiddenTextPatterns = [
  /\[calendar\.sync\]/i,
  /Affected user scope/i,
  /Data integrity risk/i,
  /Reply with ['"]?done/i,
  /\b\d+\.\d{4,}\s*min\b/i,
  /provider\/subsystem:/i,
  /Retry behavior:/i,
];

function countExport(body) {
  return {
    tasks: (body.tasks || []).length,
    deadlines: (body.deadlines || []).length,
    stopwatch_sessions: (body.stopwatch_sessions || []).length,
    pause_events: (body.pause_events || []).length,
    feedback: (body.feedback || []).length,
    exposure_logs: (body.exposure_logs || body.exposures || []).length,
    notifications: (body.notifications || body.notification_lifecycle || []).length,
  };
}

function diffCounts(before, after) {
  const diffs = [];
  for (const key of Object.keys({ ...before, ...after })) {
    if ((before[key] || 0) !== (after[key] || 0)) {
      diffs.push({ key, before: before[key] || 0, after: after[key] || 0 });
    }
  }
  return diffs;
}

function isIgnorableRequestFailure(request) {
  const url = request.url();
  const failure = request.failure()?.errorText || "";
  if (url.includes("static.cloudflareinsights.com") || url.includes("/cdn-cgi/rum")) {
    return true;
  }
  if (failure === "net::ERR_ABORTED") {
    return true;
  }
  return false;
}

async function fetchJson(pathname, token) {
  const { response, body } = await apiFetch(apiOrigin, token, pathname);
  return { status: response.status, body };
}

async function checkRoute(page, route, viewport) {
  const result = {
    route: route.path,
    viewport: viewport.name,
    duration_ms: null,
    status: null,
    screenshot: null,
    issues: [],
  };
  const responseErrors = [];
  const requestFailures = [];
  const consoleErrors = [];

  const onResponse = (response) => {
    const url = response.url();
    const status = response.status();
    if (status >= 400 && !url.includes("static.cloudflareinsights.com")) {
      responseErrors.push({ url, status });
    }
  };
  const onRequestFailed = (request) => {
    if (isIgnorableRequestFailure(request)) return;
    requestFailures.push({
      url: request.url(),
      failure: request.failure()?.errorText || "unknown",
    });
  };
  const onConsole = (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    if (text.includes("static.cloudflareinsights.com")) return;
    consoleErrors.push(text.slice(0, 500));
  };

  page.on("response", onResponse);
  page.on("requestfailed", onRequestFailed);
  page.on("console", onConsole);

  const started = Date.now();
  try {
    const response = await page.goto(`${frontendOrigin}${route.path}`, {
      waitUntil: "domcontentloaded",
      timeout: route.maxMs,
    });
    result.status = response?.status() ?? null;
    await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});
    if (route.path === "/operator") {
      await page
        .getByText(/Operator cockpit|Cohort readiness|safe to invite/i)
        .first()
        .waitFor({ timeout: 20_000 })
        .catch(() => {});
    }
    result.duration_ms = Date.now() - started;

    const bodyText = await page.locator("body").innerText({ timeout: 5_000 }).catch(() => "");
    for (const pattern of forbiddenTextPatterns) {
      if (pattern.test(bodyText)) {
        result.issues.push(`forbidden copy matched ${pattern}`);
      }
    }
    if (route.path === "/operator" && !/Operator cockpit|Cohort readiness|safe to invite/i.test(bodyText)) {
      result.issues.push("operator route did not render operator cockpit");
    }
    if (result.duration_ms > route.maxMs) {
      result.issues.push(`route exceeded latency budget ${route.maxMs}ms`);
    }

    const screenshotPath = path.join(outDir, `alinassersabry-${viewport.name}-${route.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.screenshot = path.relative(repoRoot, screenshotPath).replaceAll("\\", "/");
  } catch (error) {
    result.duration_ms = Date.now() - started;
    result.issues.push(`navigation failed: ${error.message}`);
  } finally {
    page.off("response", onResponse);
    page.off("requestfailed", onRequestFailed);
    page.off("console", onConsole);
  }

  if (responseErrors.length) {
    result.issues.push(`HTTP errors: ${JSON.stringify(responseErrors.slice(0, 8))}`);
  }
  if (requestFailures.length) {
    result.issues.push(`request failures: ${JSON.stringify(requestFailures.slice(0, 8))}`);
  }
  if (consoleErrors.length) {
    result.issues.push(`console errors: ${JSON.stringify(consoleErrors.slice(0, 8))}`);
  }
  return result;
}

assertCookieHeaderLooksUsable("LYRA_COOKIE_ALINASSERSABRY", cookieHeader);

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const result = {
  ok: true,
  generated_at: new Date().toISOString(),
  frontendOrigin,
  apiOrigin,
  outDir: path.relative(repoRoot, outDir).replaceAll("\\", "/"),
  user_ref: null,
  is_operator: null,
  before_counts: null,
  after_counts: null,
  count_diffs: [],
  routes: [],
  issues: [],
};

try {
  const context = await browser.newContext({ viewport: viewports[0] });
  await context.addCookies(parseAndExpandCookies(cookieHeader, frontendOrigin));
  const page = await context.newPage();
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  const token = await resolveBackendToken(page);

  const me = await fetchJson("/v1/users/me", token);
  if (me.status !== 200) throw new Error(`users/me failed with ${me.status}`);
  result.user_ref = userRef(me.body.user_id);
  result.is_operator = Boolean(me.body.is_operator);
  if (!result.is_operator) {
    result.issues.push("alinassersabry cookie did not resolve to an operator account");
  }

  const beforeExport = await fetchJson("/v1/users/me/export", token);
  if (beforeExport.status !== 200) throw new Error(`pre export failed with ${beforeExport.status}`);
  result.before_counts = countExport(beforeExport.body || {});

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const route of routes) {
      result.routes.push(await checkRoute(page, route, viewport));
    }
  }

  const afterExport = await fetchJson("/v1/users/me/export", token);
  if (afterExport.status !== 200) throw new Error(`post export failed with ${afterExport.status}`);
  result.after_counts = countExport(afterExport.body || {});
  result.count_diffs = diffCounts(result.before_counts, result.after_counts);
  if (result.count_diffs.length > 0) {
    result.issues.push(`read-only stress changed exported data counts: ${JSON.stringify(result.count_diffs)}`);
  }

  await context.close();
} catch (error) {
  result.issues.push(error.message);
} finally {
  await browser.close();
}

for (const route of result.routes) {
  for (const issue of route.issues || []) {
    result.issues.push(`${route.viewport} ${route.route}: ${issue}`);
  }
}

result.ok = result.issues.length === 0;
await writeFile(path.join(outDir, "result.json"), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
if (!result.ok) process.exitCode = 1;
