"use client";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";

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
  onDismiss: (id: string) => void;
}

const AUTO_DISMISS_MS = 8000;

export function Toast({
  id,
  message,
  viewId,
  lifespan = "auto",
  onDismiss,
}: ToastProps) {
  // One-shot guard — stamp viewed_at exactly once per mount (Strict
  // Mode double-mounts in dev would otherwise send two POSTs; the
  // server is idempotent but the extra call is wasted).
  const viewed = useRef(false);

  // Keep a ref to the freshest dismiss handler so the auto-dismiss
  // setTimeout doesn't capture a stale closure if parent re-renders
  // with a new onDismiss reference.
  const latestDismiss = useRef<() => void>(() => {});
  latestDismiss.current = () => {
    if (viewId) {
      markDismissed(viewId).catch(() => {
        /* fire-and-forget: dwell tracking degrades gracefully on
           network failure; the toast UX still works. */
      });
    }
    onDismiss(id);
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
    const t = setTimeout(() => latestDismiss.current(), AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [lifespan]);

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-auto flex w-80 items-start gap-2 rounded-sm border border-hairline-signal/40 bg-void p-3 text-sm text-parchment shadow-lg"
    >
      <div className="flex-1 leading-relaxed">{message}</div>
      <button
        type="button"
        onClick={() => latestDismiss.current()}
        aria-label="Dismiss"
        className="-mt-0.5 shrink-0 text-dust-deep transition-colors hover:text-parchment"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
