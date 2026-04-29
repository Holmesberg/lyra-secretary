"use client";
/**
 * IntegrationPulse — compact "data sources" status card for /pulse.
 *
 * Surfaces which integrations are alive + when each last synced. The
 * Moodle row gets the most data because it's the wedge — a stale or
 * disconnected feed is the user's #1 reason imported deadlines stop
 * appearing. Reads the existing `IntegrationsResponse` shape extended
 * with `last_synced_at` / `disconnect_reason` (alembic 041 fields).
 */
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import type { IntegrationState } from "@/lib/integrations";

export interface IntegrationPulseProps {
  integrations: IntegrationState[];
}

const SOURCE_META: Record<
  string,
  { label: string; monogram: string; color: string }
> = {
  moodle: { label: "Moodle", monogram: "Mo", color: "ember" },
  google_calendar: { label: "Google Calendar", monogram: "GC", color: "signal" },
  notion: { label: "Notion", monogram: "N", color: "dust" },
  ics: { label: "ICS", monogram: "iC", color: "dust" },
};

function fmtSynced(iso: string | null | undefined): string {
  if (!iso) return "never synced";
  try {
    return `synced ${formatDistanceToNow(new Date(iso), { addSuffix: true })}`;
  } catch {
    return "synced recently";
  }
}

export function IntegrationPulse({ integrations }: IntegrationPulseProps) {
  // Always show Moodle + Google first (in that order) — the wedge +
  // the existing live integration. Other sources only appear if
  // available && status !== coming_soon.
  const ordered = [...integrations].sort((a, b) => {
    const order: Record<string, number> = {
      moodle: 0,
      google_calendar: 1,
      notion: 2,
      ics: 3,
    };
    return (order[a.id] ?? 99) - (order[b.id] ?? 99);
  });
  const visible = ordered.filter((i) => i.available);

  return (
    <div className="terminal-panel p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="font-display text-[11px] font-medium uppercase tracking-macro text-dust">
          <span className="text-signal/70">{">>"}</span>{" "}
          <span className="ml-1">Data sources</span>
        </div>
        <Link
          href="/settings"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep hover:text-signal"
        >
          Manage →
        </Link>
      </div>
      <ul className="flex flex-col gap-2">
        {visible.map((it) => {
          const meta = SOURCE_META[it.id] ?? {
            label: it.id,
            monogram: "??",
            color: "dust",
          };
          const connected = it.status === "connected";
          const reconnect = !!it.disconnect_reason;
          const dotColor = reconnect
            ? "#FF8A3D"
            : connected
              ? meta.color === "ember"
                ? "#F5A96A"
                : "#4DD4E8"
              : "#4A5168";
          return (
            <li
              key={it.id}
              className="flex items-center gap-3 rounded-sm border border-hairline bg-void-2/40 px-3 py-2"
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-sm font-mono text-[10px] font-semibold ${
                  meta.color === "ember"
                    ? "border border-ember/30 bg-ember/10 text-ember"
                    : meta.color === "signal"
                      ? "border border-signal/30 bg-signal/10 text-signal"
                      : "border border-hairline bg-void-2 text-dust"
                }`}
              >
                {meta.monogram}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-xs text-parchment">{meta.label}</span>
                  <span
                    aria-hidden
                    className="status-dot"
                    style={{ ["--dot-color" as string]: dotColor }}
                  />
                </div>
                <div className="font-mono text-[10px] text-dust-deep">
                  {reconnect
                    ? "reconnect needed"
                    : connected
                      ? fmtSynced(it.last_synced_at)
                      : "not connected"}
                </div>
              </div>
              {!connected && (
                <Link
                  href="/settings"
                  className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-signal/80 hover:text-signal-neon"
                >
                  Connect →
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
