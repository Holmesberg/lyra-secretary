#!/usr/bin/env node
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  apiFetch,
  assertCookieHeaderLooksUsable,
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

const frontendOrigin = args.get("frontend") || process.env.LYRA_FRONTEND_ORIGIN || "https://lyraos.org";
const apiOrigin = args.get("api") || process.env.LYRA_API_ORIGIN || "https://api.lyraos.org";
const cookieHeader = process.env.LYRA_COOKIE_ALINASSERSABRY || "";
const runId = args.get("run-id") || process.env.LYRA_BROWSER_STRESS_RUN_ID || new Date().toISOString().replace(/[:.]/g, "-");
const outDir = path.resolve(args.get("out-dir") || path.join(repoRoot, "tmp", `operator-readonly-stress-${runId}`));
const proxyApi = args.get("proxy-api") === "true";
const expectReadinessSplit = args.get("expect-readiness-split") === "true";

const routes = [
  { path: "/operator", name: "operator", targetMs: 12_000, maxMs: 20_000 },
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
  const counts = {};
  const registrySections = Array.isArray(body.registry)
    ? body.registry.map((entry) => entry?.section).filter(Boolean)
    : [];
  const fallbackSections = [
    "tasks",
    "deadlines",
    "deadline_completion_events",
    "task_deadline_outcomes",
    "stopwatch_sessions",
    "task_execution_corrections",
    "pause_events",
    "pause_prediction_logs",
    "resume_prediction_logs",
    "calibration_nudge_events",
    "reflection_view_logs",
    "exposure_decision_events",
    "exposure_render_events",
    "exposure_ack_events",
    "suppression_events",
    "exposure_policy_effect_logs",
    "feedback",
    "external_event_outcomes",
    "notification_lifecycle_events",
    "email_engagement_events",
    "archetype_assignments",
    "jarvis_invocations",
  ];
  for (const section of new Set([...fallbackSections, ...registrySections])) {
    if (Array.isArray(body[section])) {
      counts[section] = body[section].length;
    }
  }
  return counts;
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

function pick(source, keys) {
  const out = {};
  const record = source || {};
  for (const key of keys) {
    out[key] = record[key] ?? null;
  }
  return out;
}

function dashboardReadOnlySnapshot(body) {
  const cleanBasis = body?.measurement_integrity?.clean_trace_ratio_basis || {};
  return {
    cohort_readiness: pick(body?.cohort_readiness, [
      "status",
      "safe_to_invite_more_users",
      "implementation_green",
      "implementation_status",
      "implementation_blockers",
      "cohort_green",
      "cohort_status",
      "cohort_evidence_gaps",
      "controlled_evidence_collection_allowed",
    ]),
    notification_lifecycle: pick(body?.notification_lifecycle, [
      "web_created",
      "web_queued",
      "web_reserved",
      "web_rendered",
      "web_acted",
      "web_dismissed",
      "web_expired",
      "web_lost_unrendered",
      "duplicate_prompt_count",
      "render_without_exposure_count",
      "exposure_without_render_count",
      "operator_created",
      "operator_pending",
    ]),
    state_invariants: pick(body?.state_invariants, [
      "duplicate_open_sessions",
      "executing_tasks_without_open_session",
      "paused_tasks_without_open_session",
      "executed_tasks_missing_start_or_end",
      "open_sessions_for_executed_tasks",
      "stale_reentry_candidates",
      "invalid_recovery_actions_seen",
    ]),
    measurement_integrity: {
      clean_trace_ratio: body?.measurement_integrity?.clean_trace_ratio ?? null,
      dirty_trace_count: body?.measurement_integrity?.dirty_trace_count ?? null,
      analytic_blockers: body?.measurement_integrity?.analytic_blockers ?? [],
      clean_trace_ratio_basis: pick(cleanBasis, ["numerator", "denominator"]),
    },
    provider_integrity: pick(body?.provider_integrity, [
      "provider_rows_total",
      "provider_rows_missing_provenance",
      "provider_completion_candidates",
      "provider_truth_violations",
      "duplicate_import_candidates",
      "sync_failures_24h",
      "user_visible_provider_errors_24h",
    ]),
  };
}

function diffObjects(before, after, prefix = "") {
  const diffs = [];
  if (JSON.stringify(before) === JSON.stringify(after)) return diffs;
  const beforeRecord = before && typeof before === "object" && !Array.isArray(before)
    ? before
    : null;
  const afterRecord = after && typeof after === "object" && !Array.isArray(after)
    ? after
    : null;
  if (!beforeRecord || !afterRecord) {
    return [{ key: prefix || "value", before, after }];
  }
  const keys = new Set([...Object.keys(beforeRecord), ...Object.keys(afterRecord)]);
  for (const key of keys) {
    const childPrefix = prefix ? `${prefix}.${key}` : key;
    diffs.push(...diffObjects(beforeRecord[key], afterRecord[key], childPrefix));
  }
  return diffs;
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
      vary: "Origin",
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
    domcontentloaded_ms: null,
    ready_ms: null,
    artifact_ms: null,
    status: null,
    screenshot: null,
    issues: [],
    warnings: [],
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
    if (text.includes("[next-auth][error][CLIENT_FETCH_ERROR]")) {
      result.warnings.push(text.slice(0, 500));
      return;
    }
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
    result.domcontentloaded_ms = Date.now() - started;
    result.status = response?.status() ?? null;
    if (route.path === "/operator") {
      await page.waitForFunction(
        () => /Operator cockpit|Cohort readiness|safe to invite|Failed to load operator dashboard|This surface is operator-only/i
          .test(document.body?.innerText || ""),
        undefined,
        { timeout: route.maxMs },
      );
    }
    result.ready_ms = Date.now() - started;

    await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});

    const bodyText = await page.locator("body").innerText({ timeout: 5_000 }).catch(() => "");
    for (const pattern of forbiddenTextPatterns) {
      if (pattern.test(bodyText)) {
        result.issues.push(`forbidden copy matched ${pattern}`);
      }
    }
    if (route.path === "/operator" && !/Operator cockpit|Cohort readiness|safe to invite/i.test(bodyText)) {
      result.issues.push("operator route did not render operator cockpit");
    }
    if (route.path === "/operator" && expectReadinessSplit) {
      for (const label of [
        /implementation green/i,
        /cohort green/i,
        /controlled evidence/i,
      ]) {
        if (!label.test(bodyText)) {
          result.issues.push(`operator route missing readiness split label ${label}`);
        }
      }
    }
    if (result.ready_ms > route.maxMs) {
      result.issues.push(`route exceeded hard latency budget ${route.maxMs}ms`);
    } else if (result.ready_ms > route.targetMs) {
      result.warnings.push(`route exceeded target latency budget ${route.targetMs}ms`);
    }

    const screenshotPath = path.join(outDir, `alinassersabry-${viewport.name}-${route.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.screenshot = path.relative(repoRoot, screenshotPath).replaceAll("\\", "/");
    result.artifact_ms = Date.now() - started;
    result.duration_ms = result.ready_ms;
  } catch (error) {
    result.duration_ms = Date.now() - started;
    result.issues.push(`navigation failed: ${error.message}`);
    const screenshotPath = path.join(
      outDir,
      `alinassersabry-${viewport.name}-${route.name}-failure.png`,
    );
    const wroteFailureShot = await page
      .screenshot({ path: screenshotPath, fullPage: true })
      .then(() => true)
      .catch(() => false);
    if (wroteFailureShot) {
      result.screenshot = path.relative(repoRoot, screenshotPath).replaceAll("\\", "/");
    }
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
  proxy_api: proxyApi,
  expect_readiness_split: expectReadinessSplit,
  user_ref: null,
  is_operator: null,
  before_counts: null,
  pre_dashboard_count_diffs: [],
  after_counts: null,
  count_diffs: [],
  route_count_diffs: [],
  dashboard_before_snapshot: null,
  dashboard_after_snapshot: null,
  dashboard_snapshot_diffs: [],
  routes: [],
  warnings: [],
  issues: [],
};

try {
  const context = await browser.newContext({ viewport: viewports[0] });
  if (proxyApi) {
    await installApiProxy(context);
  }
  await context.addCookies(parseAndExpandCookies(cookieHeader, frontendOrigin));
  const page = await context.newPage();
  const token = await resolveBackendTokenFromContext(context, frontendOrigin);

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

  const beforeDashboard = await fetchJson("/v1/operator/dashboard", token);
  if (beforeDashboard.status !== 200) {
    throw new Error(`pre operator dashboard failed with ${beforeDashboard.status}`);
  }
  const afterPreDashboardExport = await fetchJson("/v1/users/me/export", token);
  if (afterPreDashboardExport.status !== 200) {
    throw new Error(`post pre-dashboard export failed with ${afterPreDashboardExport.status}`);
  }
  const afterPreDashboardCounts = countExport(afterPreDashboardExport.body || {});
  result.pre_dashboard_count_diffs = diffCounts(result.before_counts, afterPreDashboardCounts);
  if (result.pre_dashboard_count_diffs.length > 0) {
    result.issues.push(
      `operator dashboard API read changed exported data counts before browser route: ${JSON.stringify(result.pre_dashboard_count_diffs)}`,
    );
  }
  result.dashboard_before_snapshot = dashboardReadOnlySnapshot(beforeDashboard.body || {});

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const route of routes) {
      const routeBeforeExport = await fetchJson("/v1/users/me/export", token);
      const routeBeforeCounts = countExport(routeBeforeExport.body || {});
      const routeResult = await checkRoute(page, route, viewport);
      result.routes.push(routeResult);
      const routeAfterExport = await fetchJson("/v1/users/me/export", token);
      const routeAfterCounts = countExport(routeAfterExport.body || {});
      const routeDiffs = diffCounts(routeBeforeCounts, routeAfterCounts);
      if (routeDiffs.length > 0) {
        result.route_count_diffs.push({
          viewport: viewport.name,
          route: route.path,
          diffs: routeDiffs,
        });
      }
    }
  }

  const afterExport = await fetchJson("/v1/users/me/export", token);
  if (afterExport.status !== 200) throw new Error(`post export failed with ${afterExport.status}`);
  result.after_counts = countExport(afterExport.body || {});
  result.count_diffs = diffCounts(result.before_counts, result.after_counts);
  if (result.count_diffs.length > 0) {
    result.issues.push(`read-only stress changed exported data counts: ${JSON.stringify(result.count_diffs)}`);
  }

  const afterDashboard = await fetchJson("/v1/operator/dashboard", token);
  if (afterDashboard.status !== 200) {
    throw new Error(`post operator dashboard failed with ${afterDashboard.status}`);
  }
  result.dashboard_after_snapshot = dashboardReadOnlySnapshot(afterDashboard.body || {});
  result.dashboard_snapshot_diffs = diffObjects(
    result.dashboard_before_snapshot,
    result.dashboard_after_snapshot,
  );
  if (result.dashboard_snapshot_diffs.length > 0) {
    result.issues.push(
      `operator dashboard read changed invariant snapshot: ${JSON.stringify(result.dashboard_snapshot_diffs.slice(0, 12))}`,
    );
  }

  await context.close();
} catch (error) {
  result.issues.push(error.message);
} finally {
  await browser.close();
}

for (const route of result.routes) {
  for (const warning of route.warnings || []) {
    result.warnings.push(`${route.viewport} ${route.route}: ${warning}`);
  }
  for (const issue of route.issues || []) {
    result.issues.push(`${route.viewport} ${route.route}: ${issue}`);
  }
}

result.ok = result.issues.length === 0;
await writeFile(path.join(outDir, "result.json"), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
if (!result.ok) process.exitCode = 1;
