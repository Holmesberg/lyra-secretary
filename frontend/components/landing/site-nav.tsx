"use client";

import Image from "next/image";
import { signIn } from "next-auth/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const LINKS = [
  { label: "Manifesto", href: "#manifesto" },
  { label: "Instrument", href: "#instrument" },
  { label: "Live demo", href: "#live-data" },
];

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={cn(
        "fixed inset-x-0 top-0 z-30 transition-all duration-300",
        scrolled
          ? "border-b border-hairline-signal bg-void/85 backdrop-blur-xl"
          : "border-b border-transparent"
      )}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 md:px-10">
        <a
          href="#top"
          className="group flex items-center gap-3"
          aria-label="LyraOS — the instrument"
        >
          <div className="relative h-[72px] w-[72px] overflow-hidden">
            <div
              aria-hidden
              className="absolute inset-0 -z-10 rounded-full bg-signal/30 blur-lg"
            />
            <Image
              src="/lyraos-logo.png"
              alt=""
              width={72}
              height={72}
              priority
              className="h-[72px] w-[72px] object-contain"
            />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-display text-sm font-medium tracking-wider text-parchment">
              LyraOS
            </span>
            <span className="mt-0.5 font-mono text-[9px] uppercase tracking-widest text-signal/80">
              cognitive os
            </span>
          </div>
        </a>

        <div className="hidden items-center gap-8 md:flex">
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

        <button
          onClick={() => signIn("google", { callbackUrl: "/today" })}
          className="hidden items-center gap-2 border border-signal/60 bg-signal/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-all hover:bg-signal hover:text-void hover:shadow-[0_0_24px_-4px_rgba(77,212,232,0.7)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70 md:inline-flex"
        >
          Sign in
          <span aria-hidden>→</span>
        </button>
      </div>
    </nav>
  );
}
