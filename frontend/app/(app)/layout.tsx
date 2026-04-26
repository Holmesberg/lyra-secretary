"use client";
import { signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { ArchetypeSurvey } from "@/components/archetype-survey";
import { ConsentModal } from "@/components/consent-modal";
import { TutorialOverlay } from "@/components/tutorial-overlay";
// Temporarily disabled 2026-04-21 — the full-screen onboarding surface
// was replaced by a backend-seeded starter task (see
// backend/app/core/security.py `_seed_starter_task`). Import left in
// place and commented so we can re-enable post-Spring-School when the
// onboarding + first-time-user battery + import ingestion flows are
// ready to ship together. See docs/strategic_decisions_april_21.md §5.
// import { OnboardingFlow } from "@/components/onboarding-flow";

type Me = {
  user_id: number;
  email: string;
  terms_accepted_at: string | null;
  // Kept on the Me type — still returned by /v1/users/me, still stamped
  // atomically on first task create (including the starter seed in
  // security.py). Drives the 2026-05-21 kill-criterion query regardless
  // of whether the onboarding surface is live.
  onboarding_completed_at: string | null;
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
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status, data: session } = useSession();
  const router = useRouter();
  const qc = useQueryClient();
  // True while we're auto-triggering next-auth signOut after a 401.
  // Distinguishes the "your session expired, redirecting" banner from
  // the "backend is actually down" banner — different recovery paths.
  const [autoSigningOut, setAutoSigningOut] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/");
  }, [status, router]);

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
    queryKey: ["me"],
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
    if (meQ.error instanceof ApiError && meQ.error.status === 401) {
      setAutoSigningOut(true);
      signOut({ callbackUrl: "/" });
    }
  }, [meQ.error, meError]);

  // Used by gating modals (consent, archetype, tutorial) to refresh
  // /me after the user submits. Invalidate-and-refetch — same key, so
  // every consumer updates simultaneously.
  const refetchMe = () => qc.invalidateQueries({ queryKey: ["me"] });

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
              Check that the backend is running at{" "}
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"} and
              reload.
            </div>
          )}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => signOut({ callbackUrl: "/" })}
              className="rounded-sm border border-hairline-signal/40 bg-void-2/60 px-3 py-1.5 text-xs text-parchment transition-colors hover:bg-signal/10 hover:text-signal"
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
  // Tour gate: onboarding done AND neither tutorial stamp set AND
  // archetype-survey gate has passed (so we don't stack three modals
  // on first-run).
  const needsTutorial =
    !needsConsent &&
    !needsArchetypeSurvey &&
    !!me.onboarding_completed_at &&
    !me.tutorial_completed_at &&
    !me.tutorial_skipped_at;

  // Temporarily disabled 2026-04-21 — full-screen onboarding surface
  // replaced by a backend-seeded starter task on first sign-in.
  // Re-enable post-Spring-School when the richer onboarding flow
  // (archetype instrument battery + import ingestion) is ready to ship.
  // const needsOnboarding = !needsConsent && !me.onboarding_completed_at;
  // if (needsOnboarding) {
  //   return (
  //     <OnboardingFlow
  //       userEmail={me.email}
  //       onCompleted={() => api<Me>("/v1/users/me").then(setMe)}
  //     />
  //   );
  // }

  return (
    <AppShell>
      {needsConsent && <ConsentModal onAccepted={refetchMe} />}
      {!needsConsent && children}
      {needsArchetypeSurvey && <ArchetypeSurvey onFinished={refetchMe} />}
      {needsTutorial && <TutorialOverlay onFinished={refetchMe} />}
    </AppShell>
  );
}
