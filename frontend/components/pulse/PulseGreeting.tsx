"use client";
/**
 * PulseGreeting — top bar greeting + status pills.
 *
 * Reference-image vocabulary: "Good evening, X." + a row of compact
 * pill readouts (focus minutes today, wins, overdue) + an action
 * button strip on the right (search/notifications/avatar). For v1 we
 * surface the focus minutes + wins + overdue pills since those are
 * the highest-signal at-a-glance numbers; the right-side icon strip
 * is intentionally restrained to avoid the SaaS-cliché icon parade.
 */
import { Search } from "lucide-react";
import { format } from "date-fns";

export interface PulseGreetingProps {
  displayName: string | null;
  focusMinutesToday: number | null;
  winsToday: number | null;
  overdueCount: number | null;
  onSearchClick?: () => void;
}

function greetingFor(hour: number): string {
  if (hour < 5) return "Up late";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  if (hour < 22) return "Good evening";
  return "Up late";
}

function fmtFocus(minutes: number | null): string {
  if (minutes === null) return "--";
  if (minutes <= 0) return "0m";
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function PulseGreeting({
  displayName,
  focusMinutesToday,
  winsToday,
  overdueCount,
  onSearchClick,
}: PulseGreetingProps) {
  const now = new Date();
  const hourGreeting = greetingFor(now.getHours());
  const dateLabel = format(now, "EEEE, MMMM d");

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-col gap-1">
        <div className="font-mono text-[10px] uppercase tracking-widest text-signal/70">
          {">>"} <span className="text-signal">PULSE</span>{" "}
          <span className="text-dust-deep">// {dateLabel}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-parchment lg:text-[28px]">
          {hourGreeting}
          {displayName ? `, ${displayName}` : ""}
          <span className="text-signal">.</span>
        </h1>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill
          testId="pulse-focus-today-metric"
          label="Focus today"
          value={fmtFocus(focusMinutesToday)}
          tone={focusMinutesToday !== null && focusMinutesToday > 0 ? "signal" : "dust"}
        />
        <StatusPill
          testId="pulse-wins-metric"
          label="Wins"
          value={winsToday === null ? "--" : winsToday.toString().padStart(2, "0")}
          tone={winsToday !== null && winsToday > 0 ? "signal" : "dust"}
        />
        <StatusPill
          testId="pulse-overdue-metric"
          label="Overdue"
          value={overdueCount === null ? "--" : overdueCount.toString().padStart(2, "0")}
          tone={overdueCount !== null && overdueCount > 0 ? "ember" : "dust"}
        />
        {onSearchClick && (
          <button
            type="button"
            onClick={onSearchClick}
            aria-label="Search"
            className="ml-1 rounded-sm border border-hairline bg-void-2/40 p-2 text-dust-deep transition-colors hover:border-signal/40 hover:text-signal"
          >
            <Search className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

function StatusPill({
  testId,
  label,
  value,
  tone,
}: {
  testId: string;
  label: string;
  value: string;
  tone: "signal" | "ember" | "dust";
}) {
  const valueCls =
    tone === "ember"
      ? "neon-ember"
      : tone === "signal"
        ? "text-signal"
        : "text-dust-deep";
  const borderCls =
    tone === "ember"
      ? "border-ember/40"
      : tone === "signal"
        ? "border-signal/30"
        : "border-hairline";
  const bgCls =
    tone === "ember"
      ? "bg-ember/5"
      : tone === "signal"
        ? "bg-signal/5"
        : "bg-void-2/40";
  return (
    <div
      data-testid={testId}
      className={`flex items-center gap-2 rounded-sm border px-3 py-1.5 ${borderCls} ${bgCls}`}
    >
      <span
        className={`font-display text-sm font-semibold tabular-nums leading-none ${valueCls}`}
      >
        {value}
      </span>
      <span className="font-display text-[9px] uppercase tracking-macro text-dust">
        {label}
      </span>
    </div>
  );
}
