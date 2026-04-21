"use client";
/**
 * Onboarding surface — Path B first-session planning ritual.
 *
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║ TEMPORARILY DISABLED 2026-04-21                                  ║
 * ║                                                                  ║
 * ║ Not rendered anywhere — the (app)/layout.tsx conditional that    ║
 * ║ mounted this component has been commented out. The first-time    ║
 * ║ user experience is now a backend-seeded starter task (see        ║
 * ║ backend/app/core/security.py `_seed_starter_task`), which shows  ║
 * ║ up directly on /today when the user lands — no forced UI.        ║
 * ║                                                                  ║
 * ║ Re-enable post-Spring-School when the richer onboarding flow is  ║
 * ║ ready to ship:                                                   ║
 * ║  - Archetype instrument battery (MEQ-5, BFI-10, BSCS, GP-Short)  ║
 * ║  - Import ingestion (ICS drag-drop, Google Calendar OAuth)       ║
 * ║  - Progressive revelation ("your archetype: Planner" at N=5-7)   ║
 * ║                                                                  ║
 * ║ See docs/strategic_decisions_april_21.md §5 for the reversal     ║
 * ║ rationale.                                                       ║
 * ║                                                                  ║
 * ║ Code below is intact and passes TSC — do not let it bit-rot.     ║
 * ║ Run the build on every merge so a framework or API shift breaks  ║
 * ║ loudly rather than silently when we re-enable it.                ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * Original design (preserved for reference):
 *
 * Shown when the authenticated user has `onboarding_completed_at`
 * null on the `/users/me` response (see backend migration 025 and
 * docs/strategic_decisions_april_21.md). The backend stamps the
 * field atomically when the user creates their first task, so the
 * flow auto-exits as soon as submit succeeds.
 *
 * - Structural invariant, not a behavioral gate. The "Skip for now"
 *   link calls POST /users/me/skip-onboarding which stamps the same
 *   field, so the user can always bypass — but we record that they
 *   chose to, which the 2026-05-21 kill-criterion query reads.
 * - No LLM, no OpenClaw, no Telegram. Pure Lyra-codebase work
 *   (see memory: OpenClaw is operator-only until components are
 *   integrated).
 * - Category = "planning" (the un-merged slot, shipped 2026-04-21).
 *   Default start is now + 5min rounded, 30 min duration, brain-dump
 *   textarea focused on mount.
 * - Copy pitches measurement, not productivity. The promise is
 *   "Lyra starts learning your pattern here," not "we'll teach you
 *   to plan better."
 */
import { useEffect, useRef, useState } from "react";
import { createTask } from "@/lib/tasks";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/** Round up to next 5-minute mark — matches new-task-modal defaults. */
function nextFiveMin(from: Date = new Date()) {
  const d = new Date(from);
  const mins = d.getMinutes();
  const next5 = Math.ceil(mins / 5) * 5;
  if (next5 >= 60) d.setHours(d.getHours() + 1, 0, 0, 0);
  else d.setMinutes(next5, 0, 0);
  return d;
}

interface Props {
  userEmail: string;
  onCompleted: () => void;
}

