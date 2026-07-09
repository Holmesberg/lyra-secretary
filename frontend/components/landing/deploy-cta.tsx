"use client";

import Image from "next/image";
import { CornerMarks } from "./corner-marks";
import { GoogleSignInButton } from "./google-sign-in-button";

export function DeployCta() {
  return (
    <section
      id="deploy"
      className="relative overflow-hidden border-t border-hairline py-28 md:py-36"
    >
      {/* Atmospheric glow field */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[-20%] -z-10 h-[120%] w-[90%] -translate-x-1/2 rounded-full bg-signal/12 blur-[100px] motion-safe:animate-pulse-glow"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute right-[10%] bottom-[10%] -z-10 h-64 w-64 rounded-full bg-ember/15 blur-[80px]"
      />

      <div className="mx-auto max-w-3xl px-6 text-center md:px-10">
        <div className="mb-10 flex justify-center">
          <div className="relative">
            <div
              aria-hidden
              className="absolute -inset-6 -z-10 rounded-full bg-signal/30 blur-2xl motion-safe:animate-pulse-glow"
            />
            <Image
              src="/barzakh-logo.png"
              alt="Barzakh"
              width={120}
              height={120}
              quality={100}
              sizes="120px"
              className="h-24 w-24 motion-safe:animate-glow-flicker md:h-28 md:w-28"
            />
          </div>
        </div>

        <p className="mb-6 font-mono text-[11px] uppercase tracking-widest text-signal">
          <span className="text-signal/60">//</span> start
        </p>

        <h2 className="font-display text-[2.5rem] font-medium leading-[1.05] tracking-tight text-parchment md:text-[4rem]">
          Start building
          <br />
          <span className="neon-cyan">your execution trace</span>.
        </h2>

        <p className="mx-auto mt-7 max-w-md text-base leading-relaxed text-dust md:text-[17px]">
          Pre-alpha. Free. Google sign-in, optional integrations, and account
          export or deletion from Settings.
        </p>

        <div className="mt-12 flex justify-center">
          <div className="relative inline-block">
            <CornerMarks
              size={12}
              thickness={1.5}
              color="rgba(77, 212, 232, 0.9)"
              offset={-6}
            />
            <GoogleSignInButton
              className="cyber-pill cyber-pill-primary px-8 py-4 text-sm md:text-[0.95rem]"
            >
              <GoogleGlyph className="h-4 w-4" />
              Sign in with Google
              <span aria-hidden>→</span>
            </GoogleSignInButton>
          </div>
        </div>

        <p className="mt-8 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          :: no credit card / no waitlist / signup starts the trace
        </p>
      </div>
    </section>
  );
}

function GoogleGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}
