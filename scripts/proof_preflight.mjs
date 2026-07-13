#!/usr/bin/env node
import fs from "node:fs";
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

const HEALTH_PATH = "/v1/health/topology";

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function flag(name) {
  return process.argv.includes(name);
}

function normalize(value) {
  return String(value || "").replace(/\/$/, "");
}

function rows(body, key) {
  return Array.isArray(body?.[key]) ? body[key] : [];
}

function withTimeout(label, promise, timeoutMs) {
  let timeout;
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timeout = setTimeout(() => reject(new Error(`${label} exceeded ${timeoutMs}ms`)), timeoutMs);
    }),
  ]).finally(() => clearTimeout(timeout));
}

function policyErrors({ account, intent, topology, prefix, fixtureAccountReady, proxyApi = false }) {
  const errors = [];
  if (intent === "mutable" && account !== "holmesberg") {
    errors.push("mutable proof is restricted to Holmesberg");
  }
  if (prefix && !/^DOGFOOD(?:\s|[-_])/.test(prefix)) {
    errors.push("synthetic prefix must begin with DOGFOOD");
  }
  if (fixtureAccountReady && topology !== "local-current") {
    errors.push("account-readiness fixture is restricted to local-current");
  }
  if (fixtureAccountReady && !proxyApi) {
    errors.push("account-readiness fixture requires explicit API proxying");
  }
  return errors;
}

function buildMatches(actual, expected) {
  return !expected || String(actual || "") === String(expected);
}

function accountGateBlockers(bodyText) {
  const text = String(bodyText || "");
  return [
    /Before you continue/i.test(text) ? "consent_required" : null,
    /LyraOS starts learning from the first plan/i.test(text) ? "onboarding_required" : null,
  ].filter(Boolean);
}

if (flag("--self-test")) {
  const failures = [];
  const wrapper = fs.readFileSync(path.join(repoRoot, "scripts", "proof_preflight.ps1"), "utf8");
  const source = fs.readFileSync(path.join(repoRoot, "scripts", "proof_preflight.mjs"), "utf8");
  if (!policyErrors({ account: "operator", intent: "mutable", topology: "local-current" }).length) {
    failures.push("operator mutable intent was accepted");
  }
  if (!policyErrors({ account: "holmesberg", intent: "mutable", topology: "local-current", prefix: "capture" }).length) {
    failures.push("unsafe synthetic prefix was accepted");
  }
  if (!policyErrors({ account: "holmesberg", intent: "readonly", topology: "public", fixtureAccountReady: true }).length) {
    failures.push("public account fixture was accepted");
  }
  if (buildMatches("actual", "wrong")) failures.push("wrong build ID was accepted");
  if (!accountGateBlockers("Before you continue").includes("consent_required")) {
    failures.push("consent gate was not classified");
  }
  if (!accountGateBlockers("LyraOS starts learning from the first plan").includes("onboarding_required")) {
    failures.push("onboarding gate was not classified");
  }
  if (HEALTH_PATH !== "/v1/health/topology") failures.push("canonical health path drifted");
  if (!wrapper.includes(".IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0")) {
    failures.push("PowerShell 5 compatible checkout ownership comparison is missing");
  }
  if (!wrapper.includes("function Get-CheckoutOwnerProcessId") || !wrapper.includes("$current.ParentProcessId")) {
    failures.push("local port ownership does not inspect child-process ancestry");
  }
  if (wrapper.includes(".Contains($repoRoot, [StringComparison]::OrdinalIgnoreCase)")) {
    failures.push("unsupported Windows PowerShell String.Contains overload returned");
  }
  if (!source.includes('await context.unrouteAll({ behavior: "ignoreErrors" });')) {
    failures.push("browser context can close before read-only proxy handlers settle");
  }
  console.log(JSON.stringify({ ok: failures.length === 0, checked: "proof_preflight", failures }));
  process.exit(failures.length ? 1 : 0);
}

const { chromium } = frontendRequire("playwright");

const topology = arg("--topology", "public");
const frontendOrigin = normalize(arg("--frontend"));
const apiOrigin = normalize(arg("--api"));
const intent = arg("--intent", "readonly");
const accountArg = arg("--account", "both");
const expectedBuildId = arg("--expected-frontend-build", null);
const targetPath = arg("--target-path", null);
const readySelector = arg("--ready-selector", null);
const selectedDate = arg("--selected-date", null);
const selectedWeek = arg("--selected-week", null);
const prefix = arg("--synthetic-prefix", null);
const outFile = arg("--out-file", null);
const timeoutMs = Number(arg("--timeout-ms", "30000"));
const maxExportBytes = Number(arg("--max-export-bytes", "20000000"));
const maxPending = Number(arg("--max-pending-notifications", "0"));
const proxyApi = flag("--proxy-api");
const fixtureAccountReady = flag("--fixture-account-ready");
const requireAccountReady = flag("--require-account-ready");

