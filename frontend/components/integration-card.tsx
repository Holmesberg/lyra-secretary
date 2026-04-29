"use client";
/**
 * Single integration card. Renders one row of the Integrations panel.
 *
 * Connect button is a top-level `<a>` (not `<button>` + fetch) because
 * OAuth flows require full navigation — the browser must follow the
 * redirect chain to Google and back without losing cookies. A popup
 * flow would break on mobile and add window.open timing complexity we
 * don't need.
 *
 * Disconnect button uses a two-click confirmation — not a full modal.
 * Disconnecting GCal is reversible (user can re-Connect anytime); a
 * heavy modal would over-signal finality. Single inline confirm +
 * clear undo path in the toast suffices.
 */
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { IntegrationDef, IntegrationStatus } from "@/lib/integrations";

export interface IntegrationCardProps {
  def: IntegrationDef;
  status: IntegrationStatus;
  /** Invoked when the user confirms disconnect. Parent handles the
   *  actual API call + optimistic status flip. */
  onDisconnect?: () => Promise<void> | void;
  /** Fires on transient errors surfaced from the parent. */
  errorMessage?: string | null;
  /** For non-OAuth integrations (e.g., Moodle url_subscription), the
   *  Connect button fires this callback so the parent can open a modal.
   *  OAuth integrations use def.connectHref instead. */
  onConnectClick?: () => void;
  /** Optional disconnect-reason flag (Moodle: 'token_invalid_401' etc).
   *  Surfaces "Reconnect needed" copy on the card. */
  disconnectReason?: string | null;
  /** Optional last-synced ISO for cadence-aware integrations. */
  lastSyncedAt?: string | null;
}

export function IntegrationCard({
  def,
  status,
  onDisconnect,
  errorMessage,
  onConnectClick,
  disconnectReason,
  lastSyncedAt,
}: IntegrationCardProps) {
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [showScopes, setShowScopes] = useState(false);

  const isComingSoon = status === "coming_soon";
  const isConnected = status === "connected";
  const isDisconnected = status === "disconnected";
  const reconnectNeeded = isDisconnected && Boolean(disconnectReason);

  async function handleDisconnect() {
    if (!onDisconnect) return;
    setDisconnecting(true);
    try {
      await onDisconnect();
    } finally {
      setDisconnecting(false);
      setConfirmingDisconnect(false);
    }
  }

  return (
    <Card
      className={
        isComingSoon
          ? "opacity-70 border-dashed"
          : undefined
      }
    >
      <CardContent className="flex items-start gap-4 p-4">
        {/* Monogram chip */}
        <div
          className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-sm text-xs font-semibold tracking-tight ${def.monogramClass}`}
        >
          {def.monogram}
        </div>

        {/* Body */}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-parchment">
              {def.name}
            </h3>
            <StatusChip status={status} />
          </div>
          <p className="text-xs text-dust">{def.description}</p>
          <p className="mt-1 text-[11px] leading-relaxed text-dust-deep">
            {def.capabilityLine}
          </p>
          {def.researchNote && status === "connected" && (
            <p className="mt-1 text-[11px] text-signal/70">
              {def.researchNote}
            </p>
          )}
          {def.comingSoonNote && isComingSoon && (
            <p className="mt-1 text-[11px] italic text-dust-deep">
              {def.comingSoonNote}
            </p>
          )}
          {reconnectNeeded && (
            <p className="mt-1 text-[11px] text-ember">
              Reconnect needed — your URL stopped working. Get a fresh one and connect again.
            </p>
          )}
          {isConnected && lastSyncedAt && (
            <p className="mt-1 text-[11px] text-dust-deep">
              Last synced{" "}
              {new Date(lastSyncedAt).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </p>
          )}

          {/* Scope disclosure — collapsible to keep the card tight */}
          {def.scopes.length > 0 && !isComingSoon && (
            <button
              type="button"
              onClick={() => setShowScopes((v) => !v)}
              className="mt-2 self-start text-[11px] text-dust-deep underline-offset-2 transition-colors hover:text-parchment hover:underline"
            >
              {showScopes ? "Hide" : "View"} permissions requested
            </button>
          )}
          {showScopes && def.scopes.length > 0 && (
            <ul className="mt-1 space-y-0.5 rounded-sm border border-hairline bg-void-2/40 p-2 text-[11px] font-mono text-dust">
              {def.scopes.map((s) => (
                <li key={s} className="break-all">
                  {s}
                </li>
              ))}
            </ul>
          )}

          {errorMessage && (
            <p className="mt-2 text-[11px] text-ember">{errorMessage}</p>
          )}

          {/* Actions row */}
          <div className="mt-3 flex items-center gap-2">
            {isComingSoon && (
              <Button variant="outline" size="sm" disabled>
                Coming soon
              </Button>
            )}

            {isDisconnected && def.connectHref && (
              <a
                href={def.connectHref}
                className="inline-flex h-8 items-center justify-center rounded-sm border border-signal/40 bg-signal/10 px-3 text-xs font-medium text-signal transition-colors hover:bg-signal/20 hover:text-signal-neon"
              >
                {reconnectNeeded ? "Reconnect" : "Connect"}
              </a>
            )}

            {isDisconnected &&
              !def.connectHref &&
              def.authShape === "url_subscription" &&
              onConnectClick && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={onConnectClick}
                >
                  {reconnectNeeded ? "Reconnect" : "Connect"}
                </Button>
              )}

            {isConnected && !confirmingDisconnect && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmingDisconnect(true)}
              >
                Disconnect
              </Button>
            )}

            {isConnected && confirmingDisconnect && (
              <>
                <span className="text-[11px] text-ember">
                  Disconnect? Your stored events stop syncing.
                </span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                >
                  {disconnecting && (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  )}
                  Yes, disconnect
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmingDisconnect(false)}
                  disabled={disconnecting}
                >
                  Cancel
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusChip({ status }: { status: IntegrationStatus }) {
  if (status === "connected") {
    return (
      <span className="rounded-sm bg-signal/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-signal">
        Connected
      </span>
    );
  }
  if (status === "disconnected") {
    return (
      <span className="rounded-sm bg-dust/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-dust">
        Not connected
      </span>
    );
  }
  return (
    <span className="rounded-sm bg-void-2 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-dust-deep">
      Coming soon
    </span>
  );
}
