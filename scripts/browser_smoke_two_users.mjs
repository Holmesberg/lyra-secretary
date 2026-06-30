#!/usr/bin/env node
import {
  apiFetch as helperApiFetch,
  frontendRequire,
  parseAndExpandCookies,
  resolveBackendToken,
  userRef,
} from "./browser_auth_helpers.mjs";

const { chromium } = frontendRequire("playwright");

const frontendOrigin = process.env.LYRA_FRONTEND_ORIGIN || "http://localhost:3000";
const apiOrigin = process.env.LYRA_API_ORIGIN || "http://localhost:8000";

const accounts = [
  {
    label: "asabryhafez",
    cookieHeader: process.env.LYRA_COOKIE_ASABRYHAFEZ || "",
  },
  {
    label: "holmesberg",
    cookieHeader:
      process.env.LYRA_COOKIE_HOLMESBERG
      || process.env.LYRA_COOKIE_MORIARTY
      || "",
  },
];

function fail(message, detail = undefined) {
  const err = new Error(message);
  err.detail = detail;
  throw err;
}

async function apiFetchForConfiguredApi(token, path, init = {}) {
  return helperApiFetch(apiOrigin, token, path, init);
}

async function assertOkApi(token, path) {
  const result = await apiFetchForConfiguredApi(token, path);
  if (!result.response.ok) {
    fail(`API smoke failed for ${path}`, {
      status: result.response.status,
      body: result.body,
    });
  }
  return result.body;
}

async function assertOkApiForAccount(accountLabel, token, path) {
  try {
    return await assertOkApi(token, path);
  } catch (error) {
    error.message = `${accountLabel}: ${error.message}`;
    throw error;
  }
}

async function assertForbidden(token, path) {
  const result = await apiFetchForConfiguredApi(token, path);
  if (result.response.status !== 403) {
    fail(`expected 403 for non-operator route ${path}`, {
      status: result.response.status,
      body: result.body,
    });
  }
}

function assertExportScoped(exportBody, userId) {
  for (const task of exportBody.tasks || []) {
    if (task.user_id !== userId) {
      fail("account export contained a task for a different user");
    }
  }
  for (const session of exportBody.stopwatch_sessions || []) {
    if (session.user_id !== userId) {
      fail("account export contained a session for a different user");
    }
  }
  for (const assignment of exportBody.archetype_assignments || []) {
    if (assignment.user_id !== userId) {
      fail("account export contained an archetype assignment for a different user");
    }
  }
}

async function smokeAccount(browser, account) {
  if (!account.cookieHeader.trim()) {
    fail(`missing cookie env for ${account.label}`);
  }

  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const cookies = parseAndExpandCookies(account.cookieHeader, frontendOrigin);
  if (!cookies.length) {
    fail(`no cookie pairs parsed for ${account.label}`);
  }
  await context.addCookies(cookies);

  const page = await context.newPage();
  const failedResponses = [];
  page.on("response", (response) => {
    if (response.status() >= 500) {
      failedResponses.push({ url: response.url(), status: response.status() });
    }
  });

  await page.goto(`${frontendOrigin}/pulse`, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

  let token = null;
  try {
    token = await resolveBackendToken(page);
  } catch (error) {
    fail(`no backend token resolved for ${account.label}`, {
      frontendOrigin,
      ...(error.detail || {}),
      parsedCookieNames: cookies.map((cookie) => cookie.name),
    });
  }

  const me = await assertOkApiForAccount(account.label, token, "/v1/users/me");
  const integrations = await assertOkApiForAccount(account.label, token, "/v1/integrations");
  const pressure = await assertOkApiForAccount(
    account.label,
    token,
    "/v1/academic/pressure-map?horizon_days=14"
  );
  const summary = await assertOkApiForAccount(
    account.label,
    token,
    "/v1/users/me/data-summary"
  );
  const exported = await assertOkApiForAccount(
    account.label,
    token,
    "/v1/users/me/export"
  );
  assertExportScoped(exported, me.user_id);

  const moodle = (integrations.integrations || []).find((item) => item.id === "moodle");
  if (!moodle) {
    fail(`Moodle integration row missing for ${account.label}`);
  }
  if (!Array.isArray(pressure.items)) {
    fail(`academic pressure payload malformed for ${account.label}`);
  }
  if (typeof summary.total_tasks !== "number") {
    fail(`account data summary malformed for ${account.label}`);
  }

  if (!me.is_operator) {
    await assertForbidden(token, "/v1/admin/dashboard");
    await assertForbidden(token, "/v1/admin/feedback");
    await assertForbidden(token, "/v1/jarvis/health");
  }

  if (failedResponses.length) {
    fail(`Pulse loaded with server errors for ${account.label}`, failedResponses);
  }

  await context.close();
  return {
    label: account.label,
    user_ref: userRef(me.user_id),
    is_operator: Boolean(me.is_operator),
    moodle_status: moodle.status,
    moodle_ws_connected: Boolean(moodle.ws_connected),
    pressure_items: pressure.items.length,
    export_tasks: (exported.tasks || []).length,
  };
}

const browser = await chromium.launch({ headless: true });
try {
  const results = [];
  for (const account of accounts) {
    results.push(await smokeAccount(browser, account));
  }
  if (!results.some((result) => !result.is_operator)) {
    fail("no non-operator account was available for operator-route smoke");
  }
  console.log(JSON.stringify({ ok: true, checked: results }, null, 2));
} catch (error) {
  console.error(
    JSON.stringify(
      {
        ok: false,
        error: error.message,
        detail: error.detail ?? null,
      },
      null,
      2
    )
  );
  process.exitCode = 1;
} finally {
  await browser.close();
}
