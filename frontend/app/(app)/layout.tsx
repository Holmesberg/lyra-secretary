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

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/");
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated") return;
    api<Me>("/v1/users/me").then(setMe).catch(console.error);
  }, [status]);

  if (status !== "authenticated") return null;
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
