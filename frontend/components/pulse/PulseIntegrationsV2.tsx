"use client";
/**
 * PulseIntegrationsV2 — compact data-source status row for /pulse v2.
 *
 * Smaller than v1 IntegrationPulse — single-line rows with monogram
 * + name + live-status dot + sync-age in mono. Designed to live in
 * the bottom row of the dashboard alongside System Insight + Recovery.
 */
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import type { IntegrationState } from "@/lib/integrations";

export interface PulseIntegrationsV2Props {
  integrations: IntegrationState[];
}

const SOURCE_META: Record<
  string,
  { label: string; monogram: string; color: "ember" | "signal" | "dust" }
> = {
  moodle: { label: "Moodle", monogram: "Mo", color: "ember" },
  google_calendar: { label: "Google Cal", monogram: "GC", color: "signal" },
  ics: { label: "ICS", monogram: "iC", color: "dust" },
};

function fmtSynced(iso: string | null | undefined): string {
  if (!iso) return "never synced";
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true });
  } catch {
    return "synced recently";
  }
}

export function PulseIntegrationsV2({ integrations }: PulseIntegrationsV2Props) {
  const ordered = [...integrations].sort((a, b) => {
    const order: Record<string, number> = {
      moodle: 0,
      google_calendar: 1,
      ics: 2,
    };
    return (order[a.id] ?? 99) - (order[b.id] ?? 99);
  });
  const visible = ordered.filter((i) => i.available);

  return (
    <div className="terminal-panel flex h-full flex-col p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          Integrations
          <span className="opacity-50"> ]</span>
        </div>
        <Link
          href="/settings"
          className="font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
        >
          Manage →
        </Link>
      </div>
      <ul className="flex flex-1 flex-col gap-1.5">
        {visible.map((it) => {
          const meta = SOURCE_META[it.id] ?? {
            label: it.id,
            monogram: "??",
            color: "dust" as const,
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
              data-testid={`pulse-integration-${it.id}`}
              className="grid grid-cols-[1.75rem_minmax(0,1fr)] items-start gap-x-3 rounded-sm border border-hairline bg-void-2/40 px-3 py-2"
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
              <div className="min-w-0 leading-tight">
                <div className="flex items-center gap-2">
                  <span
                    data-testid={`pulse-integration-${it.id}-label`}
                    className="min-w-0 break-words text-[12px] text-parchment"
                  >
                    {meta.label}
                  </span>
                  <span
                    aria-hidden
                    className="status-dot shrink-0"
                    style={{ ["--dot-color" as string]: dotColor }}
                  />
                </div>
                <div
                  data-testid={`pulse-integration-${it.id}-status`}
                  className="mt-1 break-words font-mono text-[9px] leading-4 text-dust-deep"
                >
                  {reconnect
                    ? "reconnect needed"
                    : connected
                      ? fmtSynced(it.last_synced_at)
                      : "not connected"}
                </div>
                {!connected && (
                  <Link
                    href="/settings"
                    data-testid={`pulse-integration-${it.id}-action`}
                    className="mt-1 inline-flex min-h-6 items-center font-mono text-[9px] uppercase tracking-widest text-signal/85 transition-colors hover:text-signal-neon focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal"
                  >
                    {reconnect ? "Reconnect" : "Connect"} →
                  </Link>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
