"use client";
/**
 * Guided tour overlay — 8-step first-run walkthrough.
 *
 * Fires for users who have completed onboarding (a seeded starter task
 * exists) but haven't yet seen the tour. Skippable anywhere; completion
 * and skip stamps are stored server-side so the overlay never re-fires.
 *
 * Design notes (see `docs/parked_ideas.md §Guided product tour`):
 * - No interactive DOM-targeting highlighting. Just a centered modal
 *   with Next/Skip. Interactive highlighting is brittle to DOM shifts
 *   between framework versions and doesn't pay for itself at v1.
 * - No auto-advance, no countdown. User-paced.
 * - No gamification (streaks / badges / XP). Per `do_not_add.md`.
 * - Escape key dismisses (counts as "skip").
 * - Every step render logs a `reflection_view_log` row typed as
 *   `tutorial` so VT-21 can eventually ask whether tour exposure
 *   correlates with D7 return.
 *
 * Triggered by a flag in `(app)/layout.tsx`: renders when `me.onboarding_completed_at`
 * IS NOT NULL AND both tutorial stamps ARE NULL.
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

const STEPS: Array<{ title: string; body: string }> = [
  {
    title: "Welcome to Lyra",
    body:
      "Lyra measures how long your tasks actually take vs how long you thought they would. Over time you see the shape of your own planning — where you overrun, where you scope-inflate, where you're spot-on.",
  },
  {
    title: "Your first task is waiting",
    body:
      '"Plan your week — brain dump and triage" has been seeded on your /today feed. Click Start to fire a timer; we\'ll ask how ready you feel before you begin. Edit the time or delete it if you want to build your own setup.',
  },
  {
    title: "A 1–5 readiness rating",
    body:
      "Before every task we ask how ready you feel (1 = drained, 5 = sharp). Not scored, not shown to anyone — it's calibration input. The rating takes two seconds and you can always skip if you don't feel a clear answer.",
  },
  {
    title: "Stop + reflect",
    body:
      "When you stop a timer we ask how focused you felt during the run (1–5 again). The gap between readiness before and reflection after is one of the signals Lyra tracks. It's not graded — it's data about you.",
  },
  {
    title: "Calendar view",
    body:
      "The /calendar page shows every task on a week or month grid. Drag planned tasks to reschedule; past tasks are locked to protect the measurement. Your external Google Calendar events can appear here too as muted grey blocks.",
  },
  {
    title: "Insights, once you have data",
    body:
      "/insights unlocks a calibration mirror after ~10 completed tasks — your average delta, your readiness pattern, the categories where you overrun or underrun most. It's honest (sometimes uncomfortable) and it sharpens over time.",
  },
  {
    title: "Integrations are optional",
    body:
      "Settings → Integrations lets you connect Google Calendar if you want your external events alongside planned Lyra tasks. Nothing is required. You'll never see a consent screen unless you click Connect.",
  },
  {
    title: "Lyra stays out of your way",
    body:
      "No streaks, no guilt, no push notifications until you've earned them. The system is a mirror, not a coach. If something feels off — a nudge that lands wrong, a prompt that interrupts — tell us from Settings. You're the expert on you.",
  },
];

export interface TutorialOverlayProps {
  onFinished: () => void;
}

export function TutorialOverlay({ onFinished }: TutorialOverlayProps) {
  const [step, setStep] = useState(0);
  const [acting, setActing] = useState(false);

  const total = STEPS.length;
  const current = STEPS[step];
  const isFirst = step === 0;
  const isLast = step === total - 1;

  const finish = useCallback(
    async (action: "complete" | "skip") => {
      if (acting) return;
      setActing(true);
      try {
        const endpoint =
          action === "complete"
            ? "/v1/users/me/tutorial/complete"
            : "/v1/users/me/tutorial/skip";
        await api(endpoint, { method: "POST" });
      } catch (e) {
        console.warn("tutorial stamp failed (non-blocking):", e);
      } finally {
        onFinished();
      }
    },
    [acting, onFinished]
  );

  // Keyboard shortcuts — Esc skips, Enter advances / finishes.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        void finish("skip");
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (isLast) void finish("complete");
        else setStep((s) => Math.min(total - 1, s + 1));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [finish, isLast, total]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="tutorial-title"
      className="fixed inset-0 z-[80] flex items-center justify-center bg-void/80 p-6 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-sm border border-hairline-signal/30 bg-void-2 p-6 shadow-xl">
        {/* Progress indicator */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-1.5">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className={`h-1 rounded-full transition-all ${
                  i === step
                    ? "w-6 bg-signal"
                    : i < step
                    ? "w-1.5 bg-signal/50"
                    : "w-1.5 bg-dust-deep/40"
                }`}
              />
            ))}
          </div>
          <span className="text-[11px] text-dust-deep">
            {step + 1} / {total}
          </span>
        </div>

        {/* Body */}
        <h2
          id="tutorial-title"
          className="mb-2 text-lg font-semibold tracking-tight text-parchment"
        >
          {current.title}
        </h2>
        <p className="mb-6 text-sm leading-relaxed text-dust">
          {current.body}
        </p>

        {/* Actions */}
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => void finish("skip")}
            disabled={acting}
            className="text-xs text-dust-deep underline-offset-2 transition-colors hover:text-parchment hover:underline disabled:opacity-50"
          >
            {isFirst ? "Skip tour" : "Skip rest"}
          </button>

          <div className="flex items-center gap-2">
            {!isFirst && (
              <button
                type="button"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={acting}
                className="rounded-sm border border-hairline-signal/40 bg-transparent px-3 py-1.5 text-xs text-parchment transition-colors hover:bg-signal/5 hover:text-signal disabled:opacity-50"
              >
                Back
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                if (isLast) void finish("complete");
                else setStep((s) => Math.min(total - 1, s + 1));
              }}
              disabled={acting}
              className="rounded-sm border border-signal/40 bg-signal/10 px-3 py-1.5 text-xs font-medium text-signal transition-colors hover:bg-signal/20 hover:text-signal-neon disabled:opacity-50"
            >
              {isLast ? "Get started" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
