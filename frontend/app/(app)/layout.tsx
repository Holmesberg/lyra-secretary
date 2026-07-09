"use client";
import { useSession } from "next-auth/react";
import { clearClientAuthState, signOutAndClear } from "@/lib/sign-out-and-clear";
import { notifyOperator } from "@/lib/operator-notify";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { AppShell } from "@/components/app-shell";
import { ArchetypeSurvey } from "@/components/archetype-survey";
import { ConsentModal } from "@/components/consent-modal";
import { TutorialOverlay } from "@/components/tutorial-overlay";
import { AppNotificationHost } from "@/components/app-notification-host";
import { UndoToastHost } from "@/components/undo-toast-host";
// Brain-dump onboarding kept — operator: "catches the user from the get
// go." Implementation pivoted 2026-04-28 evening to multi-parse + auto-
// bind + one-tap confirmation block: user types free text, LLM splits
// into real tasks + deadlines, heuristic suggests bindings, user
// confirms via one-tap questions, all rows commit in a single
// transaction. No more meta "Plan your week" task at the end.
import { OnboardingFlow } from "@/components/onboarding-flow";

const ONBOARDING_SKIP_SESSION_KEY = "lyra:onboarding-skip-this-session";

type Me = {
  user_id: number;
  email: string;
  terms_accepted_at: string | null;
  // Kept on the Me type — still returned by /v1/users/me, still stamped
  // atomically on first task create (including the starter seed in
  // security.py). Drives the 2026-05-21 kill-criterion query regardless
  // of whether the onboarding surface is live.
  onboarding_completed_at: string | null;
  // True if the user has any non-voided, non-SKIPPED task. False keeps
  // the brain-dump gate visible even after onboarding_completed_at is
  // stamped — re-engagement check (operator-locked 2026-04-29).
  has_active_task_history: boolean;
  // Guided tour stamps (alembic 029, 2026-04-22). Both null AND
  // onboarding_completed_at NOT NULL triggers the TutorialOverlay
  // render below. Either stamp set prevents re-fire.
  tutorial_completed_at: string | null;
  tutorial_skipped_at: string | null;
  // Archetype survey gate (2026-04-22 clustering ship). True when
  // user is post-launch AND has no ArchetypeAssignment yet. Drives
  // the ArchetypeSurvey gate below (fires between consent + tutorial).
  archetype_survey_eligible: boolean;
  // True when the user has a completed=True ArchetypeAssignment. Used
  // by the Settings retrofit banner (show iff no completed assignment
  // AND retrofit_dismissed_at is null). Distinguishes real archetypes
  // from skip-defaulted Diffuse Average rows.
  archetype_assignment_completed: boolean;
  archetype_retrofit_dismissed_at: string | null;
  archetype_id: string | null;
  // MANIFESTO §VT-25 / building_phases.md:167 — archetype label is
  // surfaced only after ~5 EXECUTED sessions (gate in
  // ArchetypeProfileSection). Total EXECUTED, non-voided across all time.
  executed_session_count: number;
  // Google Calendar read-only integration (2026-04-21). Boolean
  // surface only — the actual refresh_token lives in the backend
  // `user.google_refresh_token` column. Null/false means no calendar
  // data on /calendar. The /api/calendar/setup handshake below flips
  // this from false to true once the refresh_token reaches the backend.
  google_calendar_connected: boolean;
  is_operator: boolean;
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status, data: session } = useSession();
  const router = useRouter();
  const qc = useQueryClient();
  // True while we're auto-triggering next-auth signOut after a 401.
  // Distinguishes the "your session expired, redirecting" banner from
  // the "backend is actually down" banner — different recovery paths.
  const [autoSigningOut, setAutoSigningOut] = useState(false);
  const [onboardingSkippedThisSession, setOnboardingSkippedThisSession] =
    useState(() => {
      if (typeof window === "undefined") return false;
      return window.sessionStorage.getItem(ONBOARDING_SKIP_SESSION_KEY) === "1";
    });

  useEffect(() => {
    if (status === "unauthenticated") {
      // Wipe React Query localStorage on session expiry / passive
      // logout BEFORE redirecting. Without this, next user on the
      // same browser sees prior user's persisted cache flash on first
      // paint (audit-flagged 2026-04-30, RISK-5: shared family device
      // = high probability mom forgets explicit logout).
      clearClientAuthState(qc);
      router.replace("/");
    }
  }, [status, router, qc]);

  // Calendar refresh-token handshake was here (2026-04-21 → 2026-04-22).
  // Removed when we split identity from authorization: sign-in no longer
  // requests calendar.readonly, so there's no refresh_token in the JWT
  // to forward. Users acquire calendar access from Settings →
  // Integrations via the incremental OAuth flow at
  // /api/integrations/google-calendar/connect. See
  // docs/integrations_architecture.md.

  // /v1/users/me via React Query, key ["me"] — shared cache with all
  // other components that fetch /me (archetype-insights-card, settings/
  // page, archetype-survey-invalidation, etc.). Apr 25 perf fix:
  // settings page archetype section was paying a fresh ~1s /me round-
  // trip on every visit because it used a plain useEffect+useState
  // instead of the shared cache key. Now layout's first fetch warms
  // the cache; settings reads it instantly.
  const meQ = useQuery<Me>({
    queryKey: queryKeys.me,
    queryFn: () => api<Me>("/v1/users/me"),
    enabled: status === "authenticated",
    retry: false, // 401 must not retry — it'll loop signOut otherwise
    refetchOnWindowFocus: false,
    refetchInterval: false, // /me is stable across the session
    staleTime: 5 * 60_000, // treat as fresh for 5 min
  });
  const me = meQ.data;
  const meError =
    meQ.error instanceof Error
      ? meQ.error.message
      : meQ.error
        ? String(meQ.error)
        : null;

  useEffect(() => {
    if (!meQ.error) return;
    console.error("users/me fetch failed:", meError);
    // Mirror to operator Telegram per 2026-04-30 ALL-routes ask.
    // Severity is "error" for backend-unreachable, "warn" for
    // session-expired (recoverable by re-signing in).
    if (meQ.error instanceof ApiError && meQ.error.status === 401) {
      notifyOperator({
        message: `Session expired — auto-signing out. (${meError ?? "401 from /v1/users/me"})`,
        severity: "warn",
        source: "frontend.session-expired",
      });
      setAutoSigningOut(true);
      signOutAndClear(qc, { callbackUrl: "/" });
    } else {
      notifyOperator({
        message: `Backend unreachable from /v1/users/me: \`${meError ?? "unknown"}\`. Check tunnel + backend container.`,
        severity: "error",
        source: "frontend.backend-down",
      });
    }
  }, [meQ.error, meError, qc]);

  // Used by gating modals (consent, archetype, tutorial) to refresh
  // /me after the user submits. Invalidate-and-refetch — same key, so
  // every consumer updates simultaneously.
  const refetchMe = () => qc.invalidateQueries({ queryKey: queryKeys.me });
  const skipOnboardingForSession = () => {
    setOnboardingSkippedThisSession(true);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(ONBOARDING_SKIP_SESSION_KEY, "1");
    }
    void refetchMe();
  };

  useEffect(() => {
    if (!me?.has_active_task_history) return;
    setOnboardingSkippedThisSession(false);
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(ONBOARDING_SKIP_SESSION_KEY);
    }
  }, [me?.has_active_task_history]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void text-sm text-dust">
        Loading session…
      </div>
    );
  }
  if (status !== "authenticated") return null;
  if (meError) {
    const isExpiredSession = autoSigningOut;
    return (
      <div className="flex min-h-screen items-center justify-center bg-void p-8 text-center text-sm text-ember">
        <div>
          <div className="mb-2 font-semibold">
            {isExpiredSession
              ? "Session expired"
              : "Backend unreachable"}
          </div>
          <div className="text-xs text-dust">
            {isExpiredSession
              ? "Your sign-in expired. Redirecting to the sign-in page…"
              : meError}
          </div>
          {!isExpiredSession && (
            <div className="mt-4 text-[11px] text-dust-deep">
              Check that the backend is running{" "}
              {typeof window !== "undefined" && window.location.hostname.endsWith("lyraos.org")
                ? "for the public Barzakh API"
                : `at ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}`} and
              reload.
            </div>
          )}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => {
                signOutAndClear(qc, { callbackUrl: "/" });
              }}
              className="rounded-sm border border-hairline-signal/40 bg-void-2/60 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-signal/10 hover:text-signal focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/70"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    );
  }
  if (!me) return null;

  const needsConsent = !me.terms_accepted_at;
  // Archetype survey gate (2026-04-22 clustering ship). Fires for
  // post-launch users who haven't yet submitted OR skipped the survey.
  // Pre-launch users (archetype_survey_eligible=false) bypass this
  // gate and see the Settings retrofit banner instead. Skipped users
  // have an ArchetypeAssignment row → archetype_survey_eligible=false,
  // so they don't re-fire.
  const needsArchetypeSurvey = !needsConsent && me.archetype_survey_eligible;
  // Tutorial gate disabled 2026-04-28 evening per operator: "remove the
  // tutorial we'll make a better more advanced one." Component file
  // and stamp columns kept in tree for the future revival; gate logic
  // stays in this comment block as the canonical reference shape when
  // the new tutorial ships.
  //   const needsTutorial =
  //     !needsConsent &&
  //     !needsArchetypeSurvey &&
  //     !!me.onboarding_completed_at &&
  //     !me.tutorial_completed_at &&
  //     !me.tutorial_skipped_at;
  const needsTutorial = false;

  // Brain-dump onboarding gate — operator-locked 2026-04-28 evening:
  // "catches the user from the get go." Refactored implementation
  // (multi-parse + auto-bind + one-tap confirmation) replaces the
  // single-meta-task version.
  //
  // 2026-04-29 amendment (operator): a user who stamped
  // onboarding_completed_at but never created a real (non-skipped,
  // non-voided) task should re-see the brain-dump on next visit. Bug
  // case: empty-commit stamps onboarding, leaving the user inside the
  // app with nothing to do. The has_active_task_history flag from /me
  // catches this and resets the gate.
  const needsOnboarding =
    !needsConsent &&
    !onboardingSkippedThisSession &&
    (!me.onboarding_completed_at || !me.has_active_task_history);
  if (needsOnboarding) {
    return (
      <OnboardingFlow
        userEmail={me.email}
        onCompleted={refetchMe}
        onSkipped={skipOnboardingForSession}
      />
    );
  }

  return (
    <AppShell isOperator={!!me.is_operator}>
      {needsConsent && <ConsentModal onAccepted={refetchMe} />}
      {!needsConsent && children}
      {!needsConsent && <AppNotificationHost />}
      {!needsConsent && <UndoToastHost />}
      {needsArchetypeSurvey && <ArchetypeSurvey onFinished={refetchMe} />}
      {/* Tutorial overlay removed 2026-04-28 — operator: "we'll make a
          better more advanced one." Component file kept in tree for
          future revival. */}
      {needsTutorial && <TutorialOverlay onFinished={refetchMe} />}
    </AppShell>
  );
}
