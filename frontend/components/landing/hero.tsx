"use client";

import Image from "next/image";
import { signIn } from "next-auth/react";
import { motion } from "motion/react";
import { CornerMarks } from "./corner-marks";

export function Hero() {
  return (
    <section
      id="top"
      className="relative isolate overflow-hidden pt-28 md:pt-36"
    >
      <div className="mx-auto max-w-7xl px-6 md:px-10">
        {/* === Hero grid: copy left, product right (matches Landing Page.png) === */}
        <div className="grid grid-cols-1 items-center gap-14 lg:grid-cols-12 lg:gap-12">
          {/* Left: copy column */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.95, ease: [0.16, 1, 0.3, 1] }}
            className="order-1 lg:col-span-6"
          >
            <p className="terminal-prefix font-mono text-[11px] font-medium uppercase tracking-widest text-signal">
              For people who plan well and still fail themselves
            </p>

            <h1 className="mt-6 font-display font-medium leading-[0.92] tracking-tight text-parchment">
              <span className="block text-[3rem] md:text-[4.25rem] lg:text-[5rem]">
                Your Cognitive
              </span>
              <span className="neon-cyan block text-[3rem] md:text-[4.25rem] lg:text-[5rem]">
                Operating
              </span>
              <span className="block text-[3rem] md:text-[4.25rem] lg:text-[5rem]">
                System<span className="text-ember">.</span>
              </span>
            </h1>

            <p className="mt-7 max-w-xl text-base leading-relaxed text-dust md:text-[17px]">
              Why do you keep missing your own plans? Lyra quietly logs every
              estimate you make and every outcome that follows — then shows
              you the pattern you couldn&apos;t see alone.
            </p>
            <p className="mt-3 max-w-xl font-mono text-xs uppercase tracking-widest text-ember md:text-[13px]">
              Not a productivity app. A mirror.
            </p>

            <div className="mt-9 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:flex-wrap">
              <button
                onClick={() => signIn("google", { callbackUrl: "/today" })}
                className="cyber-pill cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                Sign in with Google
                <span aria-hidden>→</span>
              </button>
              <a
                href="#live-data"
                className="cyber-pill cyber-pill-outline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-parchment/30"
              >
                See Live Demo
              </a>
            </div>
          </motion.div>

          {/* Right: product chrome (laptop with insights — the hero visual) */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              duration: 1.1,
              delay: 0.15,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="order-2 lg:col-span-6"
          >
            <div className="relative mx-auto max-w-xl lg:max-w-none">
              {/* Atmospheric glow behind the product */}
              <div
                aria-hidden
                className="pointer-events-none absolute -inset-10 -z-10 rounded-3xl bg-signal/12 blur-3xl"
              />
              <div
                aria-hidden
                className="pointer-events-none absolute -right-8 -top-8 -z-10 h-40 w-40 rounded-full bg-ember/18 blur-3xl"
              />
              <CornerMarks
                size={14}
                thickness={1.5}
                color="rgba(77, 212, 232, 0.75)"
              />
              <div className="relative overflow-hidden rounded-sm border border-hairline-signal bg-void-2 shadow-[0_40px_120px_-20px_rgba(77,212,232,0.35)]">
                {/* status header chrome */}
                <div className="flex items-center justify-between border-b border-hairline-signal bg-void/80 px-4 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-ember/70" />
                    <span className="h-2 w-2 rounded-full bg-dust/50" />
                    <span className="h-2 w-2 rounded-full bg-signal/80" />
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-dust">
                    lyraos // insights // operative-001
                  </span>
                  <span className="font-mono text-[10px] text-signal motion-safe:animate-pulse-glow">
                    ●
                  </span>
                </div>
                <div className="scan-lines">
                  <Image
                    src="/insights-v1.png"
                    alt="LyraOS insights dashboard — 45 sessions analyzed across estimation, time-of-day, abandonment, pause pattern, and category dimensions."
                    width={1160}
                    height={980}
                    priority
                    className="block w-full"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* === Real-data metrics strip — pulled from operator's Supabase 2026-04-18 === */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="mt-20 md:mt-24"
        >
          <div className="relative">
            <CornerMarks size={10} color="rgba(245, 169, 106, 0.5)" />
            <div className="terminal-panel px-6 py-7 md:px-10">
              <div className="grid grid-cols-2 gap-y-7 sm:grid-cols-4 sm:gap-y-0 sm:divide-x sm:divide-hairline">
                <Metric label="Δ delta" value="−32 min" caption="vs plan · overrun" />
                <Metric label="readiness μ" value="3.7 / 5" caption="self-rated" />
                <Metric label="pauses / session" value="1.2" caption="avg breaks" />
                <Metric label="init delay" value="10 min" caption="late starts" />
              </div>
              <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                :: real data · 45 sessions · operative-001 · 14-day window
              </p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Build-publicly band */}
      <div className="mt-20 border-y border-hairline bg-void/60 py-5">
        <p className="mx-auto max-w-3xl px-6 text-center font-mono text-[11px] uppercase tracking-widest text-dust">
          Built publicly by an AI Engineering student · exploring
          neuroadaptive systems · Cairo, 2026
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
    <div className="flex flex-col items-center gap-1.5 px-4 text-center sm:items-start sm:text-left">
      <span className="data-prefix font-mono text-[10px] uppercase tracking-widest text-dust-deep">
        {label}
      </span>
      <span className="font-display text-2xl font-medium tabular-nums text-signal neon-cyan md:text-[2rem]">
        {value}
      </span>
      <span className="font-mono text-[10px] uppercase tracking-widest text-dust">
        {caption}
      </span>
    </div>
  );
}
