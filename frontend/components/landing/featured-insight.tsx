import { CornerMarks } from "./corner-marks";

/**
 * Featured insight as a terminal-readout frame — the kind of panel you'd
 * see on an instrument, not a SaaS marketing card.
 *
 * Insight grounded in live Supabase data (2026-04-18):
 *   n = 12 afternoon sessions · avg delta_minutes = -46.9  → "47 min over plan"
 */
export function FeaturedInsight() {
  return (
    <section className="relative py-24 md:py-32">
      <div className="mx-auto max-w-3xl px-6 md:px-10">
        <div className="mb-8 flex items-center justify-center gap-4">
          <span className="h-px w-10 bg-signal/60" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
            // one finding
          </span>
          <span className="h-px w-10 bg-signal/60" />
        </div>

        <div className="relative">
          <CornerMarks size={14} thickness={1.5} color="rgba(77, 212, 232, 0.75)" />
          <div className="terminal-panel px-6 py-10 md:px-12 md:py-14">
            {/* status header */}
            <div className="mb-6 flex items-center justify-between">
              <p className="font-mono text-[10px] uppercase tracking-widest text-signal">
                :: pattern.detected
              </p>
              <p className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                confidence · high
              </p>
            </div>

            <blockquote className="text-center">
              <p className="font-display text-[1.75rem] font-medium leading-[1.15] tracking-tight text-parchment md:text-[2.5rem]">
                Your afternoon tasks run{" "}
                <span className="neon-ember">47 minutes over plan</span>.
                <span className="block mt-2 text-dust md:text-[2.25rem]">
                  Consistently.
                </span>
              </p>
              <footer className="mt-8 flex items-center justify-center gap-4 font-mono text-[10px] uppercase tracking-widest text-dust">
                <span>operative-001</span>
                <span className="text-signal/40">·</span>
                <span>n = 12 afternoon sessions</span>
                <span className="text-signal/40">·</span>
                <span>14-day window</span>
              </footer>
            </blockquote>
          </div>
        </div>

        <p className="mx-auto mt-10 max-w-md text-center text-sm leading-relaxed text-dust-deep">
          Patterns look obvious in hindsight. The trick is noticing them
          before they&apos;ve cost you another week.
        </p>
      </div>
    </section>
  );
}
