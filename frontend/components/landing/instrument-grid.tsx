import { CornerMarks } from "./corner-marks";

const TILES = [
  {
    code: "01",
    title: "Trace substrate",
    body: "Brain dump, manual tasks, planned times, timers, pauses, completion, and recovery create the behavioral trace. External context stays marked as external.",
  },
  {
    code: "02",
    title: "Cortex",
    body: "Read-time projections recompute planned active minutes, executed active minutes, wall time, pause time, execution multipliers, and deltas from source rows.",
  },
  {
    code: "03",
    title: "Clean profiles",
    body: "Measured execution, planning calibration, pause process, and descriptive history have different admission rules. Retroactive and repaired data are not silently promoted.",
  },
  {
    code: "04",
    title: "Exposure ledger",
    body: "User-facing insights, nudges, predictions, and mirrors are intervention candidates. Unknown exposure state fails closed instead of becoming baseline-clean.",
  },
  {
    code: "05",
    title: "Cold-start priors",
    body: "Archetypes initialize similarity priors, not identities. Personal traces can reinforce, diffuse, or override the starting profile over time.",
  },
  {
    code: "06",
    title: "Bounded AI",
    body: "LLMs enrich, parse, assist operators, and help build. The product core remains explicit, probabilistic, inspectable, and rule-governed.",
  },
];

export function InstrumentGrid() {
  return (
    <section id="instrument" className="relative py-24 md:py-32">
      <div className="mx-auto max-w-5xl px-6 md:px-10">
        <div className="mx-auto max-w-2xl text-center">
          <p className="mb-6 font-mono text-[11px] uppercase tracking-widest text-signal">
            <span className="text-signal/60">//</span> the instrument
          </p>
          <h2 className="font-display text-4xl font-medium leading-[1.1] tracking-tight text-parchment md:text-5xl">
            What this actually <span className="neon-cyan">measures</span>.
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {TILES.map((tile) => (
            <div key={tile.code} className="relative">
              <CornerMarks
                size={10}
                thickness={1}
                color="rgba(77, 212, 232, 0.45)"
              />
              <article className="terminal-panel group h-full px-7 py-8 transition-all hover:border-signal/30">
                <div className="mb-5 flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
                    :: module.{tile.code}
                  </span>
                  <span className="h-1.5 w-1.5 rounded-full bg-signal/70 transition-all group-hover:bg-signal group-hover:shadow-[0_0_8px_rgba(77,212,232,0.9)]" />
                </div>
                <h3 className="font-display text-2xl font-medium text-parchment md:text-[1.75rem]">
                  {tile.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-dust">
                  {tile.body}
                </p>
              </article>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
