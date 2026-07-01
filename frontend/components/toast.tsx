"use client";
import { useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowUpRight, X } from "lucide-react";

import { markDismissed, markViewed } from "@/lib/reflection-view";

export interface ToastProps {
  id: string;
  message: string;
  viewId?: string | null;
  /**
   * "auto" — dismiss after 8s (default, for micro_mirror).
   * "pin"  — never auto-dismiss (for calibration_nudge reference-class
   *          summaries that need dwell time to read — per
   *          notification_patterns.md §Toast Lifespan exception).
   */
  lifespan?: "auto" | "pin";
  /**
   * Optional destination for a "View details →" affordance. When
   * present, renders a tiny link button alongside the X so the toast
   * has a deeper-engagement escape hatch instead of only click-to-
   * dismiss. Route target typically /insights. Clicking marks the
   * toast dismissed (reflection_view_log) AND navigates.
   *
   * Motivated by Day-18 finding: micro_mirror had 95% dismissal at
   * ~6s dwell across all users who viewed one. Hypothesis: no deeper-
   * engagement affordance = glance-and-dismiss is the only option.
   */
  detailHref?: string;
  onDismiss: (id: string, reason?: "acted" | "dismissed" | "expired") => void;
}

const AUTO_DISMISS_MS = 8000;

export function Toast({
  id,
  message,
  viewId,
  lifespan = "auto",
  detailHref,
  onDismiss,
}: ToastProps) {
  // One-shot guard — stamp viewed_at exactly once per mount (Strict
  // Mode double-mounts in dev would otherwise send two POSTs; the
  // server is idempotent but the extra call is wasted).
  const viewed = useRef(false);

  // Keep a ref to the freshest dismiss handler so the auto-dismiss
  // setTimeout doesn't capture a stale closure if parent re-renders
  // with a new onDismiss reference.
  const latestDismiss = useRef<(reason?: "acted" | "dismissed" | "expired") => void>(() => {});
  latestDismiss.current = (reason = "dismissed") => {
    if (viewId) {
      markDismissed(viewId).catch(() => {
        /* fire-and-forget: dwell tracking degrades gracefully on
           network failure; the toast UX still works. */
      });
    }
    onDismiss(id, reason);
  };

  useEffect(() => {
    if (viewed.current || !viewId) return;
    viewed.current = true;
    markViewed(viewId).catch(() => {
      /* fire-and-forget — dwell tracking degrades gracefully */
    });
  }, [viewId]);

  useEffect(() => {
    if (lifespan !== "auto") return;
    const t = setTimeout(() => latestDismiss.current("expired"), AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [lifespan]);

  return (
    <div
      data-testid="notification-toast"
      data-toast-id={id}
      role="status"
      aria-live="polite"
      className="pointer-events-auto flex w-80 flex-col gap-2 rounded-sm border border-hairline-signal/40 bg-void p-3 text-sm text-parchment shadow-lg"
    >
      <div className="flex items-start gap-2">
        <div className="flex-1 leading-relaxed">{message}</div>
        <button
          data-testid="notification-toast-dismiss"
          type="button"
          onClick={() => latestDismiss.current("dismissed")}
          aria-label="Dismiss"
          className="-mt-0.5 shrink-0 text-dust-deep transition-colors hover:text-parchment"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {detailHref && (
        <Link
          data-testid="notification-toast-details"
          href={detailHref}
          onClick={() => latestDismiss.current("acted")}
          className="inline-flex items-center gap-1 self-start font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
        >
          View details
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      )}
    </div>
  );
}
