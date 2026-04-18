const TILES = [
  {
    title: "Intel",
    body: "Planned vs actual task duration. Pre-task readiness (1–5). Post-task reflection. Pause reasons. Initiation delay. Nothing inferred — everything logged.",
  },
  {
    title: "Mirror",
    body: "After ten sessions per category, LyraOS surfaces bias factor, time-of-day performance, cascade risk. Insights unlock progressively — honest about what the instrument can't yet say.",
  },
  {
    title: "Stopwatch",
    body: "Start, pause with reason, resume, stop — with a thirty-second undo window and retroactive logging for the sessions you forgot to log in real time.",
  },
  {
    title: "Falsification",
    body: "A research layer validates whether any insight actually predicts anything. Pre-registered kill criteria. The instrument falsifies itself on a schedule.",
  },
];

export function InstrumentGrid() {
  return (
    <section id="instrument" className="relative py-24 md:py-32">
      <div className="mx-auto max-w-5xl px-6 md:px-10">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-medium leading-[1.1] tracking-tight text-parchment md:text-4xl">
            What this actually measures
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {TILES.map((t) => (
            <div
              key={t.title}
              className="rounded-xl border border-hairline bg-void-2/40 p-7 transition-colors hover:border-signal/30 hover:bg-void-2/60"
            >
              <h3 className="text-xl font-medium text-parchment">{t.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-dust">{t.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