if (!frontendOrigin || !apiOrigin) throw new Error("--frontend and --api are required");
if (!['readonly', 'mutable'].includes(intent)) throw new Error("--intent must be readonly or mutable");

const accounts = accountArg === "both" ? ["operator", "holmesberg"] : [accountArg];
const envNames = {
  operator: "LYRA_COOKIE_ALINASSERSABRY",
  holmesberg: "LYRA_COOKIE_HOLMESBERG",
};
const checks = [];
const accountResults = [];

function check(name, ok, detail = null) {
  checks.push({ name, ok: Boolean(ok), detail });
}

async function fetchJson(url) {
  const response = await withTimeout(url, fetch(url), timeoutMs);
  const text = await response.text();
  let body;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  return { response, body };
}

async function installReadOnlyRoute(context) {
  const pattern = `${apiOrigin}/**`;
  await context.route(pattern, async (route) => {
    const request = route.request();
    if (request.method().toUpperCase() === "OPTIONS" && proxyApi) {
      await route.fulfill({
        status: 204,
        headers: {
          "access-control-allow-origin": frontendOrigin,
          "access-control-allow-credentials": "true",
          "access-control-allow-methods": "GET,HEAD,OPTIONS",
          "access-control-allow-headers": request.headers()["access-control-request-headers"] || "authorization,content-type",
          vary: "Origin",
        },
        body: "",
      });
      return;
    }
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method().toUpperCase())) {
      await route.fulfill({ status: 409, contentType: "application/json", body: '{"detail":"proof_preflight_read_only"}' });
      return;
    }
    if (!proxyApi) {
      await route.continue();
      return;
    }
    const headers = { ...request.headers() };
    for (const key of ["host", "origin", "referer", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"]) delete headers[key];
    const response = await context.request.fetch(request.url(), {
      method: request.method(), headers, timeout: timeoutMs, failOnStatusCode: false,
    });
    const responseHeaders = {
      ...response.headers(),
      "access-control-allow-origin": frontendOrigin,
      "access-control-allow-credentials": "true",
      vary: "Origin",
    };
    let body = await response.body();
    if (fixtureAccountReady && request.method() === "GET" && new URL(request.url()).pathname === "/v1/users/me" && response.ok()) {
      const me = JSON.parse(body.toString("utf8"));
      Object.assign(me, {
        terms_accepted_at: me.terms_accepted_at || "1970-01-01T00:00:00Z",
        archetype_survey_eligible: false,
        onboarding_completed_at: me.onboarding_completed_at || "1970-01-01T00:00:00Z",
        has_active_task_history: true,
      });
      body = Buffer.from(JSON.stringify(me));
      delete responseHeaders["content-encoding"];
      delete responseHeaders["content-length"];
    }
    await route.fulfill({ status: response.status(), headers: responseHeaders, body });
  });
}

