"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * Zero-UI client effects for the landing page:
 *  (1) if the visitor has an authenticated session, bounce them to /today
 *  (2) set `data-surface="landing"` on <body> so globals.css can switch the
 *      landing-only dark background on.
 *
 * Both are client-only by necessity — useSession needs the session cookie
 * and setAttribute runs against the DOM. Isolating them here means the
 * rest of the landing can SSR for crawlers.
 */
export function AuthRedirectGate() {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/today");
  }, [status, router]);

  useEffect(() => {
    document.body.setAttribute("data-surface", "landing");
    return () => document.body.removeAttribute("data-surface");
  }, []);

  return null;
}
