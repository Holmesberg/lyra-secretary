"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const APP_ROUTES_TO_WARM = [
  "/today",
  "/pulse",
  "/calendar",
  "/deadlines",
  "/table",
  "/insights",
  "/settings",
];

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
    if (status === "authenticated") return;
    let devWarmTimer: number | undefined;

    const warm = () => {
      for (const route of APP_ROUTES_TO_WARM) {
        router.prefetch(route);
      }
      void fetch("/api/auth/providers").catch(() => {});
      void fetch("/api/auth/csrf").catch(() => {});

      if (process.env.NODE_ENV === "development") {
        devWarmTimer = window.setTimeout(() => {
          void Promise.allSettled(
            APP_ROUTES_TO_WARM.map((route) =>
              fetch(route, {
                cache: "no-store",
                credentials: "same-origin",
              })
            )
          );
        }, 750);
      }
    };

    const idle =
      "requestIdleCallback" in window
        ? window.requestIdleCallback
        : (cb: IdleRequestCallback) => window.setTimeout(cb, 1);
    const cancelIdle =
      "cancelIdleCallback" in window
        ? window.cancelIdleCallback
        : (id: number) => window.clearTimeout(id);
    const id = idle(warm);
    return () => {
      cancelIdle(id as number);
      if (devWarmTimer !== undefined) window.clearTimeout(devWarmTimer);
    };
  }, [router, status]);

  useEffect(() => {
    document.body.setAttribute("data-surface", "landing");
    return () => document.body.removeAttribute("data-surface");
  }, []);

  return null;
}
