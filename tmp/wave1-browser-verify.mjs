import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const { chromium } = playwright;
const require = createRequire(import.meta.url);
const { encode } = require("../frontend/node_modules/next-auth/jwt");

const port = process.env.WAVE1_FRONTEND_PORT || "3211";
const origin = `http://127.0.0.1:${port}`;
const apiOrigin = "http://localhost:8000";
const outDir = new URL("./", import.meta.url);
const outPath = (name) => fileURLToPath(new URL(name, outDir));
const nextAuthSecret = process.env.NEXTAUTH_SECRET || "wave1-local-secret-value-at-least-32-chars";

const now = new Date().toISOString();
const ackBodies = [];
let pendingServed = false;
let operatorMode = true;

function corsHeaders() {
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-headers": "authorization, content-type, x-idempotency-key",
    "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "access-control-allow-credentials": "true",
  };
}

function json(body, status = 200) {
  return {
    status,
    contentType: "application/json",
    headers: corsHeaders(),
    body: JSON.stringify(body),
  };
}

function mePayload() {
  return {
    user_id: 9001,
    email: "wave1-browser@example.test",
    terms_accepted_at: now,
    onboarding_completed_at: now,
    has_active_task_history: true,
    tutorial_completed_at: now,
    tutorial_skipped_at: null,
    archetype_survey_eligible: false,
    archetype_assignment_completed: true,
    archetype_retrofit_dismissed_at: now,
    archetype_id: null,
    executed_session_count: 5,
    google_calendar_connected: false,
    is_operator: operatorMode,
  };
}

function pressureMapPayload() {
  return {
    generated_at_utc: now,
    horizon_days: 14,
    headline: "No urgent pressure detected",
    pressure_summary: "No active obligations in this verification fixture.",
    items: [],
    compression_points: [],
    recovery_options: [],
    coverage_questions: [],
    capacity_context: {
      known_busy_minutes: 0,
      planned_lyra_minutes: 0,
      estimated_academic_low_minutes: 0,
      estimated_academic_high_minutes: 0,
      google_calendar_connected: false,
      caveat: "Verification fixture.",
    },
    estimated_low_minutes: 0,
    estimated_high_minutes: 0,
    source_summary: {
      deadlines_total: 0,
      external_obligation_count: 0,
      native_obligation_count: 0,
      academic_task_count: 0,
      study_task_count: 0,
      academic_task_minutes: 0,
      study_task_minutes: 0,
      google_calendar_connected: false,
      calendar_busy_minutes: 0,
      planned_lyra_minutes: 0,
    },
    methodology: [],
    warnings: [],
    exposure_id: null,
  };
}

