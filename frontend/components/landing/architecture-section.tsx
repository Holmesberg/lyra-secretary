import { CornerMarks } from "./corner-marks";

const STACK = [
  {
    label: "Frontend",
    title: "Next.js app + Google sign-in",
    body: "Users plan tasks, run timers, recover missed plans, connect optional context, and read bounded insight surfaces.",
  },
  {
    label: "Identity",
    title: "Backend JWT + request scope",
    body: "The browser presents a signed backend token; FastAPI resolves the user before user-owned reads or writes. Redis hot state is user-namespaced.",
  },
  {
    label: "Mutation",
    title: "Service-layer authorities",
    body: "Task, stopwatch, deadline, Moodle, and account deletion flows go through explicit product authorities instead of ad hoc writes.",
  },
  {
    label: "Persistence",
    title: "Postgres, Redis, workers",
    body: "SQLAlchemy models keep durable product and research rows; Redis carries live timer state, queues, and idempotency; APScheduler repairs and reconciles.",
  },
  {
    label: "Cortex",
    title: "Read-time canonicalization",
    body: "Derived metrics such as planned minutes, executed minutes, pause time, multipliers, and deltas are recomputed from provenance-aware rows.",
  },
  {
    label: "Governance",
    title: "Exposure ledger + registry",
    body: "Insights, nudges, and predictions are registered output surfaces. Baseline learning fails closed when exposure state is unknown.",
  },
];

const BOUNDARIES = [
  {
    title: "AI is bounded support",
    body: "LLM enrichment and OpenClaw support parsing, operator work, and implementation. They are not the behavioral truth substrate.",
  },
  {
    title: "Adaptive scheduling is future-gated",
    body: "The live product can observe and synthesize. It does not autonomously reschedule, mutate calendars, or make confidence-backed prescriptions.",
  },
  {
    title: "BCI is not collected",
    body: "Cognitive-state sensing is historical and future research context only. Current evidence comes from ordinary planning and execution traces.",
  },
];

export function ArchitectureSection() {
  return (
    <section id="architecture" className="relative border-y border-hairline bg-void-2/30 py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-6 md:px-10">
        <div className="mx-auto max-w-3xl text-center">
          <p className="mb-6 font-mono text-[11px] uppercase tracking-widest text-signal">
            <span className="text-signal/60">//</span> current architecture
          </p>
          <h2 className="font-display text-4xl font-medium leading-[1.1] tracking-tight text-parchment md:text-5xl">
            Product surface, measurement core,{" "}
            <span className="neon-cyan">explicit boundaries</span>.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-sm leading-relaxed text-dust md:text-base">
            Barzakh is intentionally more traditional than the hype suggests:
            rule-based where rules are safer, probabilistic where uncertainty
            matters, and conservative about what the system is allowed to claim.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {STACK.map((layer, index) => (
            <article key={layer.label} className="relative">
              <CornerMarks
                size={8}
                thickness={1}
                color="rgba(77, 212, 232, 0.4)"
              />
              <div className="terminal-panel h-full p-6">
                <div className="mb-4 flex items-center justify-between gap-4">
                  <span className="font-mono text-[9px] uppercase tracking-widest text-signal">
                    :: layer.{String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                    {layer.label}
                  </span>
                </div>
                <h3 className="font-display text-2xl font-medium text-parchment">
                  {layer.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-dust">
                  {layer.body}
                </p>
              </div>
            </article>
          ))}
        </div>

        <div id="boundaries" className="mt-16 grid grid-cols-1 gap-5 lg:grid-cols-3">
          {BOUNDARIES.map((item) => (
            <div key={item.title} className="border-l border-signal/40 pl-5">
              <p className="font-mono text-[10px] uppercase tracking-widest text-ember">
                boundary
              </p>
              <h3 className="mt-3 font-display text-2xl font-medium text-parchment">
                {item.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-dust">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
