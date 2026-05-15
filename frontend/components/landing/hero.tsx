"use client";

import Image from "next/image";
import { motion } from "motion/react";
import { CornerMarks } from "./corner-marks";
import { GoogleSignInButton } from "./google-sign-in-button";

export function Hero() {
  return (
    <section
      id="top"
      className="relative isolate overflow-hidden pt-16 sm:pt-20 md:pt-32 lg:pt-36"
    >
      <div className="mx-auto max-w-7xl px-5 sm:px-6 md:px-10">
        {/* Mobile-only logo block — gives the brand its own moment at the
           top of the content flow since the mobile nav drops the logo. */}
        <div className="mb-8 flex flex-col items-center gap-3 sm:mb-10 md:hidden">
          <div className="relative">
            <div
              aria-hidden
              className="absolute inset-0 -z-10 rounded-full bg-signal/20 blur-2xl"
            />
            <Image
              src="/lyraos-logo.png"
              alt=""
              width={140}
              height={140}
              priority
              quality={100}
              sizes="140px"
              className="h-[140px] w-auto"
            />
          </div>
          <span className="font-display text-[1.75rem] font-medium leading-none tracking-tight text-parchment">
            LyraOS
          </span>
        </div>

        {/* === Hero grid: copy left, product right.
           lg:items-start top-aligns the two columns so the insights
           panel's top edge matches the H1 "Your Cognitive" top (via
           an invisible eyebrow-height spacer + lg:mt-6 on the right
           column). Bottom edge is natural — panel keeps its native
           aspect, no height cap, no object-cover crop. Mobile (<lg)
           stacks naturally. === */}
        <div className="grid grid-cols-1 items-center gap-10 sm:gap-12 lg:grid-cols-12 lg:items-start lg:gap-12">
          {/* Left: copy column. Entrance animation uses y-translate only —
             no `opacity:0` on initial state so crawlers + social previews
             see the copy as real text in the SSR HTML. */}
          <motion.div
            initial={{ y: 18 }}
            animate={{ y: 0 }}
            transition={{ duration: 0.95, ease: [0.16, 1, 0.3, 1] }}
            className="order-1 lg:col-span-5"
          >
            <p className="terminal-prefix font-mono text-[11px] font-medium uppercase tracking-widest text-signal">
              For people who plan well and still fail themselves
            </p>

            <h1 className="mt-5 font-display font-medium leading-[0.92] tracking-tight text-parchment sm:mt-6">
              <span className="block text-[2.75rem] sm:text-[3.35rem] md:text-[4.25rem] lg:text-[5rem]">
                Your Cognitive
              </span>
              <span className="neon-cyan block text-[2.75rem] sm:text-[3.35rem] md:text-[4.25rem] lg:text-[5rem]">
                Operating
              </span>
              <span className="block text-[2.75rem] sm:text-[3.35rem] md:text-[4.25rem] lg:text-[5rem]">
                System<span className="text-ember">.</span>
              </span>
            </h1>

            <p className="mt-6 max-w-xl text-base leading-relaxed text-dust sm:mt-7 md:text-[17px]">
              Why do you keep missing your own plans? Lyra quietly logs every
              estimate you make and every outcome that follows — then shows
              you the pattern you couldn&apos;t see alone.
            </p>
            <p className="mt-3 max-w-xl font-mono text-xs uppercase tracking-widest text-ember md:text-[13px]">
              Not a productivity app. A mirror.
            </p>

            <div className="mt-8 flex flex-col items-stretch gap-3 sm:mt-9 sm:flex-row sm:items-center sm:flex-wrap">
              <GoogleSignInButton
                className="cyber-pill cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                Sign in with Google
                <span aria-hidden>→</span>
              </GoogleSignInButton>
              <a
                href="#live-data"
                className="cyber-pill cyber-pill-outline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-parchment/30"
              >
                See Live Demo
              </a>
            </div>
          </motion.div>

          {/* Right: product chrome (laptop with insights — the hero visual).
             Scale-only entrance animation; opacity always 1 for SSR. */}
          <motion.div
            initial={{ scale: 0.97 }}
            animate={{ scale: 1 }}
            transition={{
              duration: 1.1,
              delay: 0.15,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="order-2 lg:col-span-7"
          >
            {/* Invisible eyebrow-height spacer — desktop-only. Mirrors the
               left column's terminal-prefix eyebrow line metric so that,
               with lg:mt-6 on the panel below, the insights top edge
               lines up with the H1 "Your Cognitive" top. Kept as a real
               <p> with identical font classes so line-height stays
               exactly in sync across md / lg breakpoints without magic
               pixel values. `invisible` (visibility:hidden) reserves
               vertical space without rendering glyphs. */}
            <div className="relative mx-auto w-full max-w-[38rem] lg:-mt-1 lg:max-w-none">
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
              {/* Panel chrome — natural image aspect preserved (no height
                 cap, no object-cover crop). Top edge aligns with H1-top
                 via the invisible eyebrow spacer + lg:mt-6 above. Bottom
                 edge falls wherever the image's native aspect lands. */}
              <div className="relative overflow-hidden rounded-sm border border-hairline-signal bg-void-2 shadow-[0_40px_120px_-20px_rgba(77,212,232,0.35)]">
                {/* status header chrome */}
                <div className="flex items-center justify-between border-b border-hairline-signal bg-void/80 px-3 py-2 sm:px-4 sm:py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-ember/70" />
                    <span className="h-2 w-2 rounded-full bg-dust/50" />
                    <span className="h-2 w-2 rounded-full bg-signal/80" />
                  </div>
                  <span className="font-mono text-[9px] uppercase tracking-widest text-dust sm:text-[10px]">
                    <span className="sm:hidden">insights // live</span>
                    <span className="hidden sm:inline">
                      lyraos // insights // operative-001
                    </span>
                  </span>
                  <span className="font-mono text-[10px] text-signal motion-safe:animate-pulse-glow">
                    ●
                  </span>
                </div>
                <div className="scan-lines">
                  <Image
                    src="/insights-v2.png"
                    alt="LyraOS insights dashboard with a primary synthesis card and supporting confidence-ranked behavioral evidence."
                    width={875}
                    height={780}
                    priority
                    quality={95}
                    unoptimized
                    sizes="(max-width: 640px) calc(100vw - 40px), (max-width: 1024px) min(100vw - 48px, 608px), 56vw"
                    className="block h-auto w-full"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* === Real-data metrics strip — pulled from operator's Supabase 2026-04-18.
           Y-translate-only entrance on scroll-into-view; no opacity-0 initial. */}
        <motion.div
          initial={{ y: 20 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, margin: "-10%" }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="mt-14 sm:mt-16 md:mt-24"
        >
          <div className="relative">
            <CornerMarks size={10} color="rgba(245, 169, 106, 0.5)" />
            <div className="terminal-panel px-5 py-6 sm:px-6 md:px-10 md:py-7">
              <div className="grid grid-cols-2 gap-y-6 sm:grid-cols-4 sm:gap-y-0 sm:divide-x sm:divide-hairline">
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
