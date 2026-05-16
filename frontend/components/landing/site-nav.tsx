"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { GoogleSignInButton } from "./google-sign-in-button";

const LINKS = [
  { label: "Architecture", href: "#architecture" },
  { label: "Manifesto", href: "#manifesto" },
  { label: "Instrument", href: "#instrument" },
];

// === Desktop stepped-tab geometry. Do not touch on mobile — the whole
// shape is hidden below the md breakpoint; mobile gets a separate
// simple-bar treatment further down.
// TAB_H = logo render height — logo fills the tab edge-to-edge with
// zero pad so the detective silhouette reads as the brand anchor.
const TAB_W = 300;
const TAB_H = 130;
const LINE_Y = 70;
const SLOPE_W = 60;
const DROP = TAB_H - LINE_Y;
const CLIP =
  `polygon(0 0, 100% 0, 100% ${LINE_Y}px, ${TAB_W + SLOPE_W}px ${LINE_Y}px, ${TAB_W}px ${TAB_H}px, 0 ${TAB_H}px)`;

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className="fixed inset-x-0 top-0 z-30">
      {/* ───────── Desktop (md+): stepped-shape tab + slope + thin line ───────── */}
      <div
        className="relative hidden md:block"
        style={{ height: TAB_H }}
      >
        {/* Shape fill: backdrop-blurred void, clipped to stepped polygon. */}
        <div
          aria-hidden
          className={cn(
            "absolute inset-0 backdrop-blur-xl transition-colors duration-300",
            scrolled ? "bg-void/85" : "bg-void/55"
          )}
          style={{ clipPath: CLIP }}
        />

        {/* Boundary tracing: three segments along the shape's lower edge. */}
        <div
          aria-hidden
          className="absolute bottom-0 left-0 h-px bg-hairline-signal"
          style={{ width: TAB_W }}
        />
        <svg
          aria-hidden
          width={SLOPE_W}
          height={DROP}
          className="pointer-events-none absolute"
          style={{ left: TAB_W, top: LINE_Y }}
          viewBox={`0 0 ${SLOPE_W} ${DROP}`}
        >
          <line
            x1="0"
            y1={DROP}
            x2={SLOPE_W}
            y2="0"
            stroke="rgba(77, 212, 232, 0.4)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <div
          aria-hidden
          className="absolute right-0 h-px bg-hairline-signal"
          style={{ top: LINE_Y, left: TAB_W + SLOPE_W }}
        />

        {/* Tab content: logo + LyraOS wordmark */}
        <a
          href="#top"
          className="group absolute left-0 top-0 flex items-center gap-4 pl-5 lg:pl-7"
          style={{ height: TAB_H, width: TAB_W }}
          aria-label="LyraOS — the instrument"
        >
          <span className="relative flex h-[92px] w-[92px] items-center justify-center rounded-full border border-signal/45 bg-void/70 shadow-[0_0_36px_-14px_rgba(77,212,232,0.85)]">
            <span
              aria-hidden
              className="absolute inset-3 rounded-full bg-signal/10 blur-xl"
            />
            <Image
              src="/lyraos-logo.png"
              alt=""
              width={72}
              height={72}
              priority
              quality={100}
              sizes="72px"
              className="relative h-[72px] w-auto"
            />
          </span>
          <span className="font-display text-[2rem] font-medium leading-none tracking-tight text-parchment lg:text-[2.25rem]">
            LyraOS
          </span>
        </a>

        {/* Right side: nav links + Sign-in, aligned to the thin line */}
        <div
          className="absolute right-0 top-0 flex items-center gap-8 pr-6 lg:pr-10"
          style={{ height: LINE_Y }}
        >
          <div className="flex items-center gap-7">
            {LINKS.map((l) => (
              <a
                key={l.label}
                href={l.href}
                className="group relative font-mono text-[11px] uppercase tracking-widest text-dust transition-colors hover:text-parchment"
              >
                <span className="mr-1 text-signal/60 group-hover:text-signal">
                  //
                </span>
                {l.label}
              </a>
            ))}
          </div>
          <GoogleSignInButton
            className="inline-flex items-center gap-2 border border-signal/60 bg-signal/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-all hover:bg-signal hover:text-void hover:shadow-[0_0_24px_-4px_rgba(77,212,232,0.7)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
          >
            Sign in
            <span aria-hidden>→</span>
          </GoogleSignInButton>
        </div>
      </div>

      {/* ───────── Mobile (<md): simple horizontal bar, no logo ─────────
          Logo lives in the hero instead so it has its own moment.
          Right-aligned cluster — all three section anchors + Sign-in fit
          comfortably across a 375px viewport. */}
      <div
        className={cn(
          "flex items-center justify-end gap-3 border-b px-4 py-3 backdrop-blur-xl transition-colors duration-300 md:hidden",
          scrolled
            ? "border-hairline-signal bg-void/85"
            : "border-hairline-signal/60 bg-void/70"
        )}
      >
        {LINKS.map((l) => (
          <a
            key={l.label}
            href={l.href}
            className="font-mono text-[10px] uppercase tracking-widest text-dust transition-colors active:text-parchment"
          >
            {l.label}
          </a>
        ))}
        <GoogleSignInButton
          className="inline-flex items-center gap-1 border border-signal/60 bg-signal/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-signal"
        >
          Sign in
        </GoogleSignInButton>
      </div>
    </nav>
  );
}
