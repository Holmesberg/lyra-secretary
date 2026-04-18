"use client";

import Image from "next/image";
import { signIn } from "next-auth/react";
import { motion } from "motion/react";

export function Hero() {
  return (
    <section
      id="top"
      className="relative isolate overflow-hidden pt-32 md:pt-40"
    >
      {/* Decorative LyraOS brand watermark — anchored to the upper-left
         beyond the content column so it never collides with the headline or
         CTAs. Pulled slightly off-screen on the left so it reads as ambient
         atmosphere rather than competing decoration. lg-only to avoid any
         risk of overlap on tablets. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-16 top-16 -z-10 hidden lg:block xl:-left-8"
      >
        <Image
          src="/lyraos-logo.png"
          alt=""
          width={240}
          height={240}
          priority
          className="h-56 w-56 opacity-25 mix-blend-screen xl:h-64 xl:w-64"
        />
      </div>

      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-14 px-6 md:grid-cols-12 md:gap-10 md:px-8">
        {/* Left: headline column */}
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="relative z-10 md:col-span-6"
        >
          <h1 className="text-[2.5rem] font-medium leading-[1.05] tracking-tight text-parchment md:text-[3.75rem] lg:text-[4.5rem]">
            <span className="block">Your Cognitive</span>
            <span className="block">Operating System.</span>
          </h1>

          <p className="mt-7 max-w-md text-base leading-relaxed text-dust md:text-[17px]">
            LyraOS tracks the difference between what you planned and what
            actually happened — then learns how you truly work.
          </p>

          <div className="mt-9 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:flex-wrap">
            <button
              onClick={() => signIn("google", { callbackUrl: "/today" })}
              className="pill pill-primary justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
            >
              Sign in with Google
              <span aria-hidden>→</span>
            </button>
            <a
              href="#live-data"
              className="pill pill-outline justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-parchment/30"
            >
              See Live Demo
            </a>
          </div>
        </motion.div>

        {/* Right: product chrome */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.1, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="relative md:col-span-6"
        >
          {/* Laptop chrome — matches the reference. Screen contains the
             insights dashboard; base extends slightly wider with a subtle
             hinge notch. */}
          <div className="relative mx-auto max-w-md md:max-w-none">
            <div
              aria-hidden
              className="absolute -inset-8 -z-10 rounded-3xl bg-signal/12 blur-3xl"
            />
            <div
              aria-hidden
              className="absolute -right-6 -top-6 -z-10 h-32 w-32 rounded-full bg-ember/15 blur-3xl"
            />
            {/* Screen bezel */}
            <div className="relative overflow-hidden rounded-t-xl border-[6px] border-b-0 border-[#0d1320] bg-[#05070c] shadow-[0_30px_80px_-20px_rgba(77,212,232,0.3)] md:rounded-t-2xl md:border-[10px] md:border-b-0">
              <Image
                src="/insights-v1.png"
                alt="LyraOS insights dashboard — 45 sessions analyzed across estimation, time-of-day, abandonment, pause, and category dimensions."
                width={1160}
                height={980}
                priority
                className="block w-full"
              />
            </div>
            {/* Laptop base — extends ~6% wider on each side; thin hinge notch
               at top-center; rounded bottom matches a real lid-closed silhouette. */}
            <div className="relative mx-auto -mt-px h-3 w-[112%] -translate-x-[5.4%] rounded-b-[18px] bg-gradient-to-b from-[#1a1f30] via-[#0e1220] to-[#05070c] shadow-[0_24px_30px_-18px_rgba(0,0,0,0.7)] md:h-4">
              <div className="absolute left-1/2 top-0 h-1 w-16 -translate-x-1/2 rounded-b-full bg-[#05070c]" />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Real-data metrics strip — pulled from operator-001 in live Supabase
         on 2026-04-18 and hardcoded at build time. Honest snapshot of what
         the instrument has measured for the only person who has used it
         long enough to be measured. */}
      <div className="mt-20 border-t border-hairline bg-void/40">
        <div className="mx-auto max-w-5xl px-6 py-7 md:px-10">
          <div className="grid grid-cols-2 gap-y-6 sm:grid-cols-4 sm:gap-y-0 sm:divide-x sm:divide-hairline">
            <Metric label="Δ delta" value="−32 min" caption="vs plan" />
            <Metric label="readiness μ" value="3.7 / 5" caption="self-rated" />
            <Metric label="pauses / session" value="1.2" caption="avg breaks" />
            <Metric label="init delay" value="10 min" caption="late starts" />
          </div>
          <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-wider text-dust-deep">
            Real data · 45 sessions
          </p>
        </div>
      </div>

      {/* Build-in-public band — centered, between hero and thesis. */}
      <div className="border-y border-hairline bg-void/40 py-5">
        <p className="mx-auto max-w-3xl px-6 text-center text-[13px] text-dust">
          Built publicly by an AI Engineering student exploring the future of
          neuroadaptive systems
        </p>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 px-4 text-center sm:items-start sm:text-left">
      <span className="font-mono text-[10px] uppercase tracking-wider text-dust-deep">
        {label}
      </span>
      <span className="font-mono text-xl font-medium tabular-nums text-signal md:text-2xl">
        {value}
      </span>
      <span className="font-mono text-[10px] uppercase tracking-wider text-dust">
        {caption}
      </span>
    </div>
  );
}