export function OnboardingFlow({ userEmail, onCompleted }: Props) {
  // Meta-task defaults: NOW + 30 min. The planning ritual IS happening
  // right now during onboarding; scheduling it tomorrow (prior behavior)
  // told the user "plan again tomorrow" which is senseless when they're
  // mid-plan. User can still edit the times before submit.
  const defaults = (() => {
    const s = nextFiveMin();
    const e = new Date(s);
    e.setMinutes(e.getMinutes() + 30);
    return { start: formatLocal(s), end: formatLocal(e) };
  })();

  const [title, setTitle] = useState("Plan your week — brain dump and triage");
  const [description, setDescription] = useState("");
  const [start, setStart] = useState(defaults.start);
  const [end, setEnd] = useState(defaults.end);
  const [submitting, setSubmitting] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    // Focus the brain-dump textarea on mount — that's the
    // measurement-critical field (scope density, VT-22) and where we
    // want the user's attention to land, not the title (which has a
    // sensible default).
    textareaRef.current?.focus();
  }, []);

  async function handleCreate() {
    if (submitting || skipping) return;
    setError(null);
    setSubmitting(true);
    try {
      await createTask({
        title: title.trim() || "Plan your week",
        start,
        end,
        category: "planning",
        description: description.trim() || undefined,
      });
      // Backend stamped onboarding_completed_at atomically with the
      // task insert — the parent layout will re-fetch /users/me on
      // onCompleted and drop this surface.
      onCompleted();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create task");
      setSubmitting(false);
    }
  }

  async function handleSkip() {
    if (submitting || skipping) return;
    setError(null);
    setSkipping(true);
    try {
      await api("/v1/users/me/skip-onboarding", { method: "POST" });
      onCompleted();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to skip");
      setSkipping(false);
    }
  }

  return (
    <div className="min-h-screen bg-void text-parchment">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <div className="mb-10">
          <p className="terminal-prefix font-mono text-[11px] font-medium uppercase tracking-widest text-signal">
            Onboarding · operative-{userEmail.split("@")[0].slice(0, 8)}
          </p>
          <h1 className="mt-6 text-3xl font-semibold leading-tight tracking-tight text-parchment md:text-4xl">
            Lyra starts learning from the first plan you write.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-dust md:text-base">
            Plan your week. Brain dump everything that&apos;s on your mind —
            tasks, commitments, half-formed ideas. Lyra records what you
            expected and what actually happened. Patterns surface on their own,
            starting now.
          </p>
        </div>

        <div className="terminal-panel p-6">
          <div className="mb-5 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-signal motion-safe:animate-pulse-glow" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
              Your first planning task
            </span>
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="onb-title"
                className="font-mono text-[10px] font-medium uppercase tracking-widest text-dust"
              >
                Title
              </label>
              <input
                id="onb-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="h-9 rounded-sm border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="onb-description"
                className="font-mono text-[10px] font-medium uppercase tracking-widest text-dust"
              >
                Brain dump <span className="font-normal text-dust-deep">(what&apos;s on your mind?)</span>
              </label>
              <textarea
                id="onb-description"
                ref={textareaRef}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="- Deadline X on Friday&#10;- Call Y about Z&#10;- Finish the draft on N&#10;- Groceries this weekend"
                rows={6}
                className="resize-none rounded-sm border border-hairline-signal/30 bg-transparent px-3 py-2 text-sm text-parchment placeholder:text-dust-deep focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40"
              />
              <p className="text-[11px] text-dust-deep">
                Bulleted items will feed scope-density measurement later. For
                now: just dump. Nothing is committed yet.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="onb-start"
                  className="font-mono text-[10px] font-medium uppercase tracking-widest text-dust"
                >
                  Starts
                </label>
                <input
                  id="onb-start"
                  type="datetime-local"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="h-9 rounded-sm border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="onb-end"
                  className="font-mono text-[10px] font-medium uppercase tracking-widest text-dust"
                >
                  Ends
                </label>
                <input
                  id="onb-end"
                  type="datetime-local"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="h-9 rounded-sm border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
                {error}
              </div>
            )}

            <div className="mt-2 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
              <button
                onClick={handleSkip}
                disabled={submitting || skipping}
                className={cn(
                  "font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-parchment",
                  (submitting || skipping) && "opacity-40"
                )}
              >
                {skipping ? "Skipping…" : "Skip for now"}
              </button>
              <button
                onClick={handleCreate}
                disabled={submitting || skipping}
                className="cyber-pill cyber-pill-compact cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                {submitting ? "Creating…" : "Lock in my first plan →"}
              </button>
            </div>
          </div>
        </div>

        <p className="mt-10 text-center font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          :: planning ritual · session 0 · patterns emerge from here
        </p>
      </div>
    </div>
  );
}