const browser = await chromium.launch({ headless: true });
try {
  const frontend = await fetchJson(`${frontendOrigin}/api/topology`);
  const backend = await fetchJson(`${apiOrigin}${HEALTH_PATH}`);
  check("frontend topology endpoint", frontend.response.ok, { status: frontend.response.status });
  check("backend canonical topology endpoint", backend.response.ok, { status: backend.response.status, path: HEALTH_PATH });
  check("compiled API origin matches", normalize(frontend.body?.compiled_api_origin) === apiOrigin, { actual: frontend.body?.compiled_api_origin, expected: apiOrigin });
  check("frontend build matches expected", buildMatches(frontend.body?.build_id, expectedBuildId), { actual: frontend.body?.build_id, expected: expectedBuildId });

  if (checks.every((item) => item.ok)) for (const account of accounts) {
    const errors = policyErrors({ account, intent, topology, prefix, fixtureAccountReady, proxyApi });
    check(`${account} policy`, errors.length === 0, errors);
    const cookie = process.env[envNames[account]];
    assertCookieHeaderLooksUsable(account, cookie);
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await context.addCookies(parseAndExpandCookies(cookie, frontendOrigin));
    await installReadOnlyRoute(context);
    const token = await resolveBackendTokenFromContext(context, frontendOrigin);
    const me = await withTimeout(`${account} users/me`, apiFetch(apiOrigin, token, "/v1/users/me"), timeoutMs);
    const exportStarted = Date.now();
    const exported = await withTimeout(`${account} export`, apiFetch(apiOrigin, token, "/v1/users/me/export"), timeoutMs);
    const exportDurationMs = Date.now() - exportStarted;
    const pending = await withTimeout(`${account} pending`, apiFetch(apiOrigin, token, "/v1/notifications/web/pending"), timeoutMs);
    const stopwatch = await withTimeout(`${account} stopwatch`, apiFetch(apiOrigin, token, "/v1/stopwatch/status"), timeoutMs);
    const exportBytes = Buffer.byteLength(JSON.stringify(exported.body || {}));
    const pendingRows = pending.body?.notifications || [];
    const activePrefixTasks = rows(exported.body, "tasks").filter((row) => String(row.title || "").startsWith(prefix || "\0") && !row.voided_at);
    const activePrefixDeadlines = rows(exported.body, "deadlines").filter((row) => String(row.title || "").startsWith(prefix || "\0") && !row.voided_at);
    const expectedOperator = account === "operator";
    const accountReady = Boolean(me.body?.terms_accepted_at && me.body?.onboarding_completed_at && me.body?.has_active_task_history);
    check(`${account} cookie and session`, me.response.ok, { status: me.response.status });
    check(`${account} role`, me.body?.is_operator === expectedOperator, { expected_operator: expectedOperator, actual: me.body?.is_operator });
    check(`${account} export envelope`, exported.response.ok && exportDurationMs <= timeoutMs && exportBytes <= maxExportBytes, { duration_ms: exportDurationMs, bytes: exportBytes, timeout_ms: timeoutMs, max_bytes: maxExportBytes });
    check(`${account} pending envelope`, pending.response.ok && pendingRows.length <= maxPending, { count: pendingRows.length, maximum: maxPending });
    check(`${account} synthetic prefix is clean`, activePrefixTasks.length === 0 && activePrefixDeadlines.length === 0, { task_ids: activePrefixTasks.map((row) => row.task_id), deadline_ids: activePrefixDeadlines.map((row) => row.deadline_id) });
    check(`${account} account readiness`, !requireAccountReady || accountReady || fixtureAccountReady, { account_ready: accountReady, fixture_account_ready: fixtureAccountReady });

    let mounted = null;
    if (targetPath) {
      const page = await context.newPage();
      const pageErrors = [];
      page.on("pageerror", (error) => pageErrors.push(error.message));
      const response = await page.goto(`${frontendOrigin}${targetPath}`, { waitUntil: "domcontentloaded", timeout: timeoutMs });
      await page.locator("body").waitFor({ state: "visible", timeout: timeoutMs });
      const bodyText = await page.locator("body").innerText({ timeout: timeoutMs });
      const gateBlockers = accountGateBlockers(bodyText);
      let selectorVisible = null;
      if (readySelector) {
        const locator = page.locator(readySelector).first();
        await locator.waitFor({ state: "visible", timeout: timeoutMs }).catch(() => {});
        selectorVisible = await locator.isVisible().catch(() => false);
      }
      mounted = {
        status: response?.status() ?? null,
        selector: readySelector,
        selector_visible: selectorVisible,
        page_errors: pageErrors,
        account_gate_blockers: gateBlockers,
      };
      check(`${account} target mount`, Boolean(
        response?.ok()
        && pageErrors.length === 0
        && gateBlockers.length === 0
        && (readySelector ? selectorVisible : true)
      ), mounted);
    }

    accountResults.push({
      account,
      user_ref: userRef(me.body?.user_id),
      role: expectedOperator ? "operator_read_only" : "holmesberg_mutable",
      account_ready: accountReady,
      active_timer: Boolean(stopwatch.body?.active),
      export_duration_ms: exportDurationMs,
      export_bytes: exportBytes,
      pending_notifications: pendingRows.length,
      target: mounted,
    });
    await context.unrouteAll({ behavior: "ignoreErrors" });
    await context.close();
  }
} finally {
  await browser.close();
}

const result = {
  ok: checks.every((item) => item.ok),
  classification: checks.every((item) => item.ok) ? "proof_preflight_passed" : "proof_preflight_blocked",
  topology,
  frontend_origin: frontendOrigin,
  api_origin: apiOrigin,
  frontend_build_id: checks.find((item) => item.name === "frontend build matches expected")?.detail?.actual ?? null,
  intent,
  fixture_account_ready: fixtureAccountReady,
  selected_date: selectedDate,
  selected_week: selectedWeek,
  target_path: targetPath,
  checks,
  accounts: accountResults,
  writes: "none; browser API mutations are blocked with proof_preflight_read_only",
};

if (outFile) {
  const resolved = path.resolve(repoRoot, outFile);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  fs.writeFileSync(resolved, `${JSON.stringify(result, null, 2)}\n`);
}
console.log(JSON.stringify(result, null, 2));
process.exit(result.ok ? 0 : 1);
