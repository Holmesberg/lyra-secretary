"use client";
/**
 * AppShell — sidebar-first authenticated layout (refactored 2026-04-29
 * evening, operator request after the /pulse v1 ship).
 *
 * Desktop (lg+): persistent left sidebar, ~220px wide, with the
 * brand mark + wordmark stacked top-left, an icon-prefixed nav
 * stack, and the user identity + sign-out pinned to the bottom.
 * The active route gets a 3px cyan left-edge bar — mirrors the
 * `.alert-bar-ember` pattern on the OVERDUE banner so the design
 * vocabulary is consistent.
 *
 * Mobile (<lg): preserved the existing header + hamburger pattern
 * unchanged. Sidebar would eat too much of a phone viewport.
 *
 * Background continuity: same `bg-void` shell, same hairline borders,
 * same Neural Noir restraint. The sidebar is a layout shift, not an
 * aesthetic shift.
 */
import Image from "next/image";
import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { FeedbackLink } from "@/components/feedback-link";
import { clearPersistedCache } from "@/lib/clear-persisted-cache";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  CalendarDays,
  CalendarRange,
  Flag,
  LayoutGrid,
  LogOut,
  Menu,
  Settings,
  Table2,
  TrendingUp,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Marker for experimental routes; renders a small (preview) tag. */
  preview?: boolean;
}

