import { CornerMarks } from "./corner-marks";

const SURFACES = [
  {
    status: "shipped",
    title: "User-facing product",
    items: [
      "Google sign-in",
      "brain-dump onboarding",
      "task planning",
      "timer execution",
      "pause/resume/stop",
      "overdue recovery",
      "calendar view",
      "deadlines",
      "Moodle import",
      "read-only Google Calendar context",
      "Pulse",
      "Insights",
      "account export/deletion",
    ],
  },
  {
    status: "operator-only",
    title: "Internal runtime",
    items: [
      "operator cockpit",
      "OpenClaw operator-alert relay",
      "operator notifications",
      "topology verification",
      "exposure diagnostics",
    ],
  },
  {
    status: "future-gated",
    title: "Not publicly shipped",
    items: [
      "automatic rescheduling",
      "hidden calendar mutation",
      "validated adaptive scheduling",
      "confidence-backed recommendations",
      "BCI/cognitive-state input",
      "learning from interventions without exposure modeling",
    ],
  },
];

export function StatusSection() {
  return (
    <section id="status" className="relative border-y border-hairline bg-void-2/30 py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6 md:px-10">
        <div className="mx-auto max-w-2xl text-center">
          <p className="mb-6 font-mono text-[11px] uppercase tracking-widest text-signal">
            <span className="text-signal/60">//</span> shipped vs gated
          </p>
          <h2 className="font-display text-4xl font-medium leading-[1.1] tracking-tight text-parchment md:text-5xl">
            Current product, operator layer,{" "}
            <span className="neon-cyan">future research</span>.
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-sm leading-relaxed text-dust md:text-base">
            The public app is useful now, but the stronger adaptive claims are
            deliberately gated behind evidence, topology, identity, and exposure
            contracts.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 lg:grid-cols-3">
          {SURFACES.map((surface) => (
            <article key={surface.title} className="relative">
              <CornerMarks size={8} thickness={1} color="rgba(77, 212, 232, 0.4)" />
              <div className="terminal-panel h-full p-6">
                <p className="font-mono text-[10px] uppercase tracking-widest text-signal">
                  :: {surface.status}
                </p>
                <h3 className="mt-4 font-display text-2xl font-medium text-parchment">
                  {surface.title}
                </h3>
                <ul className="mt-5 space-y-2">
                  {surface.items.map((item) => (
                    <li
                      key={item}
                      className="flex gap-2 text-sm leading-relaxed text-dust"
                    >
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal/70" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
