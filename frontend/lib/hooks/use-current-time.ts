"use client";
import { useEffect, useState } from "react";

/**
 * Returns the current Date, refreshing on a fixed interval so components
 * that depend on "now" (new-task-modal defaults, today/page date key for
 * cross-midnight rollover) re-render without a manual refresh.
 *
 * Default tick is 60 seconds — fine-grained enough for minute-level UX
 * (cross-day date rollover, 5-min rounded defaults) without churning the
 * render tree. Pass a different interval if a caller needs it.
 *
 * The interval is cleaned up on unmount. A single interval per mounted
 * hook instance; callers that share a tick should colocate (we don't
 * have a shared broadcast yet and haven't needed one).
 */
export function useCurrentTime(intervalMs: number = 60_000): Date {
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return now;
}
