"use client";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
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
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a] p-8 text-center text-sm text-red-300">
        <div>
          <div className="mb-2 font-semibold">Backend unreachable</div>
          <div className="text-xs text-white/60">{meError}</div>
          <div className="mt-4 text-[11px] text-white/40">
            Check that the backend is running at{" "}
            {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"} and
            reload.
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
