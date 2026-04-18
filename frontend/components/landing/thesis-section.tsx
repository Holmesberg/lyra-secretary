export function ThesisSection() {
  return (
    <section id="thesis" className="relative py-32 md:py-40">
      <div className="mx-auto max-w-2xl px-6 text-center md:px-10">
        <h2 className="text-3xl font-medium leading-[1.1] tracking-tight text-parchment md:text-5xl">
          Your Calendar Only
          <br />
          Stores Intentions
        </h2>

        <div className="mx-auto mt-10 max-w-lg space-y-5 text-base leading-relaxed text-dust md:text-[17px]">
          <p>
            Traditional productivity tools remember what you planned. They
            ignore what actually happened.
          </p>
          <p>
            Tasks overrun. Focus drops. Energy shifts. Plans fail.
            <br />
            No system learns from that.
          </p>
          <p className="pt-2 text-parchment">Until now.</p>
        </div>
      </div>
    </section>
  );
}
