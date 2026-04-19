"use client";
import Image from "next/image";
import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/today", label: "Today" },
  { href: "/calendar", label: "Calendar" },
  { href: "/table", label: "Table" },
  { href: "/insights", label: "Insights" },
  { href: "/settings", label: "Settings" },
];

/**
 * Authenticated app shell — brand-unified with the landing (logo,
 * palette, wordmark, terminal-prefix links, cyan active state) but
 * deliberately calm: no atmospheric decorations (stars, circuits,
 * scan-lines, glow halos) that would fight the operational density
 * of /today, /calendar, /table, /insights, /settings.
 *
 * The operator should recognize the brand at a glance while still
 * being able to read task rows at speed.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-void text-parchment">
      <header className="border-b border-hairline-signal/40 bg-void/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link
            href="/today"
            className="flex items-center gap-2.5"
            aria-label="LyraOS — back to today"
          >
            <Image
              src="/lyraos-logo.png"
              alt=""
              width={36}
              height={36}
              priority
              quality={100}
              sizes="36px"
              className="h-9 w-auto"
            />
            <span className="font-display text-lg font-medium tracking-tight text-parchment">
              LyraOS
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden font-mono text-[10px] tracking-wider text-dust-deep sm:inline">
              {session?.user?.email}
            </span>
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-signal"
            >
              Sign out
            </button>
          </div>
        </div>
        <nav
          className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-6"
          aria-label="App navigation"
        >
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group relative whitespace-nowrap border-b-2 px-3 py-2.5 font-mono text-[11px] uppercase tracking-widest transition-colors",
                  active
                    ? "border-signal text-parchment"
                    : "border-transparent text-dust hover:text-parchment"
                )}
              >
                <span
                  className={cn(
                    "mr-1 transition-colors",
                    active
                      ? "text-signal"
                      : "text-signal/50 group-hover:text-signal"
                  )}
                >
                  //
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
