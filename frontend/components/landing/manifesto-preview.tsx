import { CornerMarks } from "./corner-marks";

const FIELD_NOTES = [
  {
    quote:
      "Most productivity tools assume their insights are accurate. Barzakh tests its own.",
    section: "Measurement Doctrine",
  },
  {
    quote:
      "Unknown exposure state is not clean, neutral, bounded, zero, or average.",
    section: "Exposure Boundary",
  },
  {
    quote:
      "Archetypes are cold-start priors, not identity. Personal traces must be allowed to override them.",
    section: "Cold-Start Priors",
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
            about their own execution capacity in a{" "}
            <span className="neon-cyan">structured</span>, modelable way?
            <span className="text-signal/70">&rdquo;</span>
          </blockquote>

          <div className="mx-auto mt-10 max-w-lg space-y-3 text-base leading-relaxed text-dust md:text-[17px]">
            <p>
              If yes, Barzakh can earn stronger inference rights from repeated,
              provenance-clean traces.
            </p>
            <p>
              If no, the system should say less, retire weak mechanisms, and
              preserve user trust.
            </p>
            <p className="text-parchment">
              The architecture is built to make both outcomes visible.
            </p>
          </div>
        </div>

        <div className="mt-20 grid grid-cols-1 gap-5 md:grid-cols-3">
          {FIELD_NOTES.map((note, index) => (
            <div key={note.section} className="relative">
              <CornerMarks
                size={8}
                thickness={1}
                color="rgba(77, 212, 232, 0.4)"
              />
              <figure className="terminal-panel h-full p-6">
                <p className="mb-4 font-mono text-[9px] uppercase tracking-widest text-signal">
                  :: note.{index + 1}
                </p>
                <blockquote className="text-sm leading-relaxed text-parchment">
                  &ldquo;{note.quote}&rdquo;
                </blockquote>
                <figcaption className="mt-5 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                  section / {note.section}
                </figcaption>
              </figure>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
