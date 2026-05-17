#!/usr/bin/env node
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const frontendRequire = createRequire(path.join(repoRoot, "frontend", "package.json"));
const { chromium } = frontendRequire("playwright");

const frontendOrigin = process.env.LYRA_FRONTEND_ORIGIN || "http://localhost:3000";
const apiOrigin = process.env.LYRA_API_ORIGIN || "http://localhost:8000";

const accounts = [
  {
    label: "asabryhafez",
    cookieHeader: process.env.LYRA_COOKIE_ASABRYHAFEZ || "",
  },
  {
    label: "moriarty",
    cookieHeader: process.env.LYRA_COOKIE_MORIARTY || "",
  },
];

function fail(message, detail = undefined) {
  const err = new Error(message);
  err.detail = detail;
  throw err;
}

function userRef(userId) {
  return createHash("sha256")
    .update(String(userId))
    .digest("hex")
    .slice(0, 12);
}

function parseCookieHeader(header) {
  const pairs = [];
  for (const rawPart of header.split(";")) {
    const part = rawPart.trim();
    if (!part || !part.includes("=")) continue;
    const index = part.indexOf("=");
    const name = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (!name || !value) continue;
    pairs.push({ name, value });
  }
  if (!pairs.length && header.trim()) {
    pairs.push({
      name: "next-auth.session-token",
      value: header.trim(),
    });
  }
  return pairs;
}

function expandNextAuthCookieAliases(cookies) {
  const out = [];
  const seen = new Set();

  function add(name, value) {
    const key = `${name}=${value}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ name, value, url: frontendOrigin });
  }

  for (const cookie of cookies) {
    if (
      !frontendOrigin.startsWith("http://")
      || (
        !cookie.name.startsWith("__Secure-")
        && !cookie.name.startsWith("__Host-")
      )
    ) {
      add(cookie.name, cookie.value);
    }
    if (cookie.name.startsWith("__Secure-")) {
      add(cookie.name.replace("__Secure-", ""), cookie.value);
    }
    if (cookie.name.startsWith("__Host-")) {
      add(cookie.name.replace("__Host-", ""), cookie.value);
    }
  }
  return out;
}

async function apiFetch(token, path, init = {}) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(init.headers || {}),
  };
  const response = await fetch(`${apiOrigin}${path}`, { ...init, headers });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { response, body };
}

async function assertOkApi(token, path) {
  const result = await apiFetch(token, path);
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
  const result = await apiFetch(token, path);
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
  const cookies = expandNextAuthCookieAliases(parseCookieHeader(account.cookieHeader));
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

  const session = await page.evaluate(async () => {
    const response = await fetch("/api/auth/session");
    return response.json();
  });
  const token = session?.backendToken;
  if (!token) {
    fail(`no backend token resolved for ${account.label}`, {
      sessionKeys: Object.keys(session || {}),
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
