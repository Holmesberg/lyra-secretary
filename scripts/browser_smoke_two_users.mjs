#!/usr/bin/env node
import {
  apiFetch as helperApiFetch,
  frontendRequire,
  parseAndExpandCookies,
  resolveBackendTokenFromContext,
  userRef,
} from "./browser_auth_helpers.mjs";

const { chromium } = frontendRequire("playwright");

const frontendOrigin = process.env.LYRA_FRONTEND_ORIGIN || "http://localhost:3000";
const apiOrigin = process.env.LYRA_API_ORIGIN || "http://localhost:8000";
const CLOCK_SKEW_RETRY_MS = 2_000;

const accounts = [
  {
    label: "operator",
    cookieHeader: process.env.LYRA_COOKIE_ALINASSERSABRY || "",
    expectOperator: true,
  },
  {
    label: "holmesberg",
    cookieHeader:
      process.env.LYRA_COOKIE_HOLMESBERG
      || process.env.LYRA_COOKIE_MORIARTY
      || "",
    expectOperator: false,
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
  let result = await apiFetchForConfiguredApi(token, path);
  const retryableClockSkew = result.response.status === 401
    && /not yet valid \(iat\)/i.test(JSON.stringify(result.body || {}));
  if (retryableClockSkew) {
    await new Promise((resolve) => setTimeout(resolve, CLOCK_SKEW_RETRY_MS));
    result = await apiFetchForConfiguredApi(token, path);
  }
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

async function suppressApiOnlyPressureProbe(accountLabel, token, pressure) {
  if (!pressure?.exposure_id) {
    fail(`${accountLabel}: pressure map response omitted exposure decision`);
  }
  const result = await apiFetchForConfiguredApi(
    token,
    `/v1/exposures/${encodeURIComponent(pressure.exposure_id)}/ack/suppress`,
    {
      method: "POST",
      body: JSON.stringify({
        suppression_reason: "client_discarded_before_render",
      }),
    },
  );
  if (!result.response.ok || !["suppressed", "already_suppressed"].includes(result.body?.status)) {
    fail(`${accountLabel}: pressure map API-only probe was not suppressed`, {
      status: result.response.status,
      body: result.body,
    });
  }
}

async function assertGoneOrNotFound(token, path) {
  const result = await apiFetchForConfiguredApi(token, path);
  if (![404, 410].includes(result.response.status)) {
    fail(`expected removed legacy route for ${path}`, {
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

  let token = null;
  try {
    token = await resolveBackendTokenFromContext(context, frontendOrigin);
  } catch (error) {
    fail(`no backend token resolved for ${account.label}`, {
      frontendOrigin,
      ...(error.detail || {}),
      parsedCookieNames: cookies.map((cookie) => cookie.name),
    });
  }

  const me = await assertOkApiForAccount(account.label, token, "/v1/users/me");
  if (Boolean(me.is_operator) !== account.expectOperator) {
    fail(`unexpected operator flag for ${account.label}`, {
      expected: account.expectOperator,
      actual: Boolean(me.is_operator),
    });
  }
  const integrations = await assertOkApiForAccount(account.label, token, "/v1/integrations");
  let pressure = null;
  if (!me.is_operator) {
    pressure = await assertOkApiForAccount(
      account.label,
      token,
      "/v1/academic/pressure-map?horizon_days=14"
    );
    await suppressApiOnlyPressureProbe(account.label, token, pressure);
  }
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
  if (!me.is_operator && !Array.isArray(pressure?.items)) {
    fail(`academic pressure payload malformed for ${account.label}`);
  }
  if (typeof summary.total_tasks !== "number") {
    fail(`account data summary malformed for ${account.label}`);
  }

  if (me.is_operator) {
    await assertOkApiForAccount(account.label, token, "/v1/operator/dashboard");
    await assertOkApiForAccount(account.label, token, "/v1/analytics/output_surfaces/diagnostics");
    await assertGoneOrNotFound(token, "/v1/admin/dashboard");
    await assertGoneOrNotFound(token, "/v1/jarvis/health");
  } else {
    await assertForbidden(token, "/v1/operator/dashboard");
    await assertForbidden(token, "/v1/admin/feedback");
    await assertGoneOrNotFound(token, "/v1/admin/dashboard");
    await assertGoneOrNotFound(token, "/v1/jarvis/health");
  }

  await context.close();
  return {
    label: account.label,
    user_ref: userRef(me.user_id),
    is_operator: Boolean(me.is_operator),
    moodle_status: moodle.status,
    moodle_ws_connected: Boolean(moodle.ws_connected),
    pressure_items: pressure?.items?.length ?? null,
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
  if (!results.some((result) => result.is_operator)) {
    fail("no operator account was available for operator-route smoke");
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
