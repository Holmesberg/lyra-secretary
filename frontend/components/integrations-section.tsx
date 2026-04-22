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
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { IntegrationCard } from "@/components/integration-card";
import {
  INTEGRATIONS,
  disconnectIntegration,
  getIntegrations,
  type IntegrationId,
  type IntegrationStatus,
} from "@/lib/integrations";

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
    "Your Google account isn't on Lyra's OAuth test-user list yet. Ask the operator to add it.",
  google_error: "Google returned an error during consent.",
  token_exchange_failed:
    "Couldn't exchange the consent code with Google. Try again.",
  no_refresh_token:
    "Google didn't return a refresh token. Disconnect anything leftover at myaccount.google.com/permissions, then try again.",
  account_mismatch:
    "The Google account you consented with doesn't match your Lyra account. Use the same account on both sides.",
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
      qc.invalidateQueries({ queryKey: ["integrations"] });
      qc.invalidateQueries({ queryKey: ["me"] });
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

  const statusQ = useQuery({
    queryKey: ["integrations"],
    queryFn: getIntegrations,
    staleTime: 30_000,
  });

  const statusById = new Map<IntegrationId, IntegrationStatus>();
  for (const row of statusQ.data?.integrations ?? []) {
    statusById.set(row.id as IntegrationId, row.status);
  }

  async function handleDisconnect(id: IntegrationId) {
    setCardErrors((e) => ({ ...e, [id]: undefined }));
    try {
      await disconnectIntegration(id);
      qc.invalidateQueries({ queryKey: ["integrations"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      // Also invalidate calendar event queries so /today and /calendar
      // drop the stale GCal events on next render — user expects
      // disconnect to have an immediate visible effect.
      qc.invalidateQueries({
        predicate: (q) =>
          typeof q.queryKey[0] === "string" &&
          (q.queryKey[0] as string).startsWith("calendar-events"),
      });
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
    <Card>
      <CardHeader>
        <CardTitle>Integrations</CardTitle>
        <p className="text-xs text-dust">
          Connect Lyra to the tools you already use. Each integration asks
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
                className="text-dust-deep transition-colors hover:text-parchment"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {INTEGRATIONS.map((def) => {
          const serverStatus = statusById.get(def.id);
          const status: IntegrationStatus = !def.available
            ? "coming_soon"
            : serverStatus ?? "disconnected";
          return (
            <IntegrationCard
              key={def.id}
              def={def}
              status={status}
              errorMessage={cardErrors[def.id] ?? null}
              onDisconnect={
                status === "connected"
                  ? () => handleDisconnect(def.id)
                  : undefined
              }
            />
          );
        })}
      </CardContent>
    </Card>
  );
}

function humanName(id: string): string {
  const def = INTEGRATIONS.find((d) => d.id === id);
  return def?.name ?? id;
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
