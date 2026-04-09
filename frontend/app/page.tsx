"use client";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LandingPage() {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/today");
  }, [status, router]);

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center text-white/50">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0a0a0a] p-8 text-white">
      <h1 className="mb-2 text-3xl font-semibold">Lyra Secretary</h1>
      <p className="mb-8 max-w-md text-center text-white/60">
        An adaptive scheduler that learns the gap between what you plan and what
        you execute.
      </p>
      <button
        onClick={() => signIn("google", { callbackUrl: "/today" })}
        className="rounded-md bg-white px-4 py-2 font-medium text-black hover:bg-white/90"
      >
        Sign in with Google
      </button>
    </div>
  );
}
