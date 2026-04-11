"use client";
import { signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { ConsentModal } from "@/components/consent-modal";

type Me = {
  user_id: number;
  email: string;
  terms_accepted_at: string | null;
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
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
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a] text-sm text-white/50">
        Loading session…
      </div>
    );
  }
  if (status !== "authenticated") return null;
  if (meError) {
    const isExpiredSession = autoSigningOut;
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a] p-8 text-center text-sm text-red-300">
        <div>
          <div className="mb-2 font-semibold">
            {isExpiredSession
              ? "Session expired"
              : "Backend unreachable"}
          </div>
          <div className="text-xs text-white/60">
            {isExpiredSession
              ? "Your sign-in expired. Redirecting to the sign-in page…"
              : meError}
          </div>
          {!isExpiredSession && (
            <div className="mt-4 text-[11px] text-white/40">
              Check that the backend is running at{" "}
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"} and
              reload.
            </div>
          )}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => signOut({ callbackUrl: "/" })}
              className="rounded border border-white/20 bg-white/5 px-3 py-1.5 text-xs text-white/80 hover:bg-white/10"
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
