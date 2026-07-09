import fs from "node:fs";
import path from "node:path";

import {
  apiFetch,
  parseAndExpandCookies,
  resolveBackendTokenFromContext,
  frontendRequire,
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
const runId = args.get("run-id") || `notification-lifecycle-${Date.now()}`;
const cookie = process.env.LYRA_COOKIE_HOLMESBERG || "";
if (cookie.length < 100) {
  throw new Error("LYRA_COOKIE_HOLMESBERG is missing or looks truncated.");
}

const outDir = path.join(
  "tmp",
  "browser-notification-lifecycle",
  new Date().toISOString().replaceAll(":", "-").replace(".", "-")
);
fs.mkdirSync(outDir, { recursive: true });

const checks = [];
const issues = [];

function addCheck(name, ok, detail = null) {
  checks.push({ name, ok: Boolean(ok), detail });
}

async function screenshot(page, name) {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function poll(description, fn, timeoutMs = 25_000, intervalMs = 1_000) {
  const start = Date.now();
  let last = null;
  while (Date.now() - start < timeoutMs) {
    last = await fn();
    if (last) return last;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error(`${description} timed out; last=${JSON.stringify(last)}`);
}

async function lifecycleRow(token, notificationId, expectedStatus) {
  return poll(`notification ${notificationId} -> ${expectedStatus}`, async () => {
    const exported = await apiFetch(apiOrigin, token, "/v1/users/me/export");
    const rows = exported.body?.notification_lifecycle_events || [];
    return rows.find((row) => (
      row.notification_id === notificationId
      && row.status === expectedStatus
      && row.rendered_at
    )) || null;
  });
}

async function push(token, payload) {
  const response = await apiFetch(apiOrigin, token, "/v1/notifications/push", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!response.response.ok) {
    throw new Error(`push ${payload.notification_id} failed: ${response.response.status}`);
  }
}

const browser = await chromium.launch({ headless: true });
let result;
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  await context.addCookies(parseAndExpandCookies(cookie, frontendOrigin));
  const token = await resolveBackendTokenFromContext(context, frontendOrigin);
  const page = await context.newPage();

  const actionId = `${runId}-acted`.slice(0, 64);
  await push(token, {
    notification_id: actionId,
    type: "resume_prediction",
    task_id: `${runId}-task-action`.slice(0, 64),
    task_title: "DOGFOOD notification action",
    paused_for_minutes: 7,
    planned_minutes: 60,
  });
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const actionToast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /DOGFOOD notification action|Pick it back up/i })
    .first();
  await actionToast.waitFor({ state: "visible", timeout: 20_000 });
  await screenshot(page, "action-toast-visible");
  await page.getByRole("link", { name: /view details/i }).first().click({ timeout: 5_000 });
  const acted = await lifecycleRow(token, actionId, "acted");
  addCheck("notification details click records acted lifecycle", Boolean(acted?.acted_at), acted);

  const expiryId = `${runId}-expired`.slice(0, 64);
  await push(token, {
    notification_id: expiryId,
    type: "pause_prediction",
    task_id: `${runId}-task-expiry`.slice(0, 64),
  });
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const expiryToast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /open for a while/i })
    .first();
  await expiryToast.waitFor({ state: "visible", timeout: 20_000 });
  await screenshot(page, "expiry-toast-visible");
  await expiryToast.waitFor({ state: "hidden", timeout: 12_000 });
  const expired = await lifecycleRow(token, expiryId, "expired");
  addCheck("notification auto-dismiss records expired lifecycle", Boolean(expired?.expired_at), expired);

  const pending = await apiFetch(apiOrigin, token, "/v1/notifications/web/pending");
  addCheck("notification action/expiry test leaves no synthetic pending rows", !(
    Array.isArray(pending.body?.notifications)
    && pending.body.notifications.some((row) => (
      row.notification_id === actionId || row.notification_id === expiryId
    ))
  ), pending.body);

  result = {
    ok: checks.every((check) => check.ok),
    run_id: runId,
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
    output_dir: outDir,
    checks,
    issues,
  };
} catch (error) {
  result = {
    ok: false,
    run_id: runId,
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
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
