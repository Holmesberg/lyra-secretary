export function ThesisSection() {
  return (
    <section id="thesis" className="relative py-32 md:py-44">
      <div className="mx-auto max-w-3xl px-6 text-center md:px-10">
        <p className="mb-8 font-mono text-[11px] uppercase tracking-widest text-signal">
          <span className="text-signal/60">//</span> The thesis
        </p>

        <h2 className="font-display text-[2.75rem] font-medium leading-[1.02] tracking-tight text-parchment md:text-[4.5rem]">
          <span className="block">Your calendar</span>
          <span className="block">only stores</span>
          <span className="neon-cyan block">intentions.</span>
        </h2>

        <div className="mx-auto mt-12 max-w-lg space-y-5 text-base leading-relaxed text-dust md:text-[17px]">
          <p>
            Traditional productivity tools remember what you{" "}
            <span className="text-parchment">planned</span>. They ignore what
            actually happened.
          </p>
          <p>
            Tasks overrun. Focus drops. Energy shifts. Plans fail.
            <br />
            <span className="text-parchment">
              No system learns from that.
            </span>
          </p>
        </div>

        <p className="mt-16 font-display text-3xl font-medium text-ember md:text-4xl">
          Until now.
        </p>
      </div>
    </section>
  );
}
