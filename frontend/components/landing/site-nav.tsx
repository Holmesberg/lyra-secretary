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
          ? "border-b border-hairline bg-void/85 backdrop-blur-xl"
          : "border-b border-transparent"
      )}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 md:px-8">
        <a
          href="#top"
          className="group flex items-center gap-2.5"
          aria-label="LyraOS — adaptive scheduling instrument"
        >
          <Image
            src="/lyraos-logo.png"
            alt=""
            width={36}
            height={36}
            priority
            className="h-8 w-8"
          />
          <span className="text-base font-medium tracking-tight text-parchment">
            LyraOS
          </span>
        </a>
        <div className="hidden items-center gap-7 md:flex">
          {LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="text-[13px] text-dust transition-colors hover:text-parchment"
            >
              {l.label}
            </a>
          ))}
        </div>
        <button
          onClick={() => signIn("google", { callbackUrl: "/today" })}
          className="hidden items-center gap-2 rounded-full bg-signal px-4 py-1.5 text-xs font-medium text-void transition-all hover:bg-[#6fe0f1] hover:-translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70 md:inline-flex"
        >
          Sign in
          <span aria-hidden>→</span>
        </button>
      </div>
    </nav>
  );
}