function operatorPayload() {
  const meta = { basis: "direct", confidence: "medium", readiness_impact: "warning" };
  return {
    generated_at: now,
    data_freshness: {
      ...meta,
      source_windows: {
        tasks_last_seen_at: now,
        sessions_last_seen_at: now,
        notifications_last_seen_at: now,
        exposures_last_seen_at: now,
        providers_last_seen_at: null,
      },
      stale_sources: ["providers_last_seen_at"],
    },
    metric_confidence: {
      retention: "medium",
      login_frequency: "not_instrumented",
      clean_trace_ratio: "high",
      notification_lifecycle: "medium",
      provider_integrity: "medium",
      product_loop_funnel: "medium",
      state_invariants: "high",
    },
    meaningful_activity_definition: {
      basis: "contract",
      confidence: "high",
      readiness_impact: "informational",
      included_events: ["task_created", "timer_started", "timer_stopped"],
      excluded_events: ["login_only", "page_refresh", "background_sync"],
    },
    cohort_readiness: {
      basis: "derived",
      confidence: "medium",
      readiness_impact: "blocker",
      status: "yellow",
      blockers: [],
      warnings: ["notification_lifecycle_under_verification"],
      minimum_fix_set: ["verify_notification_lifecycle_counts"],
      safe_to_invite_more_users: false,
      rationale: "Dogfood only until Wave 1 lifecycle verification is accepted.",
    },
    cohort_segments: { ...meta, operator_users_excluded: 1, trusted_users: 1, new_users_7d: 1, activated_users: 1, dormant_users: 0, users_with_dirty_data_only: 0, users_with_clean_sessions: 1, users_with_open_stale_sessions: 0 },
    cohort: { ...meta, non_operator_users: 1, trusted_users_total: 1, activated_users: 1, meaningful_active_users_7d: 1, weekly_active_users: 1, dormant_users_7d: 0, dormant_users_14d: 0 },
    retention: { ...meta, d1_return_rate: null, d7_return_rate: null, d14_return_rate: null, returning_today: 1, returning_7d: 1, returning_14d: 1 },
    activity_frequency: { ...meta, active_days_last_7d: 1, active_days_last_14d: 1, median_days_between_activity: null, login_frequency_status: "not_instrumented", proxy: "active_days_from_explicit_lyra_events" },
    activation_quality: { ...meta, first_task_created_count: 1, first_timer_started_count: 1, first_clean_stop_count: 1, first_pressure_map_action_count: 0, first_recovery_action_count: 0, median_time_to_first_clean_loop: null },
    product_loop_funnel: { ...meta, pulse_opened: null, quick_capture_used: null, brain_dump_submitted: null, preview_confirmed: null, task_created: 1, obligation_bound: 0, pressure_map_opened: 0, recovery_plan_previewed: null, recovery_plan_confirmed: 0, timer_started: 1, timer_stopped_cleanly: 1, recovery_surface_seen: 0, insight_seen: 0, returned_after_24h: 0, dropoff_points: [] },
    measurement_integrity: { ...meta, clean_trace_ratio: 1, dirty_trace_count: 0, dirty_reasons: { auto_closed: 0, stale_recovered: 0, retroactive: 0, corrected: 0, voided: 0, missing_timestamps: 0, impossible_duration: 0, unknown_exposure: 0, provider_only: 0, exposure_contaminated: 0 }, analytic_blockers: [], calibration_safe: true, insights_safe: true },
    state_invariants: { ...meta, duplicate_open_sessions: 0, executing_tasks_without_open_session: 0, paused_tasks_without_open_session: 0, executed_tasks_missing_start_or_end: 0, open_sessions_for_executed_tasks: 0, stale_reentry_candidates: 0, invalid_recovery_actions_seen: null },
    notification_lifecycle: {
      ...meta,
      web_created: 2,
      web_queued: 0,
      web_reserved: 0,
      web_rendered: 1,
      web_acted: 0,
      web_dismissed: ackBodies.some((b) => b.event_type === "dismissed") ? 1 : 0,
      web_expired: 0,
      web_lost_unrendered: 1,
      duplicate_prompt_count: 0,
      render_without_exposure_count: 0,
      exposure_without_render_count: 0,
      operator_created: 1,
      operator_pending: 1,
      not_instrumented_fields: [],
      redis_errors: [],
    },
    provider_integrity: { ...meta, provider_rows_total: 0, provider_rows_missing_provenance: 0, provider_completion_candidates: 0, provider_truth_violations: 0, duplicate_import_candidates: 0, sync_failures_24h: 0, user_visible_provider_errors_24h: 0 },
    reliability: { ...meta, user_visible_error_count_24h: 0, failed_api_count_24h: null, calendar_token_warning_user_visible_count: 0, task_state_rejection_count: null, export_success_count: null, delete_success_count: null },
    privacy_boundary: { ...meta, raw_task_titles_exposed: false, raw_emails_exposed: false, provider_tokens_exposed: false, raw_provider_urls_exposed: false, user_debug_mode_enabled: false },
    bug_watchlist: { ...meta, k01_calendar_warning_leak: "pass", k02_timer_overflow_duplicate: "pass", k03_invalid_mark_done_executed: "unknown", k04_parked_25h_stale: "pass", k05_pulse_quick_capture_anchor: "unknown" },
    users: [{ user_id: 9001, first_name: "Wave", name_source: "google_profile", email_hash: "wave1hash", created_at: now, last_meaningful_activity_at: now, active_days_7d: 1, active_days_14d: 1, task_count: 1, executed_task_count: 1, stopwatch_session_count: 1, clean_trace_ratio: 1, open_timer_count: 0, paused_over_72h_count: 0, last_loop_stage: "clean_loop" }],
    operator_recommendations: [{ severity: "warning", message: "verify notification lifecycle counts", suggested_action: "Confirm rendered and lost-unrendered states are distinct.", related_section: "notification_lifecycle", blocks_cohort_expansion: false }],
    derived_metrics: { full_loop_users: 1, full_loop_completion_rate: 1, timer_start_to_clean_stop_rate: 1, safe_to_invite_more_users: false },
  };
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  page.on("console", (msg) => {
    if (msg.type() === "error") console.error(`[browser console] ${msg.text()}`);
  });

  await page.route("**/api/auth/session**", async (route) => {
    await route.fulfill(json({
      user: { name: "Wave One", email: "wave1-browser@example.test", image: null },
      expires: "2099-01-01T00:00:00.000Z",
      backendToken: "wave1-local-token",
    }));
  });

  const sessionCookie = await encode({
    secret: nextAuthSecret,
    token: {
      sub: "wave1-google-sub",
      email: "wave1-browser@example.test",
      name: "Wave One",
      given_name: "Wave",
      backendToken: "wave1-local-token",
    },
  });
  await page.context().addCookies([
    {
      name: "next-auth.session-token",
      value: sessionCookie,
      url: origin,
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  await page.route(`${apiOrigin}/v1/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders(), body: "" });
      return;
    }
    if (url.pathname === "/v1/notifications/web/pending") {
      if (pendingServed) {
        await route.fulfill(json({ notifications: [], count: 0 }));
        return;
      }
      pendingServed = true;
      await route.fulfill(json({
        notifications: [
          {
            type: "timer_overflow",
            notification_id: "wave1-timer",
            elapsed_minutes: 35.82404850000967,
            planned_minutes: 30,
            task_id: "wave1-task",
            session_id: "wave1-session",
            surface_id: "worker.timer_overflow",
            exposure_id: "wave1-exposure",
          },
          {
            type: "operator_alert",
            notification_id: "wave1-operator",
            message: "[alert] [scheduler.timer-overflow] Reply with 'done' 345.82404850000967",
          },
        ],
        count: 2,
      }));
      return;
    }
    if (url.pathname === "/v1/notifications/web/ack") {
      ackBodies.push(request.postDataJSON());
      await route.fulfill(json({ acknowledged: request.postDataJSON()?.notification_ids?.length ?? 0 }));
      return;
    }
    if (url.pathname === "/v1/users/me") {
      await route.fulfill(json(mePayload()));
      return;
    }
    if (url.pathname === "/v1/tasks/query") {
      await route.fulfill(json({ tasks: [], total: 0 }));
      return;
    }
    if (url.pathname === "/v1/deadlines") {
      await route.fulfill(json({ deadlines: [], total: 0 }));
      return;
    }
    if (url.pathname === "/v1/integrations") {
      await route.fulfill(json({ integrations: [] }));
      return;
    }
    if (url.pathname === "/v1/academic/pressure-map") {
      await route.fulfill(json(pressureMapPayload()));
      return;
    }
    if (url.pathname === "/v1/operator/dashboard") {
      await route.fulfill(json(operatorPayload()));
      return;
    }
    if (url.pathname.includes("/ack/render")) {
      await route.fulfill(json({ ok: true }));
      return;
    }
    await route.fulfill(json({ ok: true }));
  });

  await page.goto(`${origin}/pulse#quick-capture`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);
  await fs.writeFile(new URL("wave1-pulse-debug.txt", outDir), await page.locator("body").innerText());
  await page.screenshot({ path: outPath("wave1-pulse-debug.png"), fullPage: true });
  await page.getByText("Task is past its planned window").waitFor({ timeout: 15_000 });
  const bodyText = await page.locator("body").innerText();
  if (!bodyText.includes("Task is past its planned window (36m active; planned 30m). Open it to stop or correct.")) {
    throw new Error("User-safe timer-overflow toast did not render with rounded minutes.");
  }
  for (const forbidden of ["Reply with", "[alert]", "345.82404850000967", "[scheduler.timer-overflow]"]) {
    if (bodyText.includes(forbidden)) {
      throw new Error(`Forbidden operator/raw copy rendered in web: ${forbidden}`);
    }
  }
  await page.screenshot({ path: outPath("wave1-pulse-toast.png"), fullPage: true });

  await page.getByLabel("Dismiss").click();
  await page.waitForTimeout(500);
  const renderedAck = ackBodies.find((b) => b.event_type === "rendered");
  const lostAck = ackBodies.find((b) => b.event_type === "lost_unrendered");
  const dismissedAck = ackBodies.find((b) => b.event_type === "dismissed");
  if (!renderedAck?.notification_ids?.includes("wave1-timer")) {
    throw new Error(`Rendered ack missing timer id: ${JSON.stringify(ackBodies)}`);
  }
  if (renderedAck?.notification_ids?.includes("wave1-operator")) {
    throw new Error(`Rendered ack included unrendered operator id: ${JSON.stringify(ackBodies)}`);
  }
  if (!lostAck?.notification_ids?.includes("wave1-operator")) {
    throw new Error(`Lost-unrendered ack missing operator id: ${JSON.stringify(ackBodies)}`);
  }
  if (!dismissedAck?.notification_ids?.includes("wave1-timer")) {
    throw new Error(`Dismissed ack missing timer id: ${JSON.stringify(ackBodies)}`);
  }

  operatorMode = true;
  await page.goto(`${origin}/operator`, { waitUntil: "domcontentloaded" });
  await page.getByText("Cohort readiness").first().waitFor({ timeout: 15_000 });
  await page.getByText("Notification Lifecycle", { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: outPath("wave1-operator-lifecycle.png"), fullPage: true });
  const operatorText = await page.locator("body").innerText();
  for (const required of ["Notification Lifecycle", "web rendered", "1", "web lost unrendered", "operator pending"]) {
    if (!operatorText.toLowerCase().includes(required.toLowerCase())) {
      throw new Error(`Operator dashboard missing lifecycle text: ${required}`);
    }
  }

  await browser.close();
  await fs.writeFile(
    new URL("wave1-browser-verify-result.json", outDir),
    JSON.stringify({ ok: true, ackBodies }, null, 2)
  );
}

main().catch(async (error) => {
  await fs.writeFile(
    new URL("wave1-browser-verify-result.json", outDir),
    JSON.stringify({ ok: false, error: String(error?.stack || error) }, null, 2)
  ).catch(() => {});
  console.error(error);
  process.exit(1);
});
