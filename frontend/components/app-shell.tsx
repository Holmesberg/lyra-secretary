"use client";
import Image from "next/image";
import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
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
 * md+ gets the horizontal tab strip (Phase 2). Below md, the tab
 * strip collapses behind a hamburger toggle (Phase 4) — the
 * previous overflow-x-auto stripe required horizontal scrubbing on
 * small viewports, which failed mobile tap targets.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // Auto-close the mobile menu on any route change — clicking a link
  // navigates and closes the panel in one gesture. Also covers
  // programmatic nav (e.g., deep-link open).
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

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
            {/* App wordmark uses Geist Sans (already bundled) rather than
               the landing's Chakra Petch; the display font is reserved
               for marketing surfaces so authenticated routes don't pull
               down the 5-weight Chakra WOFF2 family on first paint. */}
            <span className="text-lg font-semibold tracking-tight text-parchment">
              LyraOS
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden font-mono text-[10px] tracking-wider text-dust-deep sm:inline">
              {session?.user?.email}
            </span>
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="hidden font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-signal md:inline"
            >
              Sign out
            </button>
            {/* Mobile hamburger toggle — md:hidden so it disappears at the
               same breakpoint where the horizontal tab strip appears.
               aria-expanded tracks panel state for SR users; aria-controls
               points at the #app-mobile-nav panel below. */}
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="rounded-sm p-1 text-parchment transition-colors hover:bg-signal/10 hover:text-signal md:hidden"
              aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={menuOpen}
              aria-controls="app-mobile-nav"
            >
              {menuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
        {/* Desktop horizontal tab strip — unchanged from Phase 2; just
           gated to md+. overflow-x-auto kept as a safety net for the
           medium-width range (768-900px) where long labels + five tabs
           still need a tiny bit of scroll room before the hamburger
           takes over. */}
        <nav
          className="mx-auto hidden max-w-6xl gap-1 overflow-x-auto px-6 md:flex"
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
        {/* Mobile dropdown panel — slides open below the header when the
           hamburger is tapped. Uses the same // terminal-prefix pattern
           as the desktop strip so the brand vocabulary stays consistent
           across viewports. */}
        {menuOpen && (
          <nav
            id="app-mobile-nav"
            className="border-t border-hairline-signal/30 bg-void md:hidden"
            aria-label="App navigation (mobile)"
          >
            <ul className="flex flex-col py-2">
              {NAV.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => setMenuOpen(false)}
                      className={cn(
                        "group flex items-center gap-1 px-6 py-3 font-mono text-xs uppercase tracking-widest transition-colors",
                        active
                          ? "bg-signal/10 text-parchment"
                          : "text-dust hover:bg-signal/5 hover:text-parchment"
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
                  </li>
                );
              })}
              {/* Mobile sign-out sits at the bottom of the panel since the
                 header row hides the desktop "Sign out" button on mobile
                 (gained horizontal space for the hamburger). */}
              <li className="mt-1 border-t border-hairline-signal/20 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    signOut({ callbackUrl: "/" });
                  }}
                  className="w-full px-6 py-3 text-left font-mono text-xs uppercase tracking-widest text-dust-deep transition-colors hover:bg-ember/5 hover:text-ember"
                >
                  Sign out
                </button>
              </li>
            </ul>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
