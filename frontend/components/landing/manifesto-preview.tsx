import { CornerMarks } from "./corner-marks";

const FIELD_NOTES = [
  {
    quote:
      "Most productivity tools assume their insights are accurate. Lyra tests its own.",
    section: "What This Is",
  },
  {
    quote:
      "Delta is the gap between what you planned and what you executed. It cannot lie.",
    section: "The Core Variables",
  },
  {
    quote:
      "Every productivity system measures estimation error. Nobody measures whether the planning layer is being used at all.",
    section: "The Most Original Variable",
  },
];

export function ManifestoPreview() {
  return (
    <section id="manifesto" className="relative py-24 md:py-32">
      <div className="mx-auto max-w-3xl px-6 md:px-10">
        <div className="text-center">
          <p className="mb-6 font-mono text-[11px] uppercase tracking-widest text-signal">
            <span className="text-signal/60">//</span> the question
          </p>
          <blockquote className="font-display text-[1.75rem] font-medium leading-[1.2] tracking-tight text-parchment md:text-[2.5rem]">
            <span className="text-signal/70">&ldquo;</span>Are humans wrong
            about themselves in a{" "}
            <span className="neon-cyan">structured</span> way that predicts
            failure?<span className="text-signal/70">&rdquo;</span>
          </blockquote>

          <div className="mx-auto mt-10 max-w-lg space-y-3 text-base leading-relaxed text-dust md:text-[17px]">
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

        <div className="mt-20 grid grid-cols-1 gap-5 md:grid-cols-3">
          {FIELD_NOTES.map((q) => (
            <div key={q.section} className="relative">
              <CornerMarks
                size={8}
                thickness={1}
                color="rgba(77, 212, 232, 0.4)"
              />
              <figure className="terminal-panel h-full p-6">
                <p className="mb-4 font-mono text-[9px] uppercase tracking-widest text-signal">
                  :: note.{FIELD_NOTES.indexOf(q) + 1}
                </p>
                <blockquote className="text-sm leading-relaxed text-parchment">
                  &ldquo;{q.quote}&rdquo;
                </blockquote>
                <figcaption className="mt-5 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                  § {q.section}
                </figcaption>
              </figure>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
