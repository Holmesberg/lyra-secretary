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
const syntheticNotificationIds = new Set();
const renderedAckDomProofs = [];
const ackRequestProofs = [];
const forcedRenderedAckFailures = new Set();
let failFirstRenderedAckFor = null;
let preflight = null;

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

async function withTimeout(description, promise, timeoutMs) {
  let timeout;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timeout = setTimeout(
          () => reject(new Error(`${description} exceeded ${timeoutMs}ms`)),
          timeoutMs
        );
      }),
    ]);
  } finally {
    clearTimeout(timeout);
  }
}

function redactedLifecycle(row) {
  if (!row) return null;
  return {
    notification_id: row.notification_id,
    status: row.status,
    reserved_at: row.reserved_at ?? null,
    rendered_at: row.rendered_at ?? null,
    acted_at: row.acted_at ?? null,
    dismissed_at: row.dismissed_at ?? null,
    expired_at: row.expired_at ?? null,
    lost_unrendered_at: row.lost_unrendered_at ?? null,
  };
}

async function exportedLifecycleRows(token, notificationIds) {
  const exported = await apiFetch(apiOrigin, token, "/v1/users/me/export");
  const wanted = new Set(notificationIds);
  return (exported.body?.notification_lifecycle_events || []).filter((row) => (
    wanted.has(row.notification_id)
  ));
}

function successfulAck(notificationId, eventType) {
  return ackRequestProofs.find((proof) => (
    proof.event_type === eventType
    && proof.status >= 200
    && proof.status < 300
    && proof.notification_ids.includes(notificationId)
  )) || null;
}

async function waitForSuccessfulAck(notificationId, eventType) {
  return poll(`notification ${notificationId} ACK -> ${eventType}`, async () => (
    successfulAck(notificationId, eventType)
  ));
}

async function proveQueuedWithoutRender(token, notificationIds, label) {
  const pending = await apiFetch(apiOrigin, token, "/v1/notifications/web/pending");
  const pendingIds = new Set(
    (pending.body?.notifications || []).map((row) => row.notification_id)
  );
  const ok = notificationIds.every((id) => (
    pendingIds.has(id) && !successfulAck(id, "rendered")
  ));
  addCheck(
    `${label} queue insertion has no browser-render truth`,
    ok,
    { notification_ids: notificationIds, pending_before_mount: ok }
  );
}

async function syntheticPendingIds(token) {
  const pending = await apiFetch(apiOrigin, token, "/v1/notifications/web/pending");
  return (pending.body?.notifications || [])
    .map((row) => row.notification_id)
    .filter((id) => syntheticNotificationIds.has(id));
}

