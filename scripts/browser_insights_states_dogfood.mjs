import fs from "node:fs";
import path from "node:path";

import {
  frontendRequire,
  parseAndExpandCookies,
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

const frontendOrigin = args.get("frontend") || "https://lyraos.org";
const apiOrigin = args.get("api") || "https://api.lyraos.org";
const proxyApi = args.get("proxy-api") === "true";
const onboardingSkipSessionKey = "lyra:onboarding-skip-this-session";
const cookie = process.env.LYRA_COOKIE_HOLMESBERG || "";
if (cookie.length < 100) {
  throw new Error("LYRA_COOKIE_HOLMESBERG is missing or looks truncated.");
}

const outDir = path.join(
  "tmp",
  "browser-insights-states",
  new Date().toISOString().replaceAll(":", "-").replace(".", "-")
);
fs.mkdirSync(outDir, { recursive: true });

const forbiddenClaimWords = [
  "adhd",
  "diagnosis",
  "lazy",
  "undisciplined",
  "avoidant personality",
  "you are avoidant",
  "mental health",
];

const scenarios = [
  {
    name: "locked",
    payload: {
      surface_id: "analytics.insights",
      insights: [],
      sessions_analyzed: 1,
      history_events_analyzed: 1,
      min_sessions_required: 3,
      unlocked: false,
      ready: false,
      message: "Log 2 more executed sessions to unlock execution insights.",
      suppressed_generators: [],
    },
    expect: [/log 2 more executed sessions/i, /1\s*\/\s*3\s*sessions analyzed/i],
    reject: [/holding these cards/i, /clean stops to reopen/i],
  },
  {
    name: "held",
    payload: {
      surface_id: "analytics.insights",
      insights: [],
      sessions_analyzed: 27,
      history_events_analyzed: 41,
      min_sessions_required: 3,
      unlocked: true,
      ready: false,
      suppressed_reason: "rule11_no_nudge_control_day",
      reopen_after_clean_sessions: 3,
      new_clean_sessions_since_hold: 1,
      clean_sessions_until_reopen: 2,
      message: "Insights are unlocked. LyraOS is holding these cards until there is new clean evidence after this hold. Complete 2 more cleanly stopped sessions to reopen this surface.",
      suppressed_generators: [],
    },
    expect: [/27 sessions analyzed/i, /2 clean stops to reopen/i, /new clean evidence/i],
    reject: [/27\s*\/\s*3\s*sessions analyzed/i, /unlock in/i],
  },
  {
    name: "unlocked",
    payload: {
      surface_id: "analytics.insights",
      insights: [
        {
          id: "time_of_day_bias",
          surface_id: "analytics.insights.time_of_day_bias",
          title: "Time of day",
          body: "Your afternoon estimates are running long in the clean sample.",
          observation: "Your afternoon estimates are running long in the clean sample.",
          confidence: "medium",
          confidence_label: "Medium confidence",
          sample_label: "5 clean sessions",
          data_points: 5,
          strength: 0.42,
          evidence_rows: [
            {
              source_insight_id: "time_of_day_bias",
              label: "Clean sample",
              value: "5 sessions",
            },
          ],
        },
      ],
      sessions_analyzed: 5,
      history_events_analyzed: 9,
      min_sessions_required: 3,
      unlocked: true,
      ready: true,
      suppressed_generators: [],
    },
    expect: [/time of day/i, /medium confidence/i, /afternoon estimates are running long/i],
    reject: [/failed to load/i, /holding these cards/i],
  },
  {
    name: "empty-unlocked",
    payload: {
      surface_id: "analytics.insights",
      insights: [],
      sessions_analyzed: 9,
      history_events_analyzed: 15,
      min_sessions_required: 3,
      unlocked: true,
      ready: true,
      suppressed_reason: "no_contract_safe_insights",
      suppressed_generators: [],
    },
    expect: [/no stable insight cards right now/i, /analytics remain unlocked/i],
    reject: [/unlock in/i, /failed to load/i],
  },
];

const checks = [];
const issues = [];

function addCheck(name, ok, detail = null) {
  checks.push({ name, ok: Boolean(ok), detail });
}

async function installApiProxy(context, insightsRouteHandler, renderAckRouteHandler = null) {
  const apiPattern = `${apiOrigin.replace(/\/$/, "")}/**`;
  await context.route(apiPattern, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === "/v1/analytics/insights") {
      await insightsRouteHandler(route);
      return;
    }
    if (
      renderAckRouteHandler
      && /^\/v1\/exposures\/[^/]+\/ack\/render$/.test(pathname)
    ) {
      await renderAckRouteHandler(route);
      return;
    }
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
      await route.fulfill({ status: 204, headers: corsHeaders, body: "" });
      return;
    }

    const headers = { ...requestHeaders };
    for (const header of [
      "host",
      "origin",
      "referer",
      "sec-fetch-dest",
      "sec-fetch-mode",
      "sec-fetch-site",
    ]) {
      delete headers[header];
    }

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
        headers: { ...response.headers(), ...corsHeaders },
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

async function screenshot(page, name) {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

function textHasForbiddenClaim(text) {
  const lower = text.toLowerCase();
  return forbiddenClaimWords.filter((word) => lower.includes(word));
}

async function newPage(browser, scenarioName, routeHandler, renderAckRouteHandler = null) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  await context.addInitScript((key) => {
    window.sessionStorage.setItem(key, "1");
  }, onboardingSkipSessionKey);
  if (proxyApi) {
    await installApiProxy(context, routeHandler, renderAckRouteHandler);
  }
  await context.addCookies(parseAndExpandCookies(cookie, frontendOrigin));
  const consoleErrors = [];
  const page = await context.newPage();
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleErrors.push(`${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(`pageerror: ${error.message}`);
  });
  if (!proxyApi) {
    await page.route(`${apiOrigin}/v1/analytics/insights**`, routeHandler);
    if (renderAckRouteHandler) {
      await page.route(
        `${apiOrigin}/v1/exposures/*/ack/render`,
        renderAckRouteHandler,
      );
    }
  }
  return { context, page, consoleErrors, scenarioName };
}

async function runExposureAckScenario(browser) {
  const base = scenarios.find((scenario) => scenario.name === "unlocked").payload;
  const exposureId = `fixture-insights-${Date.now()}`;
  const renderSnapshot = {
    schema_version: "analytics_insights_exposure_snapshot_v1",
    surface_id: "analytics.insights",
    insight_count: base.insights.length,
    insight_ids: base.insights.map((insight) => insight.id),
    audit_envelopes: [],
  };
  const payload = {
    ...base,
    exposure_id: exposureId,
    render_snapshot: renderSnapshot,
  };
  const ackRequests = [];
  const { context, page, consoleErrors } = await newPage(
    browser,
    "exposure-ack",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
    },
    async (route) => {
      const request = route.request();
      let body = null;
      try {
        body = JSON.parse(request.postData() || "{}");
      } catch (error) {
        body = { parse_error: String(error?.message || error) };
      }
      ackRequests.push({
        method: request.method(),
        pathname: new URL(request.url()).pathname,
        body,
      });
      if (ackRequests.length === 1) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "forced fixture retry" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ack_id: `fixture-ack-${exposureId}`,
          exposure_id: exposureId,
          event_type: "render",
          user_id: 0,
          acked_at: new Date().toISOString(),
          created: true,
        }),
      });
    },
  );
  try {
    await page.goto(`${frontendOrigin}/insights`, { waitUntil: "domcontentloaded" });
    await page.getByText(/afternoon estimates are running long/i).waitFor({ timeout: 15_000 });
    const deadline = Date.now() + 10_000;
    while (ackRequests.length < 2 && Date.now() < deadline) {
      await page.waitForTimeout(100);
    }
    await screenshot(page, "exposure-ack-desktop");

    addCheck("insights mounted render retries a failed acknowledgement", ackRequests.length === 2, {
      request_count: ackRequests.length,
    });
    const finalAck = ackRequests.at(-1);
    addCheck("insights render acknowledgement uses the canonical owner route", Boolean(
      finalAck
      && finalAck.method === "POST"
      && finalAck.pathname === `/v1/exposures/${exposureId}/ack/render`
    ), finalAck);
    addCheck("insights render acknowledgement binds surface, event, and snapshot", Boolean(
      finalAck
      && finalAck.body?.surface_id === "analytics.insights"
      && finalAck.body?.client_event_id === `analytics.insights:${exposureId}`
      && JSON.stringify(finalAck.body?.content_snapshot) === JSON.stringify(renderSnapshot)
    ), finalAck?.body || null);
    const unexpectedErrors = consoleErrors.filter(
      (entry) => !entry.includes("503 (Service Unavailable)"),
    );
    addCheck("insights render acknowledgement retry has no unexpected page errors", unexpectedErrors.length === 0, {
      console_errors: consoleErrors,
      unexpected_errors: unexpectedErrors,
    });
  } finally {
    await context.close();
  }
}

async function runScenario(browser, scenario) {
  const { context, page, consoleErrors } = await newPage(
    browser,
    scenario.name,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scenario.payload),
      });
    }
  );
  try {
    const started = Date.now();
    await page.goto(`${frontendOrigin}/insights`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => {});
    const bodyText = await page.locator("body").innerText({ timeout: 15_000 });
    const durationMs = Date.now() - started;
    await screenshot(page, `${scenario.name}-desktop`);

    for (const pattern of scenario.expect) {
      addCheck(`insights ${scenario.name} includes ${pattern}`, pattern.test(bodyText), {
        duration_ms: durationMs,
      });
    }
    for (const pattern of scenario.reject) {
      addCheck(`insights ${scenario.name} excludes ${pattern}`, !pattern.test(bodyText), {
        duration_ms: durationMs,
      });
    }
    const forbidden = textHasForbiddenClaim(bodyText);
    addCheck(`insights ${scenario.name} avoids forbidden claims`, forbidden.length === 0, forbidden);
    addCheck(`insights ${scenario.name} loads within senior UI budget`, durationMs < 8_000, {
      duration_ms: durationMs,
    });
    addCheck(`insights ${scenario.name} has no page errors`, consoleErrors.length === 0, consoleErrors);
  } finally {
    await context.close();
  }
}

async function runLatencyScenario(browser) {
  const payload = scenarios.find((scenario) => scenario.name === "unlocked").payload;
  let insightsRequestStarted = false;
  const { context, page, consoleErrors } = await newPage(
    browser,
    "latency",
    async (route) => {
      insightsRequestStarted = true;
      await new Promise((resolve) => setTimeout(resolve, 3_000));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
    }
  );
  try {
    const started = Date.now();
    await page.goto(`${frontendOrigin}/insights`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
      () => document.body?.innerText?.includes("Insights"),
      null,
      { timeout: 5_000 }
    ).catch(() => {});
    await new Promise((resolve) => setTimeout(resolve, 500));
    const bodyDuringLoad = await page.locator("body").innerText({ timeout: 5_000 });
    const skeletonVisible = await page.locator(".animate-pulse").first().isVisible({ timeout: 500 }).catch(() => false);
    const hasResolvedCopyEarly = /afternoon estimates are running long/i.test(bodyDuringLoad);
    await screenshot(page, "latency-in-flight");
    await page.getByText(/afternoon estimates are running long/i).waitFor({ timeout: 10_000 });
    const durationMs = Date.now() - started;
    await screenshot(page, "latency-desktop");
    addCheck("insights latency scenario exercised delayed request", insightsRequestStarted, {
      duration_ms: durationMs,
    });
    addCheck("insights latency scenario shows loading skeleton before data", skeletonVisible && !hasResolvedCopyEarly, {
      duration_ms: durationMs,
      body_during_load: bodyDuringLoad.slice(0, 500),
    });
    addCheck("insights latency scenario resolves within budget", durationMs < 8_000, {
      duration_ms: durationMs,
    });
    addCheck("insights latency scenario has no page errors", consoleErrors.length === 0, consoleErrors);
  } finally {
    await context.close();
  }
}

async function runErrorScenario(browser) {
  const { context, page, consoleErrors } = await newPage(
    browser,
    "error",
    async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "insights unavailable in dogfood" }),
      });
    }
  );
  try {
    await page.goto(`${frontendOrigin}/insights`, { waitUntil: "domcontentloaded" });
    await page.getByText(/failed to load insights/i).waitFor({ timeout: 25_000 });
    const bodyText = await page.locator("body").innerText({ timeout: 5_000 });
    await screenshot(page, "error-desktop");
    addCheck("insights error state is visible", /failed to load insights/i.test(bodyText), bodyText);
    addCheck("insights error state keeps copy bounded", /check your connection and try again/i.test(bodyText), bodyText);
    const severe = consoleErrors.filter((entry) => !entry.includes("Failed to load resource"));
    addCheck("insights error state has no unexpected page errors", severe.length === 0, consoleErrors);
  } finally {
    await context.close();
  }
}

const browser = await chromium.launch({ headless: true });
let result;
try {
  for (const scenario of scenarios) {
    await runScenario(browser, scenario);
  }
  await runExposureAckScenario(browser);
  await runLatencyScenario(browser);
  await runErrorScenario(browser);
  result = {
    ok: checks.every((check) => check.ok),
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
    proxy_api: proxyApi,
    fixture_only: true,
    fixture_overrides: [
      "session_only_onboarding_skip",
      "forced_insights_payload",
      "forced_render_ack_transport",
    ],
    output_dir: outDir,
    checks,
    issues,
  };
} catch (error) {
  result = {
    ok: false,
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
    proxy_api: proxyApi,
    fixture_only: true,
    fixture_overrides: [
      "session_only_onboarding_skip",
      "forced_insights_payload",
      "forced_render_ack_transport",
    ],
    output_dir: outDir,
    error: error instanceof Error ? error.message : String(error),
    checks,
    issues,
  };
} finally {
  await browser.close();
}

fs.writeFileSync(path.join(outDir, "result.json"), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
if (!result.ok) {
  process.exit(1);
}
