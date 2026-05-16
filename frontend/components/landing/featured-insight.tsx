import { CornerMarks } from "./corner-marks";

/**
 * Featured insight as a terminal-readout frame: descriptive, bounded,
 * and explicitly not a recommendation.
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
          <CornerMarks
            size={14}
            thickness={1.5}
            color="rgba(77, 212, 232, 0.75)"
          />
          <div className="terminal-panel px-6 py-10 md:px-12 md:py-14">
            <div className="mb-6 flex items-center justify-between">
              <p className="font-mono text-[10px] uppercase tracking-widest text-signal">
                :: primary.synthesis
              </p>
              <p className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                descriptive / time-local
              </p>
            </div>

            <blockquote className="text-center">
              <p className="font-display text-[1.75rem] font-medium leading-[1.15] tracking-tight text-parchment md:text-[2.5rem]">
                Study drift is clustering{" "}
                <span className="neon-ember">later in the day</span>.
                <span className="mt-2 block text-dust md:text-[2.25rem]">
                  Work traces are staying calibrated.
                </span>
              </p>
              <footer className="mt-8 flex flex-wrap items-center justify-center gap-4 font-mono text-[10px] uppercase tracking-widest text-dust">
                <span>operator dogfood</span>
                <span className="text-signal/40">/</span>
                <span>bounded synthesis</span>
                <span className="text-signal/40">/</span>
                <span>not a prescription</span>
              </footer>
            </blockquote>
          </div>
        </div>

        <p className="mx-auto mt-10 max-w-md text-center text-sm leading-relaxed text-dust-deep">
          The system can describe what the trace currently suggests. Stronger
          guidance has to be earned by cleaner evidence, exposure tracking, and
          repeated outcomes.
        </p>
      </div>
    </section>
  );
}