async function push(token, payload) {
  syntheticNotificationIds.add(payload.notification_id);
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
let token = null;
let page = null;
let failureContext = null;
let cleanupProof = {
  ok: false,
  pending_before: [],
  terminalized_as_lost_unrendered: [],
  pending_after: [],
};
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  await context.addCookies(parseAndExpandCookies(cookie, frontendOrigin));
  token = await resolveBackendTokenFromContext(context, frontendOrigin);
  page = await context.newPage();

  const preflightStartedAt = Date.now();
  const topologyResponse = await withTimeout(
    "frontend topology preflight",
    fetch(`${frontendOrigin}/api/topology`),
    10_000
  );
  const topology = await topologyResponse.json();
  const healthResponse = await withTimeout(
    "backend health preflight",
    fetch(`${apiOrigin}/v1/health`),
    10_000
  );
  const me = await withTimeout(
    "account eligibility preflight",
    apiFetch(apiOrigin, token, "/v1/users/me"),
    15_000
  );
  const pendingBeforeRun = await withTimeout(
    "pending notification debt preflight",
    apiFetch(apiOrigin, token, "/v1/notifications/web/pending"),
    15_000
  );
  const exportStartedAt = Date.now();
  const exportedBeforeRun = await withTimeout(
    "export envelope preflight",
    apiFetch(apiOrigin, token, "/v1/users/me/export"),
    30_000
  );
  const exportDurationMs = Date.now() - exportStartedAt;
  const exportBytes = Buffer.byteLength(JSON.stringify(exportedBeforeRun.body || {}));
  const pendingCount = Array.isArray(pendingBeforeRun.body?.notifications)
    ? pendingBeforeRun.body.notifications.length
    : -1;
  const onboardingCompleted = Boolean(
    me.body?.onboarding_completed_at || me.body?.onboarding_completed
  );
  const hasActiveTaskHistory = Boolean(me.body?.has_active_task_history);
  const onboardingGateOpen = !onboardingCompleted || !hasActiveTaskHistory;
  if (onboardingGateOpen) {
    await page.addInitScript(() => {
      try {
        if (window.location.origin.startsWith("http")) {
          window.sessionStorage.setItem("lyra:onboarding-skip-this-session", "1");
        }
      } catch {
        // Opaque documents such as about:blank have no sessionStorage access.
      }
    });
  }
  const termsAccepted = Boolean(me.body?.terms_accepted_at);
  preflight = {
    ok: topologyResponse.ok
      && healthResponse.ok
      && me.response.ok
      && me.body?.is_operator === false
      && termsAccepted
      && pendingCount === 0
      && exportDurationMs <= 30_000
      && exportBytes <= 20_000_000,
    frontend_health: topologyResponse.status,
    backend_health: healthResponse.status,
    topology_class: topology.topology_class,
    frontend_build_id: topology.build_id,
    compiled_api_origin: topology.compiled_api_origin,
    proxy_mode: false,
    cookie_valid: me.response.ok,
    account_role: me.body?.is_operator ? "operator" : "mutable_dogfood",
    terms_accepted: termsAccepted,
    onboarding_completed: onboardingCompleted,
    has_active_task_history: hasActiveTaskHistory,
    onboarding_gate_open: onboardingGateOpen,
    onboarding_resolution: onboardingGateOpen
      ? "session_only_skip_fixture"
      : "account_ready",
    selected_calendar_range: "not_applicable",
    page_loading_completion: "checked by mounted-toast waits",
    target_surface_eligible: termsAccepted && me.body?.is_operator === false,
    existing_pending_count: pendingCount,
    existing_synthetic_lifecycle_debt_count: pendingCount,
    export_duration_ms: exportDurationMs,
    export_bytes: exportBytes,
    export_notification_lifecycle_rows:
      exportedBeforeRun.body?.notification_lifecycle_events?.length ?? null,
    timeout_envelope_ms: 30_000,
    elapsed_ms: Date.now() - preflightStartedAt,
  };
  addCheck("focused browser preflight passes before synthetic writes", preflight.ok, preflight);
  if (!preflight.ok) {
    throw new Error(`notification browser preflight failed: ${JSON.stringify(preflight)}`);
  }

  page.on("pageerror", (error) => {
    issues.push(`pageerror: ${error.message}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      if (
        forcedRenderedAckFailures.size > 0
        && message.text().includes("503 (Service Unavailable)")
      ) {
        return;
      }
      issues.push(`console: ${message.text()}`);
    }
  });
  page.on("response", async (response) => {
    if (response.url().includes("/v1/notifications/web/ack")) {
      let payload = null;
      try {
        payload = response.request().postDataJSON();
      } catch {
        payload = null;
      }
      const notificationIds = Array.isArray(payload?.notification_ids)
        ? payload.notification_ids.filter((id) => syntheticNotificationIds.has(id))
        : [];
      if (notificationIds.length > 0) {
        let responseBody = null;
        try {
          responseBody = await response.json();
        } catch {
          responseBody = null;
        }
        ackRequestProofs.push({
          event_type: payload?.event_type ?? "unknown",
          notification_ids: notificationIds,
          status: response.status(),
          acknowledged: responseBody?.acknowledged ?? null,
          forced: response.status() === 503,
        });
      }
    }
    if (response.status() < 400) return;
    if (
      response.status() === 503
      && response.url().includes("/v1/notifications/web/ack")
      && forcedRenderedAckFailures.size > 0
    ) {
      return;
    }
    issues.push(`http ${response.status()}: ${response.url()}`);
  });

  await page.route("**/v1/notifications/web/ack", async (route) => {
    const request = route.request();
    let payload = null;
    try {
      payload = request.postDataJSON();
    } catch {
      payload = null;
    }
    const notificationIds = Array.isArray(payload?.notification_ids)
      ? payload.notification_ids.filter((id) => syntheticNotificationIds.has(id))
      : [];
    if (payload?.event_type === "rendered" && notificationIds.length > 0) {
      for (const id of notificationIds) {
        const locator = page.locator(
          `[data-testid="notification-toast"][data-toast-id=${JSON.stringify(id)}]`
        );
        const count = await locator.count();
        const visible = count === 1 && await locator.first().isVisible();
        renderedAckDomProofs.push({ notification_id: id, dom_count: count, visible });
        if (!visible) {
          issues.push(`render ACK preceded visible DOM commit for ${id}`);
        }
      }
      if (
        failFirstRenderedAckFor
        && notificationIds.includes(failFirstRenderedAckFor)
        && !forcedRenderedAckFailures.has(failFirstRenderedAckFor)
      ) {
        forcedRenderedAckFailures.add(failFirstRenderedAckFor);
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "forced verifier retry" }),
        });
        return;
      }
    }
    await route.continue();
  });

  const actionId = `${runId}-acted`.slice(0, 64);
  failFirstRenderedAckFor = actionId;
  await push(token, {
    notification_id: actionId,
    type: "resume_prediction",
    task_id: `${runId}-task-action`.slice(0, 64),
    task_title: "DOGFOOD notification action",
    paused_for_minutes: 7,
    planned_minutes: 60,
  });
  await proveQueuedWithoutRender(token, [actionId], "action notification");
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const actionToast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /DOGFOOD notification action|Pick it back up/i })
    .first();
  await actionToast.waitFor({ state: "visible", timeout: 20_000 });
  const actionRendered = await waitForSuccessfulAck(actionId, "rendered");
  const actionRenderProofs = renderedAckDomProofs.filter(
    (proof) => proof.notification_id === actionId
  );
  addCheck(
    "render ACK retries after a forced first failure without losing DOM proof",
    forcedRenderedAckFailures.has(actionId)
      && actionRenderProofs.length >= 2
      && actionRenderProofs.every((proof) => proof.visible)
      && Boolean(actionRendered),
    {
      forced_failure: forcedRenderedAckFailures.has(actionId),
      attempts: actionRenderProofs,
      acknowledged_request: actionRendered,
    }
  );
  await screenshot(page, "action-toast-visible");
  await actionToast.getByRole("link", { name: /view details/i }).click({ timeout: 5_000 });
  const acted = await waitForSuccessfulAck(actionId, "acted");
  addCheck(
    "notification details click records acted lifecycle",
    Boolean(acted),
    acted
  );

  await page.goto("about:blank");
  const expiryId = `${runId}-expired`.slice(0, 64);
  await push(token, {
    notification_id: expiryId,
    type: "pause_prediction",
    task_id: `${runId}-task-expiry`.slice(0, 64),
  });
  await proveQueuedWithoutRender(token, [expiryId], "expiry notification");
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const expiryToast = page
    .locator('[data-testid="notification-toast"], [role="status"]')
    .filter({ hasText: /open for a while/i })
    .first();
  await expiryToast.waitFor({ state: "visible", timeout: 20_000 });
  await screenshot(page, "expiry-toast-visible");
  await expiryToast.waitFor({ state: "hidden", timeout: 12_000 });
  const expired = await waitForSuccessfulAck(expiryId, "expired");
  addCheck(
    "notification auto-dismiss records expired lifecycle",
    Boolean(expired),
    expired
  );

  await page.goto("about:blank");
  const unsupportedId = `${runId}-unsupported`.slice(0, 64);
  await push(token, {
    notification_id: unsupportedId,
    type: "dogfood_unsupported",
  });
  await proveQueuedWithoutRender(token, [unsupportedId], "unsupported notification");
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const unsupported = await waitForSuccessfulAck(unsupportedId, "lost_unrendered");
  const unsupportedDomCount = await page.locator(
    `[data-testid="notification-toast"][data-toast-id=${JSON.stringify(unsupportedId)}]`
  ).count();
  addCheck(
    "unsupported notification terminates without render truth",
    unsupportedDomCount === 0
      && Boolean(unsupported)
      && !renderedAckDomProofs.some((proof) => proof.notification_id === unsupportedId),
    { dom_count: unsupportedDomCount, acknowledged_request: unsupported }
  );

  await page.goto("about:blank");
  const duplicateIds = [
    `${runId}-duplicate-a`.slice(0, 64),
    `${runId}-duplicate-b`.slice(0, 64),
  ];
  const duplicateTaskId = `${runId}-duplicate-task`.slice(0, 64);
  for (const id of duplicateIds) {
    await push(token, {
      notification_id: id,
      type: "resume_prediction",
      task_id: duplicateTaskId,
      task_title: "DOGFOOD duplicate notification",
      paused_for_minutes: 9,
    });
  }
  await proveQueuedWithoutRender(token, duplicateIds, "duplicate notifications");
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const duplicateSplit = await poll("duplicate lifecycle split", async () => {
    const rendered = duplicateIds.filter((id) => successfulAck(id, "rendered"));
    const lost = duplicateIds.filter((id) => successfulAck(id, "lost_unrendered"));
    return rendered.length === 1 && lost.length === 1
      ? { rendered_id: rendered[0], lost_unrendered_id: lost[0] }
      : null;
  });
  addCheck(
    "same-key duplicates produce one mounted toast and one honest non-render terminal",
    Boolean(duplicateSplit),
    duplicateSplit
  );
  const duplicateToast = page.locator(
    `[data-testid="notification-toast"][data-toast-id=${JSON.stringify(
      duplicateSplit.rendered_id
    )}]`
  );
  await duplicateToast.waitFor({ state: "visible", timeout: 20_000 });
  await duplicateToast.getByTestId("notification-toast-dismiss").click();
  await waitForSuccessfulAck(duplicateSplit.rendered_id, "dismissed");

  await page.goto("about:blank");
  const capacityIds = Array.from({ length: 4 }, (_, index) => (
    `${runId}-capacity-${index + 1}`.slice(0, 64)
  ));
  for (const [index, id] of capacityIds.entries()) {
    await push(token, {
      notification_id: id,
      type: "resume_prediction",
      task_id: `${runId}-capacity-task-${index + 1}`.slice(0, 64),
      task_title: `DOGFOOD capacity notification ${index + 1}`,
      paused_for_minutes: 11 + index,
    });
  }
  await proveQueuedWithoutRender(token, capacityIds, "capacity notifications");
  await page.goto(`${frontendOrigin}/pulse`, { waitUntil: "domcontentloaded" });
  const visibleToasts = page.locator('[data-testid="notification-toast"]');
  await poll("three-toast capacity", async () => (
    await visibleToasts.count() === 3 ? true : null
  ));
  const initialCapacitySplit = await poll("capacity lifecycle split", async () => {
    const renderedIds = capacityIds.filter((id) => successfulAck(id, "rendered"));
    return renderedIds.length === 3
      ? {
          rendered_ids: renderedIds,
          deferred_id: capacityIds.find((id) => !renderedIds.includes(id)),
        }
      : null;
  });
  addCheck(
    "toast capacity leaves the fourth notification pending without fabricated render",
    Boolean(initialCapacitySplit.deferred_id) && await visibleToasts.count() === 3,
    initialCapacitySplit
  );
  await screenshot(page, "capacity-three-visible");
  const firstCapacityRenderedId = initialCapacitySplit.rendered_ids[0];
  const firstCapacityToast = page.locator(
    `[data-testid="notification-toast"][data-toast-id=${JSON.stringify(
      firstCapacityRenderedId
    )}]`
  );
  await firstCapacityToast.getByTestId("notification-toast-dismiss").click();
  await waitForSuccessfulAck(firstCapacityRenderedId, "dismissed");
  const deferredRendered = await waitForSuccessfulAck(
    initialCapacitySplit.deferred_id,
    "rendered"
  );
  const deferredToast = page.locator(
    `[data-testid="notification-toast"][data-toast-id=${JSON.stringify(
      initialCapacitySplit.deferred_id
    )}]`
  );
  await deferredToast.waitFor({ state: "visible", timeout: 20_000 });
  addCheck(
    "deferred fourth notification renders only after a visible slot opens",
    Boolean(deferredRendered),
    deferredRendered
  );
  for (const id of capacityIds) {
    const toast = page.locator(
      `[data-testid="notification-toast"][data-toast-id=${JSON.stringify(id)}]`
    );
    if (await toast.isVisible()) {
      await toast.getByTestId("notification-toast-dismiss").click();
      await toast.waitFor({ state: "hidden", timeout: 5_000 });
    }
  }
  for (const id of capacityIds) {
    await waitForSuccessfulAck(id, "dismissed");
  }

  const finalLifecycleRows = await exportedLifecycleRows(
    token,
    [...syntheticNotificationIds]
  );
  const finalLifecycleById = new Map(
    finalLifecycleRows.map((row) => [row.notification_id, row])
  );
  const expectedFinalStatuses = new Map([
    [actionId, "acted"],
    [expiryId, "expired"],
    [unsupportedId, "lost_unrendered"],
    [duplicateSplit.rendered_id, "dismissed"],
    [duplicateSplit.lost_unrendered_id, "lost_unrendered"],
    ...capacityIds.map((id) => [id, "dismissed"]),
  ]);
  const exactLifecycleOk = [...expectedFinalStatuses].every(([id, status]) => {
    const row = finalLifecycleById.get(id);
    if (!row || row.status !== status) return false;
    if (status === "lost_unrendered") {
      return Boolean(row.lost_unrendered_at) && !row.rendered_at;
    }
    const terminalField = `${status}_at`;
    return Boolean(row.rendered_at && row[terminalField]);
  });
  addCheck(
    "final export proves exact affected-row lifecycle outcomes",
    exactLifecycleOk
      && finalLifecycleRows.length === syntheticNotificationIds.size,
    finalLifecycleRows.map(redactedLifecycle)
  );

  const pendingIds = await syntheticPendingIds(token);
  addCheck(
    "notification lifecycle test leaves no synthetic pending rows",
    pendingIds.length === 0,
    { pending_notification_ids: pendingIds }
  );
  addCheck(
    "every rendered ACK was issued with exactly one visible matching toast",
    renderedAckDomProofs.length > 0
      && renderedAckDomProofs.every((proof) => proof.visible && proof.dom_count === 1),
    renderedAckDomProofs
  );

  result = {
    ok: checks.every((check) => check.ok) && issues.length === 0,
    run_id: runId,
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
    output_dir: outDir,
    preflight,
    checks,
    issues,
    rendered_ack_dom_proofs: renderedAckDomProofs,
    ack_request_proofs: ackRequestProofs,
  };
} catch (error) {
  if (page && !page.isClosed()) {
    try {
      failureContext = {
        page_url: page.url(),
        document_ready_state: await page.evaluate(() => document.readyState),
        notification_toast_count: await page.locator(
          '[data-testid="notification-toast"]'
        ).count(),
        app_navigation_count: await page.locator('a[href="/pulse"]').count(),
        dialog_count: await page.locator('[role="dialog"]').count(),
        session_onboarding_skip: await page.evaluate(() => (
          window.sessionStorage.getItem("lyra:onboarding-skip-this-session") === "1"
        )),
        screenshot: await screenshot(page, "failure-context"),
      };
    } catch (contextError) {
      failureContext = {
        capture_error: contextError instanceof Error
          ? contextError.message
          : String(contextError),
      };
    }
  }
  result = {
    ok: false,
    run_id: runId,
    frontend_origin: frontendOrigin,
    api_origin: apiOrigin,
    output_dir: outDir,
    preflight,
    failure_context: failureContext,
    error: error instanceof Error ? error.message : String(error),
    checks,
    issues,
    rendered_ack_dom_proofs: renderedAckDomProofs,
    ack_request_proofs: ackRequestProofs,
  };
} finally {
  if (token) {
    try {
      const pendingBefore = await syntheticPendingIds(token);
      if (pendingBefore.length > 0) {
        const cleanup = await apiFetch(apiOrigin, token, "/v1/notifications/web/ack", {
          method: "POST",
          body: JSON.stringify({
            notification_ids: pendingBefore,
            event_type: "lost_unrendered",
          }),
        });
        if (!cleanup.response.ok) {
          throw new Error(`cleanup ACK failed: ${cleanup.response.status}`);
        }
      }
      const pendingAfter = await syntheticPendingIds(token);
      cleanupProof = {
        ok: pendingAfter.length === 0,
        pending_before: pendingBefore,
        terminalized_as_lost_unrendered: pendingBefore,
        pending_after: pendingAfter,
        retained_terminal_rows: syntheticNotificationIds.size,
        retained_rows_classification: "explicit synthetic terminal lifecycle evidence",
      };
    } catch (error) {
      cleanupProof = {
        ok: false,
        pending_before: [],
        terminalized_as_lost_unrendered: [],
        pending_after: [],
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
  await browser.close();
  result.cleanup = cleanupProof;
  result.issues = issues;
  result.ok = Boolean(result.ok && cleanupProof.ok && issues.length === 0);
}

fs.writeFileSync(path.join(outDir, "result.json"), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
if (!result.ok) {
  process.exit(1);
}
