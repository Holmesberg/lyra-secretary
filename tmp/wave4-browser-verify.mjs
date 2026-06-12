import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const { chromium } = playwright;
const require = createRequire(import.meta.url);
const { encode } = require("../frontend/node_modules/next-auth/jwt");

const origin = process.env.WAVE4_FRONTEND_ORIGIN || "http://localhost:3000";
const outDir = new URL("./", import.meta.url);
const outPath = (name) => fileURLToPath(new URL(name, outDir));
const nextAuthSecret =
  process.env.NEXTAUTH_SECRET || "wave4-local-secret-value-at-least-32-chars";

const nowIso = new Date().toISOString();

function corsHeaders() {
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-headers": "authorization, content-type",
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

function sectionMeta(basis = "derived", confidence = "high", impact = "warning") {
  return { basis, confidence, readiness_impact: impact };
}

function dashboardPayload() {
  const dynamicIssues = [
    {
      id: "duplicate_open_sessions",
      severity: "critical",
      message: "A task has more than one open stopwatch session.",
      suggested_action: "Repair the state transition path that created duplicate sessions.",
      related_section: "state_invariants",
      readiness_impact: "blocker",
      blocks_cohort_expansion: true,
      tags: [],
    },
    {
      id: "invalid_recovery_actions_not_instrumented",
      severity: "warning",
      message: "Invalid recovery actions are not instrumented.",
      suggested_action: "Keep K03 as unknown until invalid recovery attempts are counted.",
      related_section: "state_invariants",
      readiness_impact: "warning",
      blocks_cohort_expansion: false,
      tags: ["K03"],
    },
    {
      id: "exposure_records_without_render_evidence",
      severity: "critical",
      message: "Exposure ledger contains 17 exposure records without render evidence.",
      suggested_action:
        "Do not treat exposure-influenced metrics as valid until render linkage is reconciled.",
      related_section: "notification_lifecycle",
      readiness_impact: "blocker",
      blocks_cohort_expansion: true,
      tags: [],
    },
    {
      id: "notification_source_freshness_not_instrumented",
      severity: "warning",
      message: "Notification lifecycle freshness is not instrumented.",
      suggested_action:
        "Treat notification lifecycle counts as incomplete until notification source freshness is recorded.",
      related_section: "data_freshness",
      readiness_impact: "warning",
      blocks_cohort_expansion: false,
      tags: [],
    },
  ];
  return {
    generated_at: nowIso,
    data_freshness: {
      ...sectionMeta("direct", "high", "informational"),
      generated_at: nowIso,
      source_windows: {
        tasks_last_seen_at: nowIso,
        sessions_last_seen_at: nowIso,
        notifications_last_seen_at: null,
        exposures_last_seen_at: nowIso,
        providers_last_seen_at: nowIso,
      },
      stale_sources: ["notifications_last_seen_at"],
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
      ...sectionMeta("contract", "high", "informational"),
      included_events: ["task_created", "timer_started", "timer_stopped"],
      excluded_events: ["login_only", "page_refresh", "background_sync"],
    },
    cohort_readiness: {
      ...sectionMeta("derived", "medium", "blocker"),
      status: "red",
      blockers: ["duplicate_open_sessions", "exposure_records_without_render_evidence"],
      warnings: [
        "invalid_recovery_actions_not_instrumented",
        "notification_source_freshness_not_instrumented",
      ],
      minimum_fix_set: ["duplicate_open_sessions", "exposure_records_without_render_evidence"],
      safe_to_invite_more_users: false,
      rationale: "Fix blocker set before inviting more users.",
    },
    cohort_segments: {
      ...sectionMeta("derived", "high", "informational"),
      operator_users_excluded: 1,
      test_or_synthetic_users_excluded: 2,
      trusted_users: 4,
      new_users_7d: 1,
      activated_users: 3,
      dormant_users: 1,
      users_with_dirty_data_only: 1,
      users_with_clean_sessions: 2,
      users_with_open_stale_sessions: 0,
    },
    cohort: {
      ...sectionMeta("derived", "medium", "informational"),
      non_operator_users: 4,
      trusted_users_total: 4,
      activated_users: 3,
      meaningful_active_users_7d: 2,
      weekly_active_users: 2,
      dormant_users_7d: 1,
      dormant_users_14d: 1,
    },
    retention: {
      ...sectionMeta("proxy", "medium", "informational"),
      d1_return_rate: 0.5,
      d7_return_rate: null,
      d14_return_rate: null,
      returning_today: 1,
      returning_7d: 2,
      returning_14d: 2,
      basis_note: "meaningful_activity_proxy",
    },
    activity_frequency: {
      ...sectionMeta("proxy", "medium", "informational"),
      active_days_last_7d: 4,
      active_days_last_14d: 6,
      median_days_between_activity: null,
      login_frequency_status: "not_instrumented",
      proxy: "active_days_from_explicit_lyra_events",
    },
    activation_quality: {
      ...sectionMeta("derived", "medium", "warning"),
      first_task_created_count: 3,
      first_timer_started_count: 3,
      first_clean_stop_count: 2,
      first_pressure_map_action_count: 1,
      first_recovery_action_count: 0,
      median_time_to_first_clean_loop: null,
      not_instrumented_fields: ["median_time_to_first_clean_loop"],
    },
    product_loop_funnel: {
      ...sectionMeta("mixed", "medium", "warning"),
      pulse_opened: null,
      quick_capture_used: null,
      brain_dump_submitted: null,
      preview_confirmed: null,
      task_created: 8,
      obligation_bound: 2,
      pressure_map_opened: 1,
      recovery_plan_previewed: null,
      recovery_plan_confirmed: 0,
      timer_started: 5,
      timer_stopped_cleanly: 4,
      recovery_surface_seen: 1,
      insight_seen: 1,
      returned_after_24h: 2,
      dropoff_points: ["task_created->obligation_bound"],
      not_instrumented_fields: ["pulse_opened", "quick_capture_used"],
    },
    measurement_integrity: {
      ...sectionMeta("derived", "high", "blocker"),
      clean_trace_ratio: 0.5,
      dirty_trace_count: 2,
      dirty_reasons: {
        auto_closed: 0,
        stale_recovered: 1,
        retroactive: 0,
        corrected: 0,
        voided: 0,
        missing_timestamps: 0,
        impossible_duration: 0,
        unknown_exposure: 0,
        provider_only: 3,
        exposure_contaminated: 1,
      },
      dirty_reason_distribution: {
        stale_recovered: 1,
        provider_only: 3,
        exposure_contaminated: 1,
      },
      clean_trace_ratio_basis: {
        definition:
          "clean eligible explicit stopwatch sessions / all eligible explicit stopwatch sessions",
        window_days: 14,
        numerator: 2,
        denominator: 4,
        excluded_from_denominator: {
          operator_user_sessions: 1,
          test_or_synthetic_user_sessions: 2,
          voided_or_deleted_task_sessions: 1,
          deleted_retained_sessions: 0,
          provider_only_rows: 3,
          non_session_tasks: 6,
        },
      },
      dirty_session_reason_sample: {
        sample_session_hash: ["exposure_contaminated"],
      },
      analytic_blockers: [],
      calibration_safe: false,
      insights_safe: false,
    },
    state_invariants: {
      ...sectionMeta("derived", "high", "blocker"),
      duplicate_open_sessions: 1,
      executing_tasks_without_open_session: 0,
      paused_tasks_without_open_session: 0,
      executed_tasks_missing_start_or_end: 0,
      open_sessions_for_executed_tasks: 0,
      stale_reentry_candidates: 0,
      invalid_recovery_actions_seen: null,
      not_instrumented_fields: ["invalid_recovery_actions_seen"],
    },
    notification_lifecycle: {
      ...sectionMeta("mixed", "medium", "warning"),
      web_created: 2,
      web_queued: 1,
      web_reserved: 0,
      web_rendered: 1,
      web_acted: 0,
      web_dismissed: 1,
      web_expired: 0,
      web_lost_unrendered: 0,
      duplicate_prompt_count: 0,
      render_without_exposure_count: 0,
      exposure_without_render_count: 17,
      operator_created: 0,
      operator_pending: 0,
      not_instrumented_fields: [],
      redis_errors: [],
    },
    provider_integrity: {
      ...sectionMeta("derived", "medium", "warning"),
      provider_rows_total: 3,
      provider_rows_missing_provenance: 0,
      provider_completion_candidates: 0,
      provider_truth_violations: 0,
      duplicate_import_candidates: 0,
      sync_failures_24h: 0,
      user_visible_provider_errors_24h: 0,
    },
    reliability: {
      ...sectionMeta("derived", "medium", "warning"),
      user_visible_error_count_24h: 0,
      failed_api_count_24h: null,
      calendar_token_warning_user_visible_count: 0,
      task_state_rejection_count: null,
      export_success_count: null,
      delete_success_count: null,
      not_instrumented_fields: [
        "failed_api_count_24h",
        "task_state_rejection_count",
        "export_success_count",
        "delete_success_count",
      ],
    },
    privacy_boundary: {
      ...sectionMeta("direct", "high", "blocker"),
      raw_task_titles_exposed: false,
      raw_emails_exposed: false,
      provider_tokens_exposed: false,
      raw_provider_urls_exposed: false,
      user_debug_mode_enabled: false,
    },
    bug_watchlist: {
      ...sectionMeta("derived", "medium", "blocker"),
      k01_calendar_warning_leak: "pass",
      k02_timer_overflow_duplicate: "pass",
      k03_invalid_mark_done_executed: "unknown",
      k04_parked_25h_stale: "pass",
      k05_pulse_quick_capture_anchor: "unknown",
    },
    dynamic_issues: dynamicIssues,
    users: [
      {
        user_id: 44,
        first_name: "Aly",
        name_source: "google_profile",
        email_hash: "abc123abc123",
        created_at: nowIso,
        last_meaningful_activity_at: nowIso,
        active_days_7d: 2,
        active_days_14d: 3,
        task_count: 4,
        executed_task_count: 2,
        stopwatch_session_count: 3,
        clean_trace_ratio: 0.67,
        open_timer_count: 0,
        paused_over_72h_count: 0,
        last_loop_stage: "clean_loop",
      },
    ],
    operator_recommendations: dynamicIssues.map((issue) => ({
      severity: issue.severity,
      message: issue.message,
      suggested_action: issue.suggested_action,
      related_section: issue.related_section,
      blocks_cohort_expansion: issue.blocks_cohort_expansion,
    })),
    derived_metrics: {
      full_loop_users: 2,
      full_loop_completion_rate: 0.67,
      timer_start_to_clean_stop_rate: 0.8,
      safe_to_invite_more_users: false,
    },
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
    await route.fulfill(
      json({
        user: {
          name: "Wave Four",
          email: "wave4-browser@example.test",
          image: null,
        },
        expires: "2099-01-01T00:00:00.000Z",
        backendToken: "wave4-local-token",
      }),
    );
  });

  const sessionCookie = await encode({
    secret: nextAuthSecret,
    token: {
      sub: "wave4-google-sub",
      email: "wave4-browser@example.test",
      name: "Wave Four",
      given_name: "Wave",
      backendToken: "wave4-local-token",
    },
  });
  const sessionCookies = [
    {
      name: "next-auth.session-token",
      value: sessionCookie,
      url: origin,
      httpOnly: true,
      sameSite: "Lax",
    },
  ];
  if (origin.startsWith("https://")) {
    sessionCookies.push({
      name: "__Secure-next-auth.session-token",
      value: sessionCookie,
      url: origin,
      httpOnly: true,
      sameSite: "Lax",
      secure: true,
    });
  }
  await page.context().addCookies(sessionCookies);

  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders(), body: "" });
      return;
    }
    if (url.pathname === "/v1/users/me") {
      await route.fulfill(
        json({
          user_id: 9404,
          email: "wave4-browser@example.test",
          terms_accepted_at: nowIso,
          onboarding_completed_at: nowIso,
          has_active_task_history: true,
          tutorial_completed_at: nowIso,
          tutorial_skipped_at: null,
          archetype_survey_eligible: false,
          archetype_assignment_completed: true,
          archetype_retrofit_dismissed_at: nowIso,
          archetype_id: null,
          executed_session_count: 3,
          google_calendar_connected: false,
          is_operator: true,
        }),
      );
      return;
    }
    if (url.pathname === "/v1/operator/dashboard") {
      await route.fulfill(json(dashboardPayload()));
      return;
    }
    await route.fulfill(json({ ok: true }));
  });

  await page.goto(`${origin}/operator`, { waitUntil: "domcontentloaded" });
  await page.getByText("Dynamic Issues").waitFor({ timeout: 15_000 });
  await page
    .getByText("A task has more than one open stopwatch session.")
    .first()
    .waitFor({ timeout: 15_000 });
  const bodyText = await page.locator("body").innerText();
  for (const expected of [
    "clean eligible explicit stopwatch sessions",
    "operator user sessions",
    "test or synthetic user sessions",
    "K03",
    "Exposure ledger contains 17 exposure records without render evidence",
    "Notification lifecycle freshness is not instrumented",
    "source windows",
  ]) {
    if (!bodyText.toLowerCase().includes(expected.toLowerCase())) {
      throw new Error(`Expected operator dashboard text missing: ${expected}`);
    }
  }
  if (bodyText.includes("[object Object]")) {
    throw new Error("Operator dashboard rendered raw object text.");
  }
  for (const forbidden of [
    "avoidance",
    "motivation",
    "discipline",
    "fragmentation score",
    "focus score",
  ]) {
    if (bodyText.toLowerCase().includes(forbidden)) {
      throw new Error(`Forbidden operator copy appeared: ${forbidden}`);
    }
  }

  await page.screenshot({ path: outPath("wave4-operator-dashboard.png"), fullPage: true });
  await browser.close();
  await fs.writeFile(
    new URL("wave4-browser-verify-result.json", outDir),
    JSON.stringify({ ok: true, origin }, null, 2),
  );
}

main().catch(async (error) => {
  await fs
    .writeFile(
      new URL("wave4-browser-verify-result.json", outDir),
      JSON.stringify({ ok: false, error: String(error?.stack || error) }, null, 2),
    )
    .catch(() => {});
  console.error(error);
  process.exit(1);
});
