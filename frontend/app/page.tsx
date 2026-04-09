"use client";
import { signIn, signOut, useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ConsentModal } from "@/components/consent-modal";

type Me = {
  user_id: number;
  email: string;
  terms_accepted_at: string | null;
};

export default function HomePage() {
  const { data: session, status } = useSession();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (status !== "authenticated") return;
    setLoading(true);
    api<Me>("/v1/users/me")
      .then(setMe)
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [status]);

  if (status === "loading") return <Center>Loading…</Center>;

  if (status === "unauthenticated") {
    return (
      <Center>
        <h1 className="text-3xl font-semibold mb-2">Lyra Secretary</h1>
        <p className="text-muted-foreground mb-8 max-w-md text-center">
          An adaptive scheduler that learns the gap between what you plan and what you execute.
        </p>
        <button
          onClick={() => signIn("google")}
          className="px-4 py-2 rounded-md bg-white text-black font-medium hover:bg-white/90"
        >
          Sign in with Google
        </button>
      </Center>
    );
  }

  const needsConsent = me && !me.terms_accepted_at;

  return (
    <div className="min-h-screen p-8">
      <header className="flex items-center justify-between mb-12">
        <h1 className="text-2xl font-semibold">Lyra Secretary</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">{session?.user?.email}</span>
          <button onClick={() => signOut()} className="text-sm text-muted-foreground hover:text-foreground">
            Sign out
          </button>
        </div>
      </header>

      {loading && <p className="text-muted-foreground">Loading account…</p>}
      {needsConsent && <ConsentModal onAccepted={() => api<Me>("/v1/users/me").then(setMe)} />}
      {me && me.terms_accepted_at && (
        <main>
          <p className="text-muted-foreground">
            Welcome, user #{me.user_id}. The Today view, calendar, and table arrive in Phase 3.
          </p>
        </main>
      )}
    </div>
  );
}

function Center({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen flex flex-col items-center justify-center p-8">{children}</div>;
}
