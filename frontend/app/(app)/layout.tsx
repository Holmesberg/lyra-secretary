"use client";
import { signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { ConsentModal } from "@/components/consent-modal";
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
  const [me, setMe] = useState<Me | null>(null);
  const [meError, setMeError] = useState<string | null>(null);
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

  useEffect(() => {
    if (status !== "authenticated") return;
    setMeError(null);
    api<Me>("/v1/users/me")
      .then(setMe)
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e);
        setMeError(msg);
        // Log with a real label so WSL/dev tab shows the actual reason.
        console.error("users/me fetch failed:", msg);

        // 401 = expired/invalid JWT in the next-auth session. Reloading
        // won't help — the stored token is dead. Auto-trigger signOut
        // and bounce to the landing page for a fresh login.
        if (e instanceof ApiError && e.status === 401) {
          setAutoSigningOut(true);
          signOut({ callbackUrl: "/" });
        }
      });
  }, [status]);

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
      {needsConsent && (
        <ConsentModal
          onAccepted={() => api<Me>("/v1/users/me").then(setMe)}
        />
      )}
      {!needsConsent && children}
    </AppShell>
  );
}
