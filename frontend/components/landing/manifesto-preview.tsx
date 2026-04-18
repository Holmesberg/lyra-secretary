/**
 * Manifesto preview — quotes are embedded inline so the section remains
 * self-contained even after the source repo goes private. Each quote is
 * extracted verbatim from MANIFESTO.md and attributed to its section.
 */
const FIELD_NOTES = [
  {
    quote:
      "Most productivity tools assume their insights are accurate. Lyra tests its own.",
    attribution: "Manifesto · What This Is",
  },
  {
    quote:
      "Delta is the gap between what you planned and what you executed. It is ground truth. It cannot lie.",
    attribution: "Manifesto · The Core Variables",
  },
  {
    quote:
      "Every productivity system measures estimation error. Nobody measures whether the planning layer is being used at all.",
    attribution: "Manifesto · The Most Original Variable",
  },
];

export function ManifestoPreview() {
  return (
    <section id="manifesto" className="relative py-24 md:py-32">
      <div className="mx-auto max-w-3xl px-6 md:px-10">
        {/* Central question — the manifesto's load-bearing line. */}
        <div className="text-center">
          <p className="mb-6 text-xs uppercase tracking-wider text-signal">
            From the Manifesto
          </p>
          <blockquote className="text-2xl font-medium leading-[1.25] tracking-tight text-parchment md:text-[2rem]">
            “Are humans wrong about themselves in a structured way that
            predicts failure?”
          </blockquote>

          <div className="mx-auto mt-7 max-w-lg space-y-3 text-base leading-relaxed text-dust md:text-[17px]">
            <p>
              If yes — the error is modelable, correctable, and eventually
              preventable.
            </p>
            <p>If no — the data tells us that too, and we pivot.</p>
            <p className="text-parchment">
              Everything in this system exists to answer that question
              cleanly.
            </p>
          </div>
        </div>

        {/* Three supporting field notes — pulled inline so the section
           stays intact when the repo goes private. */}
        <div className="mt-20 grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-hairline bg-hairline md:grid-cols-3">
          {FIELD_NOTES.map((q) => (
            <figure
              key={q.attribution}
              className="bg-void-2/60 p-7 transition-colors hover:bg-void-2"
            >
              <blockquote className="text-base leading-relaxed text-parchment">
                “{q.quote}”
              </blockquote>
              <figcaption className="mt-5 text-[11px] uppercase tracking-wider text-dust-deep">
                — {q.attribution}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
