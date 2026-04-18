import { CornerMarks } from "./corner-marks";

const TILES = [
  {
    code: "01",
    title: "Intel",
    body: "Planned vs actual task duration. Pre-task readiness (1–5). Post-task reflection. Pause reasons. Initiation delay. Nothing inferred — everything logged.",
  },
  {
    code: "02",
    title: "Mirror",
    body: "After ten sessions per category, LyraOS surfaces bias factor, time-of-day performance, cascade risk. Insights unlock progressively — honest about what the instrument can't yet say.",
  },
  {
    code: "03",
    title: "Stopwatch",
    body: "Start, pause with reason, resume, stop — with a thirty-second undo window and retroactive logging for the sessions you forgot to log in real time.",
  },
  {
    code: "04",
    title: "Falsification",
    body: "A research layer validates whether any insight actually predicts anything. Pre-registered kill criteria. The instrument falsifies itself on a schedule.",
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

        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {TILES.map((t) => (
            <div key={t.code} className="relative">
              <CornerMarks
                size={10}
                thickness={1}
                color="rgba(77, 212, 232, 0.45)"
              />
              <article className="terminal-panel group h-full px-7 py-8 transition-all hover:border-signal/30">
                <div className="mb-5 flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
                    :: module.{t.code}
                  </span>
                  <span className="h-1.5 w-1.5 rounded-full bg-signal/70 transition-all group-hover:bg-signal group-hover:shadow-[0_0_8px_rgba(77,212,232,0.9)]" />
                </div>
                <h3 className="font-display text-2xl font-medium text-parchment md:text-[1.75rem]">
                  {t.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-dust">
                  {t.body}
                </p>
              </article>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