const NAV: NavItem[] = [
  { href: "/today", label: "Today", icon: CalendarDays },
  // Pulse is the Neural Noir dashboard. Listed second per its
  // dashboard-iness (operator's preferred-but-not-yet-promoted surface).
  { href: "/pulse", label: "Pulse", icon: Activity, preview: true },
  { href: "/calendar", label: "Calendar", icon: CalendarRange },
  { href: "/deadlines", label: "Deadlines", icon: Flag },
  { href: "/table", label: "Table", icon: Table2 },
  { href: "/insights", label: "Insights", icon: TrendingUp },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const userEmail = session?.user?.email ?? null;
  const userInitial = userEmail ? userEmail.charAt(0).toUpperCase() : "·";

  return (
    <div className="min-h-screen bg-void text-parchment lg:flex">
      {/* ─── DESKTOP SIDEBAR ─────────────────────────────────────── */}
      <aside
        className="sticky top-0 hidden h-screen w-[220px] shrink-0 flex-col border-r border-hairline-signal/30 bg-void-2/60 backdrop-blur-sm lg:flex xl:w-[240px]"
        aria-label="Primary navigation"
      >
        {/* Brand mark */}
        <Link
          href="/today"
          className="flex items-center gap-2.5 border-b border-hairline-signal/30 px-5 py-5"
          aria-label="LyraOS — Today"
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
          <div className="flex flex-col leading-none">
            <span className="text-[15px] font-semibold tracking-tight text-parchment">
              LyraOS
            </span>
            <span className="mt-1 font-mono text-[9px] uppercase tracking-widest text-signal/70">
              v1.5 · alpha
            </span>
          </div>
        </Link>

        {/* Nav stack */}
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-4">
          <div className="px-3 pb-2 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
            // Main
          </div>
          {NAV.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/today" && pathname?.startsWith(item.href + "/"));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group relative flex items-center gap-3 rounded-sm px-3 py-2 font-mono text-[12px] tracking-wide transition-colors",
                  active
                    ? "bg-signal/10 text-parchment"
                    : "text-dust hover:bg-void/40 hover:text-parchment"
                )}
                aria-current={active ? "page" : undefined}
              >
                {/* Active edge bar — mirrors .alert-bar-ember vocab */}
                {active && (
                  <span
                    aria-hidden
                    className="absolute inset-y-1.5 left-0 w-[3px] rounded-r bg-signal shadow-[0_0_10px_rgba(77,212,232,0.6)]"
                  />
                )}
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-colors",
                    active
                      ? "text-signal"
                      : "text-dust-deep group-hover:text-signal/70"
                  )}
                />
                <span className="flex-1 truncate">{item.label}</span>
                {item.preview && (
                  <span className="shrink-0 rounded-sm border border-signal/30 bg-signal/5 px-1.5 py-px text-[8px] font-medium uppercase tracking-widest text-signal/80">
                    new
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom: user identity + sign out */}
        <div className="border-t border-hairline-signal/30 px-3 py-3">
          {userEmail && (
            <div className="mb-2 flex items-center gap-2.5 rounded-sm px-2 py-2">
              <div
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-signal/40 bg-signal/10 font-mono text-[11px] font-semibold text-signal"
                aria-hidden
              >
                {userInitial}
              </div>
              <div className="min-w-0 flex-1 leading-tight">
                <div
                  className="truncate font-mono text-[10px] text-parchment"
                  title={userEmail}
                >
                  {userEmail.split("@")[0]}
                </div>
                <div className="truncate font-mono text-[9px] text-dust-deep">
                  @{userEmail.split("@")[1] ?? ""}
                </div>
              </div>
            </div>
          )}
          <div className="mb-2 px-2">
            <FeedbackLink className="!text-[10px] !uppercase !tracking-widest" />
          </div>
          <button
            type="button"
            onClick={() => {
              clearPersistedCache();
              signOut({ callbackUrl: "/" });
            }}
            className="group flex w-full items-center gap-2 rounded-sm px-2 py-2 font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:bg-ember/10 hover:text-ember"
          >
            <LogOut className="h-3.5 w-3.5 transition-colors group-hover:text-ember" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* ─── MAIN CONTENT (desktop + mobile share) ──────────────── */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile-only top header (lg:hidden) — preserved hamburger pattern */}
        <header className="border-b border-hairline-signal/40 bg-void/90 backdrop-blur-sm lg:hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <Link
              href="/today"
              className="flex items-center gap-2.5"
              aria-label="LyraOS — back to today"
            >
              <Image
                src="/lyraos-logo.png"
                alt=""
                width={32}
                height={32}
                priority
                quality={100}
                sizes="32px"
                className="h-8 w-auto"
              />
              <span className="text-base font-semibold tracking-tight text-parchment">
                LyraOS
              </span>
            </Link>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="rounded-sm p-1 text-parchment transition-colors hover:bg-signal/10 hover:text-signal"
              aria-label={
                menuOpen ? "Close navigation menu" : "Open navigation menu"
              }
              aria-expanded={menuOpen}
              aria-controls="app-mobile-nav"
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
          {menuOpen && (
            <nav
              id="app-mobile-nav"
              className="border-t border-hairline-signal/30 bg-void"
              aria-label="App navigation (mobile)"
            >
              <ul className="flex flex-col py-2">
                {NAV.map((item) => {
                  const active = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setMenuOpen(false)}
                        className={cn(
                          "group flex items-center gap-3 px-5 py-3 font-mono text-xs uppercase tracking-widest transition-colors",
                          active
                            ? "bg-signal/10 text-parchment"
                            : "text-dust hover:bg-signal/5 hover:text-parchment"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-4 w-4 shrink-0 transition-colors",
                            active
                              ? "text-signal"
                              : "text-dust-deep group-hover:text-signal/70"
                          )}
                        />
                        <span className="flex-1">{item.label}</span>
                        {item.preview && (
                          <span className="rounded-sm border border-signal/30 bg-signal/5 px-1.5 py-px text-[8px] uppercase tracking-widest text-signal/80">
                            new
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
                <li className="mt-1 border-t border-hairline-signal/20 px-5 py-2">
                  <div className="flex flex-col gap-0.5 leading-tight">
                    <span className="font-mono text-[10px] tracking-wider text-dust-deep">
                      {userEmail}
                    </span>
                    <FeedbackLink />
                  </div>
                </li>
                <li className="border-t border-hairline-signal/20 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      signOut({ callbackUrl: "/" });
                    }}
                    className="w-full px-5 py-3 text-left font-mono text-xs uppercase tracking-widest text-dust-deep transition-colors hover:bg-ember/5 hover:text-ember"
                  >
                    Sign out
                  </button>
                </li>
              </ul>
            </nav>
          )}
        </header>

        {/* Page content — wider on desktop now that the sidebar
            replaces the top tab strip. Keeping max-w-7xl for breathing
            room on ultrawide displays. */}
        <main className="mx-auto w-full max-w-[1400px] px-5 py-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
