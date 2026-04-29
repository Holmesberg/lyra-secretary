"use client";
/**
 * InsightsPulse — preview-or-locked treatment for /insights on /pulse.
 *
 * Honest about the empty state. /insights gates its real cards on
 * EXECUTED session count thresholds — for new users (and most of the
 * alpha cohort) the page is just "unlock in N more sessions." On
 * /pulse we can't render a real card grid yet, so we show 4
 * locked-preview tiles with the labels of the cards that ARE coming
 * + a single live progress count toward the next unlock.
 *
 * If the user is past the unlock threshold (executed_session_count >= 6)
 * we show a sneak-peek of one calm summary line + a "View all" link.
 */
import Link from "next/link";

const FIRST_UNLOCK = 6;

const PREVIEW_TILES: { label: string; hint: string }[] = [
  { label: "Time of day", hint: "When you actually focus best" },
  { label: "Best category", hint: "Where you overrun the least" },
  { label: "Calibration", hint: "How honest your estimates are" },
  { label: "Pause rhythm", hint: "Your natural break cadence" },
];

export interface InsightsPulseProps {
  executedSessionCount: number;
}

export function InsightsPulse({ executedSessionCount }: InsightsPulseProps) {
  const unlocked = executedSessionCount >= FIRST_UNLOCK;
  const remaining = Math.max(0, FIRST_UNLOCK - executedSessionCount);
  const pct = Math.min(100, (executedSessionCount / FIRST_UNLOCK) * 100);

  return (
    <div className="terminal-panel p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="font-display text-[11px] font-medium uppercase tracking-macro text-dust">
          <span className="text-signal/70">{">>"}</span>{" "}
          <span className="ml-1">{unlocked ? "Patterns" : "Patterns · locked"}</span>
        </div>
        <Link
          href="/insights"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep hover:text-signal"
        >
          {unlocked ? "Open →" : "Preview →"}
        </Link>
      </div>

      {unlocked ? (
        <div className="space-y-2">
          <p className="text-xs text-parchment/85">
            Your patterns are warming up. Open{" "}
            <Link href="/insights" className="text-signal hover:underline">
              /insights
            </Link>{" "}
            for the full readout.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {PREVIEW_TILES.map((t) => (
              <div
                key={t.label}
                className="relative rounded-sm border border-hairline bg-void-2/40 px-3 py-2.5"
              >
                {/* Diagonal lock-stripe */}
                <span
                  aria-hidden
                  className="pointer-events-none absolute inset-0 rounded-sm opacity-30"
                  style={{
                    backgroundImage:
                      "repeating-linear-gradient(45deg, rgba(74,81,104,0.18) 0 6px, transparent 6px 12px)",
                  }}
                />
                <div className="relative">
                  <div className="font-display text-[10px] uppercase tracking-macro text-dust-deep">
                    {t.label}
                  </div>
                  <div className="mt-0.5 text-[10px] leading-snug text-dust">
                    {t.hint}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-1">
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                Unlock in
              </span>
              <span className="font-mono text-[10px] tabular-nums text-signal">
                {remaining} more {remaining === 1 ? "session" : "sessions"}
              </span>
            </div>
            <div className="relative h-1.5 overflow-hidden rounded-full bg-void-2 border border-hairline">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-signal/40 to-signal"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              {executedSessionCount} / {FIRST_UNLOCK} sessions analyzed
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
