"use client";

import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Undo2, X } from "lucide-react";

import {
  UNDO_AVAILABLE_EVENT,
  undoLastAction,
  type UndoAvailableDetail,
} from "@/lib/undo";

const UNDO_WINDOW_MS = 30_000;

interface UndoToastState {
  id: number;
  message: string;
  expiresAt: number;
  status: "ready" | "working" | "done" | "error";
  detail?: string;
}

function invalidateAfterUndo(qc: ReturnType<typeof useQueryClient>) {
  const keys = [
    ["tasks"],
    ["tasks-range"],
    ["tasks-evidence"],
    ["stopwatch-status"],
    ["deadlines"],
    ["operator-dashboard"],
    ["me"],
  ];
  for (const queryKey of keys) {
    qc.invalidateQueries({ queryKey });
  }
}

export function UndoToastHost() {
  const qc = useQueryClient();
  const [toast, setToast] = useState<UndoToastState | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const onUndoAvailable = (event: Event) => {
      const detail = (event as CustomEvent<UndoAvailableDetail>).detail;
      const startedAt = Date.now();
      setNow(startedAt);
      setToast({
        id: startedAt,
        message: detail?.message || "Action saved.",
        expiresAt: startedAt + UNDO_WINDOW_MS,
        status: "ready",
      });
    };
    window.addEventListener(UNDO_AVAILABLE_EVENT, onUndoAvailable);
    return () => window.removeEventListener(UNDO_AVAILABLE_EVENT, onUndoAvailable);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [toast]);

  useEffect(() => {
    if (!toast || toast.status !== "ready") return;
    if (now < toast.expiresAt) return;
    setToast(null);
  }, [now, toast]);

  useEffect(() => {
    if (!toast || toast.status !== "done") return;
    const timer = window.setTimeout(() => setToast(null), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const secondsLeft = useMemo(() => {
    if (!toast) return 0;
    return Math.max(0, Math.ceil((toast.expiresAt - now) / 1000));
  }, [now, toast]);

  if (!toast) return null;

  const undoDisabled = toast.status !== "ready";
  const body =
    toast.status === "done"
      ? toast.detail || "Undone."
      : toast.status === "error"
        ? toast.detail || "Undo failed."
        : toast.message;

  return (
    <div className="fixed bottom-4 right-4 z-[95] pointer-events-none">
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-auto flex w-[min(22rem,calc(100vw-2rem))] items-center gap-3 rounded-sm border border-hairline-signal/50 bg-void px-3 py-3 text-sm text-parchment shadow-lg"
      >
        <Undo2 className="h-4 w-4 shrink-0 text-signal" aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="truncate leading-relaxed">{body}</div>
          {toast.status === "ready" && (
            <div className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              {secondsLeft}s undo window
            </div>
          )}
        </div>
        {toast.status === "ready" || toast.status === "working" ? (
          <button
            type="button"
            disabled={undoDisabled}
            onClick={async () => {
              setToast((prev) => prev && { ...prev, status: "working" });
              try {
                const result = await undoLastAction();
                invalidateAfterUndo(qc);
                setToast((prev) =>
                  prev && {
                    ...prev,
                    status: "done",
                    detail: result.message || "Undone.",
                  }
                );
              } catch (error) {
                setToast((prev) =>
                  prev && {
                    ...prev,
                    status: "error",
                    detail:
                      error instanceof Error
                        ? error.message
                        : "Undo failed.",
                  }
                );
              }
            }}
            className="inline-flex min-h-9 shrink-0 items-center justify-center gap-1 rounded-sm border border-signal/45 bg-signal/10 px-3 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 hover:text-signal-neon disabled:cursor-not-allowed disabled:opacity-55"
          >
            {toast.status === "working" && (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            )}
            Undo
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => setToast(null)}
          aria-label="Dismiss undo"
          className="shrink-0 text-dust-deep transition-colors hover:text-parchment"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
