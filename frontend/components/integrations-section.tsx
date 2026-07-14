"use client";
/**
 * Integrations section — renders every entry in the registry plus its
 * per-user connection state. Reads URL query params to surface the
 * success/error feedback from the OAuth callback redirect.
 *
 * Placement: lives inside /settings, above Export. Integrations feel
 * "above" data-ops in information hierarchy.
 *
 * Status join: the registry (lib/integrations.ts) supplies ORDER +
 * COPY; the backend endpoint (/v1/integrations) supplies per-user
 * STATE. When a registry entry has no server match, we trust the
 * registry's `available: false` and fall through to "coming_soon".
 *
 * Moodle row (2026-05-01 redesign — operator: "I didn't notice the
 * button below moodle, could u bundle both in a single button?"):
 * one Connect button → bundled MoodleConnectModal (handles both URL
 * + WS token in one paste step). After connect, the row blooms into
 * a "Data feeds" panel showing Calendar + Submissions side-by-side
 * with their own sync states + Sync-now actions. Replaces the prior
 * sub-row + standalone WS modal.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { IntegrationCard } from "@/components/integration-card";
import { MoodleConnectModal } from "@/components/integrations/MoodleConnectModal";
import {
  disconnectMoodleWS,
  syncMoodleNow,
  syncMoodleWSNow,
} from "@/lib/integrations";
import {
  INTEGRATIONS,
  disconnectIntegration,
  getIntegrations,
  type IntegrationId,
  type IntegrationState,
  type IntegrationStatus,
} from "@/lib/integrations";
import {
  invalidateIntegrationAccountCaches,
  invalidateCalendarIntegrationCaches,
  invalidateIntegrationStatusCaches,
  invalidateMoodleConnectCaches,
  invalidateMoodleFeedSyncCaches,
  queryKeys,
} from "@/lib/query-keys";

// Copy for the callback-redirect banners. Kept here (not in the
// callback route) so translations can live next to the surface the
// user actually reads.
const ERROR_COPY: Record<string, string> = {
  missing_params: "The consent redirect didn't carry the expected parameters.",
  state_invalid: "Couldn't verify the consent request. Try again.",
  state_expired:
    "The consent request expired (10 min window). Try connecting again.",
  user_mismatch:
    "The session that started the flow isn't the one that finished it. Sign out and back in, then try again.",
  user_denied: "You declined calendar access. No harm done — try again anytime.",
  testing_mode_block:
    "Your Google account isn't on LyraOS's OAuth test-user list yet. Ask the operator to add it.",
  google_error: "Google returned an error during consent.",
  token_exchange_failed:
    "Couldn't exchange the consent code with Google. Try again.",
  no_refresh_token:
    "Google didn't return a refresh token. Disconnect anything leftover at myaccount.google.com/permissions, then try again.",
  account_mismatch:
    "The Google account you consented with doesn't match your LyraOS account. Use the same account on both sides.",
  backend_store_failed:
    "Got consent from Google but couldn't save it on the server. Try again.",
};

export function IntegrationsSection() {
  const qc = useQueryClient();
  const search = useSearchParams();
  const [banner, setBanner] = useState<{
    kind: "success" | "error";
    title: string;
    detail?: string;
  } | null>(null);
  const [cardErrors, setCardErrors] = useState<
    Partial<Record<IntegrationId, string>>
  >({});

  // Surface callback feedback from ?integration_connected / ?integration_error.
  // Clears the query params after reading so a refresh doesn't replay.
  useEffect(() => {
    const connected = search.get("integration_connected");
    const errored = search.get("integration_error");
    const reason = search.get("reason") || "";
    const detail = search.get("detail") || undefined;

    if (connected) {
      setBanner({
        kind: "success",
        title: `${humanName(connected)} connected.`,
      });
      void (connected === "google_calendar"
        ? invalidateCalendarIntegrationCaches(qc)
        : invalidateIntegrationAccountCaches(qc));
      cleanQueryParams();
    } else if (errored) {
      const text = ERROR_COPY[reason] || "Something went wrong connecting.";
      setBanner({
        kind: "error",
        title: `${humanName(errored)} not connected.`,
        detail: text + (detail ? ` (${detail})` : ""),
      });
      cleanQueryParams();
    }
    // Intentionally run once on mount — search is read from URL, not state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [moodleModalOpen, setMoodleModalOpen] = useState(false);
  const [icalSyncBusy, setIcalSyncBusy] = useState(false);
  const [wsSyncBusy, setWsSyncBusy] = useState(false);
  const [wsDisconnectBusy, setWsDisconnectBusy] = useState(false);

  const statusQ = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: getIntegrations,
    staleTime: 30_000,
  });

  const stateById = new Map<IntegrationId, IntegrationState>();
  for (const row of statusQ.data?.integrations ?? []) {
    stateById.set(row.id as IntegrationId, row);
  }

  async function handleDisconnect(id: IntegrationId) {
    setCardErrors((e) => ({ ...e, [id]: undefined }));
    try {
      await disconnectIntegration(id);
      void invalidateCalendarIntegrationCaches(qc);
      setBanner({
        kind: "success",
        title: `${humanName(id)} disconnected.`,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setCardErrors((prev) => ({ ...prev, [id]: msg }));
    }
  }

  return (
    <Card id="integrations" tabIndex={-1}>
      <CardHeader>
        <CardTitle>Integrations</CardTitle>
        <p className="text-xs text-dust">
          Connect LyraOS to the tools you already use. Each integration asks
          for its own permission when you turn it on — we don&apos;t
          request anything at sign-in.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {banner && (
          <div
            role="status"
            className={
              banner.kind === "success"
                ? "rounded-sm border border-signal/40 bg-signal/5 px-3 py-2 text-xs text-signal"
                : "rounded-sm border border-ember/40 bg-ember/5 px-3 py-2 text-xs text-ember"
            }
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">{banner.title}</p>
                {banner.detail && (
                  <p className="mt-0.5 text-[11px] opacity-80">
                    {banner.detail}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setBanner(null)}
                aria-label="Dismiss"
                className="text-dust transition-colors hover:text-parchment"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {INTEGRATIONS.map((def) => {
          const serverState = stateById.get(def.id);
          const status: IntegrationStatus = !def.available
            ? "coming_soon"
            : serverState?.status ?? "disconnected";
          const isMoodle = def.id === "moodle";
          const onConnectClick =
            isMoodle && def.authShape === "url_subscription"
              ? () => setMoodleModalOpen(true)
              : undefined;
          // For Moodle, suppress the card's built-in "Last synced X" line
          // — the Data feeds panel below presents both iCal + WS freshness
          // in one place, with bright labels and Sync-now controls.
          const lastSyncedAt = isMoodle
            ? null
            : serverState?.last_synced_at ?? null;

          return (
            <div key={def.id} className="flex flex-col gap-2">
              <IntegrationCard
                def={def}
                status={status}
                errorMessage={cardErrors[def.id] ?? null}
                onDisconnect={
                  status === "connected"
                    ? () => handleDisconnect(def.id)
                    : undefined
                }
                onConnectClick={onConnectClick}
                disconnectReason={serverState?.disconnect_reason ?? null}
                lastSyncedAt={lastSyncedAt}
              />
              {isMoodle && status === "connected" && (
                <MoodleDataFeeds
                  icalLastSyncedAt={serverState?.last_synced_at ?? null}
                  icalSyncBusy={icalSyncBusy}
                  wsConnected={!!serverState?.ws_connected}
                  wsLastSyncedAt={serverState?.ws_last_synced_at ?? null}
                  wsDisconnectReason={serverState?.ws_disconnect_reason ?? null}
                  wsSyncBusy={wsSyncBusy}
                  wsDisconnectBusy={wsDisconnectBusy}
                  onIcalSyncNow={async () => {
                    setIcalSyncBusy(true);
                    try {
                      const res = await syncMoodleNow();
                      void invalidateMoodleFeedSyncCaches(qc);
                      const created = res.created ?? 0;
                      const updated = res.updated ?? 0;
                      const parts: string[] = [];
                      if (created) parts.push(`${created} new`);
                      if (updated) parts.push(`${updated} updated`);
                      setBanner({
                        kind: "success",
                        title:
                          parts.length > 0
                            ? `Calendar synced — ${parts.join(", ")}.`
                            : `Calendar synced — nothing new.`,
                      });
                    } catch (e) {
                      setBanner({
                        kind: "error",
                        title: "Calendar sync failed",
                        detail: e instanceof Error ? e.message : String(e),
                      });
                    } finally {
                      setIcalSyncBusy(false);
                    }
                  }}
                  onWsEnable={() => setMoodleModalOpen(true)}
                  onWsSyncNow={async () => {
                    setWsSyncBusy(true);
                    try {
                      const res = await syncMoodleWSNow();
                      void invalidateMoodleFeedSyncCaches(qc);
                      const backfilled =
                        res.backfilled_completed +
                        (res.backfilled_completion_candidates ?? 0) +
                        res.backfilled_planned +
                        res.backfilled_missed;
                      const parts: string[] = [];
                      if ((res.completion_candidates ?? 0) > 0) {
                        parts.push(
                          `${res.completion_candidates ?? 0} completion evidence`
                        );
                      }
                      if (backfilled > 0) {
                        const segs: string[] = [];
                        if ((res.backfilled_completion_candidates ?? 0) > 0)
                          segs.push(`${res.backfilled_completion_candidates ?? 0} with evidence`);
                        if (res.backfilled_missed > 0)
                          segs.push(`${res.backfilled_missed} missed`);
                        if (res.backfilled_planned > 0)
                          segs.push(`${res.backfilled_planned} upcoming`);
                        parts.push(`imported ${segs.join(", ")}`);
                      }
                      setBanner({
                        kind: "success",
                        title:
                          parts.length > 0
                            ? `Submissions synced — ${parts.join(" · ")}.`
                            : `Submissions synced — nothing new.`,
                      });
                    } catch (e) {
                      setBanner({
                        kind: "error",
                        title: "Submissions sync failed",
                        detail: e instanceof Error ? e.message : String(e),
                      });
                    } finally {
                      setWsSyncBusy(false);
                    }
                  }}
                  onWsDisconnect={async () => {
                    setWsDisconnectBusy(true);
                    try {
                      await disconnectMoodleWS();
                      void invalidateIntegrationStatusCaches(qc);
                      setBanner({
                        kind: "success",
                        title: "Submission auto-detect disconnected.",
                      });
                    } catch (e) {
                      setBanner({
                        kind: "error",
                        title: "Disconnect failed",
                        detail: e instanceof Error ? e.message : String(e),
                      });
                    } finally {
                      setWsDisconnectBusy(false);
                    }
                  }}
                />
              )}
            </div>
          );
        })}

        <MoodleConnectModal
          open={moodleModalOpen}
          onOpenChange={setMoodleModalOpen}
          existingIcalConnected={
            stateById.get("moodle")?.status === "connected"
          }
          existingWSConnected={!!stateById.get("moodle")?.ws_connected}
          onConnected={(result) => {
            void invalidateMoodleConnectCaches(qc);
            const ical = result?.ical ?? null;
            const wsOn = !!result?.ws;
            const parts: string[] = [];
            if (ical !== null) {
              parts.push(
                ical > 0
                  ? `${ical} ${ical === 1 ? "deadline" : "deadlines"} imported`
                  : "no new deadlines yet"
              );
            }
            if (wsOn) parts.push("submission evidence enabled");
            setBanner({
              kind: "success",
              title: `Moodle connected.`,
              detail: parts.length ? parts.join(" · ") : undefined,
            });
          }}
        />
      </CardContent>
    </Card>
  );
}

function humanName(id: string): string {
  const def = INTEGRATIONS.find((d) => d.id === id);
  return def?.name ?? id;
}

// ---------------------------------------------------------------------------
// MoodleDataFeeds — telemetry strip rendered under the Moodle card after
// connect. Two parallel rows (Calendar / Submissions) — bright labels,
// dust freshness, signal-green Sync-now buttons. Refinement of the prior
// sub-row design that operator missed; here both feeds are co-present
// and the 6h cadence is explicit per row.
// ---------------------------------------------------------------------------

interface MoodleDataFeedsProps {
  icalLastSyncedAt: string | null;
  icalSyncBusy: boolean;
  wsConnected: boolean;
  wsLastSyncedAt: string | null;
  wsDisconnectReason: string | null;
  wsSyncBusy: boolean;
  wsDisconnectBusy: boolean;
  onIcalSyncNow: () => void;
  onWsEnable: () => void;
  onWsSyncNow: () => void;
  onWsDisconnect: () => void;
}

function MoodleDataFeeds({
  icalLastSyncedAt,
  icalSyncBusy,
  wsConnected,
  wsLastSyncedAt,
  wsDisconnectReason,
  wsSyncBusy,
  wsDisconnectBusy,
  onIcalSyncNow,
  onWsEnable,
  onWsSyncNow,
  onWsDisconnect,
}: MoodleDataFeedsProps) {
  // Indent matches IntegrationCard body (40px monogram + 16px gap = 56px).
  //
  // Aesthetic notes (operator design pass 2026-05-01, ref:
  // docs/Screenshots/ChatGPT Image Apr 29, 2026, 10_25_37 PM.png +
  // operator follow-up "aim for the middle ground"): subtle gradient
  // for slight depth, status dots as a functional pulse, but skip
  // heavy console flourishes (no bracket labels, no ring glow). Same
  // dark palette, lightly refined.
  return (
    <div
      className="
        ml-14 relative overflow-hidden rounded-sm
        border border-hairline
        bg-gradient-to-b from-void-2/50 to-void-2/30
        px-4 py-3.5
      "
    >
      <div className="mb-2.5 flex items-baseline justify-between">
        <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-dust">
          Data feeds
        </p>
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-dust">
          auto-sync · 6h
        </p>
      </div>

      <FeedRow
        label="Calendar"
        description="Imports upcoming deadlines from Moodle"
        dotState={dotStateFor(icalLastSyncedAt, false, icalSyncBusy)}
        statusLine={
          <>
            <span>synced {relativeAge(icalLastSyncedAt)}</span>
          </>
        }
        primaryAction={
          <SignalButton onClick={onIcalSyncNow} busy={icalSyncBusy}>
            Sync now
          </SignalButton>
        }
      />

      <Divider />

      {wsConnected ? (
        <FeedRow
          label="Submissions"
          description={
            wsDisconnectReason
              ? "Token rejected - reconnect to resume submission checks."
              : "Shows submission evidence from Moodle - backfills past items"
          }
          dotState={
            wsDisconnectReason
              ? "error"
              : dotStateFor(wsLastSyncedAt, false, wsSyncBusy)
          }
          statusLine={
            wsDisconnectReason ? (
              <span className="text-ember">action required</span>
            ) : (
              <span>synced {relativeAge(wsLastSyncedAt)}</span>
            )
          }
          primaryAction={
            wsDisconnectReason ? (
              <SignalButton onClick={onWsEnable}>Reconnect</SignalButton>
            ) : (
              <SignalButton onClick={onWsSyncNow} busy={wsSyncBusy}>
                Sync now
              </SignalButton>
            )
          }
          secondaryAction={
            <GhostButton
              onClick={onWsDisconnect}
              busy={wsDisconnectBusy}
              variant="warn"
            >
              Disconnect
            </GhostButton>
          }
        />
      ) : (
        <FeedRow
          label="Submissions"
          description="Show submission evidence from Moodle - imports past items LyraOS missed"
          dotState="idle"
          statusLine={<span>not enabled</span>}
          primaryAction={
            <SignalButton onClick={onWsEnable} variant="filled">
              Enable
            </SignalButton>
          }
        />
      )}
    </div>
  );
}

type DotState = "live" | "syncing" | "stale" | "idle" | "error";

function dotStateFor(
  iso: string | null,
  _connected: boolean,
  busy: boolean,
): DotState {
  if (busy) return "syncing";
  if (!iso) return "idle";
  const ageMs = Date.now() - new Date(iso).getTime();
  if (ageMs < 6 * 60 * 60 * 1000 + 30 * 60 * 1000) return "live"; // within 6.5h cadence
  return "stale";
}

function StatusDot({ state }: { state: DotState }) {
  // Tiny breathing indicator left of each feed label — gives the panel
  // a pulse that signals "this thing is alive" without adding noise.
  // Inline color tokens keep the dot consistent with feed semantics.
  const cls =
    state === "live"
      ? "bg-signal shadow-[0_0_8px_rgba(56,189,182,0.55)] animate-pulse"
      : state === "syncing"
        ? "bg-signal animate-ping"
        : state === "error"
          ? "bg-ember shadow-[0_0_8px_rgba(255,120,90,0.55)]"
          : state === "stale"
            ? "bg-dust"
            : "bg-dust/40 ring-1 ring-dust/40 ring-inset";
  return (
    <span
      aria-hidden
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${cls}`}
    />
  );
}

function FeedRow({
  label,
  description,
  statusLine,
  dotState,
  primaryAction,
  secondaryAction,
}: {
  label: string;
  description: string;
  statusLine: React.ReactNode;
  dotState: DotState;
  primaryAction: React.ReactNode;
  secondaryAction?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-4 py-2.5 first-of-type:pt-0 last-of-type:pb-0">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <StatusDot state={dotState} />
          <p className="text-xs font-semibold tracking-tight text-parchment">
            {label}
          </p>
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-dust">
          {description}
        </p>
        <p className="mt-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-dust">
          {statusLine}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 pt-0.5">
        {primaryAction}
        {secondaryAction}
      </div>
    </div>
  );
}

function Divider() {
  // Hairline separator between feed rows — fades to transparent at the
  // edges for a console-y feel.
  return (
    <div
      aria-hidden
      className="my-1.5 h-px w-full bg-gradient-to-r from-transparent via-hairline to-transparent"
    />
  );
}

function SignalButton({
  children,
  onClick,
  busy,
  variant = "outline",
}: {
  children: React.ReactNode;
  onClick: () => void;
  busy?: boolean;
  variant?: "outline" | "filled";
}) {
  const base =
    "inline-flex items-center gap-1 rounded-sm px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] transition-colors disabled:opacity-40";
  const styles =
    variant === "filled"
      ? "border border-signal/40 bg-signal/15 text-signal hover:bg-signal/25"
      : "border border-signal/40 bg-signal/5 text-signal hover:bg-signal/15";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className={`${base} ${styles}`}
    >
      {busy && <Loader2 className="h-3 w-3 animate-spin" />}
      {children}
    </button>
  );
}

function GhostButton({
  children,
  onClick,
  busy,
  variant = "default",
}: {
  children: React.ReactNode;
  onClick: () => void;
  busy?: boolean;
  variant?: "default" | "warn";
}) {
  const base =
    "inline-flex items-center gap-1 rounded-sm border border-hairline bg-transparent px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] transition-colors disabled:opacity-40";
  const styles =
    variant === "warn"
      ? "text-dust hover:border-ember/40 hover:text-ember"
      : "text-dust hover:border-parchment/40 hover:text-parchment";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className={`${base} ${styles}`}
    >
      {busy && <Loader2 className="h-3 w-3 animate-spin" />}
      {children}
    </button>
  );
}

// Relative-age formatter — "5h ago", "just now", "3d ago". Operator
// scans /settings to check freshness; relative reads faster than an
// absolute clock string.
function relativeAge(iso: string | null): string {
  if (!iso) return "never";
  const ms = Date.now() - parseApiInstant(iso).getTime();
  if (ms < 0) return "just now";
  if (ms < 60_000) return "just now";
  const m = Math.floor(ms / 60_000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function parseApiInstant(iso: string): Date {
  // Defensive compatibility for pre-fix persisted integration cache
  // entries. Moodle sync timestamps are UTC; older API responses omitted
  // the offset, which browsers interpreted as local time.
  const hasExplicitZone = /(?:Z|[+-]\d\d:\d\d)$/.test(iso);
  return new Date(hasExplicitZone ? iso : `${iso}Z`);
}

function cleanQueryParams() {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  url.searchParams.delete("integration_connected");
  url.searchParams.delete("integration_error");
  url.searchParams.delete("reason");
  url.searchParams.delete("detail");
  window.history.replaceState({}, "", url.pathname + url.search + url.hash);
}
