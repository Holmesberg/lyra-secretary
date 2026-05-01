"use client";
/**
 * MoodleWSConnectModal — paste a Moodle Web Services token to enable
 * automatic submission detection.
 *
 * Why a separate modal from MoodleConnectModal:
 *   - iCal subscription (URL) and Web Services (token) are orthogonal
 *     capabilities — user may want one without the other
 *   - Pasting a token is one step, not a multi-step wizard
 *
 * Operator-flow: from the Moodle integration card on /settings, click
 * "Auto-detect submitted" → this modal opens → paste token → backend
 * validates against core_webservice_get_site_info → save → close.
 *
 * Backend: POST /v1/integrations/moodle/ws-connect (validates +
 * persists). Errors surface inline with the standard error map.
 *
 * Phase B 2026-05-01 — operator: "I wanted the submitted status to
 * be automatically caught, I feel like we keep asking the user for
 * too much input."
 */
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { ApiError } from "@/lib/api";
import { connectMoodleWS } from "@/lib/integrations";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const ERROR_COPY: Record<string, string> = {
  ws_token_too_short:
    "That token looks too short. Moodle WS tokens are 32-character hex strings.",
  moodle_ws_base_url_missing:
    "Moodle base URL isn't configured server-side yet. Operator: set MOODLE_WS_BASE_URL env.",
  ws_token_rejected_invalidtoken:
    "Moodle rejected that token. Generate a fresh one from Moodle → Preferences → Security keys.",
  ws_token_rejected_accessexception:
    "Moodle says your account doesn't have permission for that service. Contact your LMS admin.",
  ws_validation_failed_TimeoutError:
    "Couldn't reach Moodle in time. Try again, or check your network.",
};

function copyForError(detail: string): string {
  // Detail may be "ws_token_rejected: invalidtoken" — try the
  // composite key first, then fall back to the bare prefix.
  const composite = detail.replace(/[: ]+/g, "_");
  return ERROR_COPY[composite] ?? ERROR_COPY[detail] ?? detail;
}

export interface MoodleWSConnectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: () => void;
}

export function MoodleWSConnectModal({
  open,
  onOpenChange,
  onConnected,
}: MoodleWSConnectModalProps) {
  const [token, setToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  // Reset state when modal closes — don't leak token across opens.
  useEffect(() => {
    if (!open) {
      setToken("");
      setSubmitting(false);
      setErrorDetail(null);
    }
  }, [open]);

  async function handleSubmit() {
    if (submitting || !token.trim()) return;
    setSubmitting(true);
    setErrorDetail(null);
    try {
      await connectMoodleWS(token.trim());
      onConnected?.();
      onOpenChange(false);
    } catch (e) {
      const detail =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Couldn't connect.";
      setErrorDetail(detail);
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Auto-detect submitted assignments</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <p className="text-xs text-dust">
            Lyra will automatically mark deadlines complete when Moodle
            confirms you submitted the assignment. Runs every 6 hours
            alongside the calendar sync — no extra action needed after
            you submit in Moodle.
          </p>
          <div className="rounded-sm border border-hairline bg-void-2/40 p-3 text-[11px] text-dust">
            <p className="mb-1.5 font-semibold text-parchment">
              How to get your token:
            </p>
            <ol className="ml-4 list-decimal space-y-0.5">
              <li>Open Moodle and log in</li>
              <li>Top-right avatar → <span className="text-parchment">Preferences</span></li>
              <li>
                Under <span className="text-parchment">User account</span>,
                click <span className="text-parchment">Security keys</span>
              </li>
              <li>
                Copy the token next to{" "}
                <span className="text-parchment">
                  Moodle mobile web service
                </span>{" "}
                (32 chars)
              </li>
            </ol>
          </div>
          <div>
            <label
              htmlFor="ws-token"
              className="mb-1 block text-[11px] uppercase tracking-wide text-dust-deep"
            >
              Web Services token
            </label>
            <input
              id="ws-token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="32-character hex"
              className="w-full rounded-sm border border-hairline bg-void-2/60 px-3 py-2 font-mono text-xs text-parchment placeholder:text-dust-deep focus:border-signal/60 focus:outline-none"
              autoComplete="off"
              spellCheck={false}
            />
            <p className="mt-1 text-[10px] text-dust-deep">
              Stored encrypted-at-rest in v2; plaintext today (same as the
              calendar URL). Never shared outside Lyra.
            </p>
          </div>
          {errorDetail && (
            <p className="text-xs text-ember">{copyForError(errorDetail)}</p>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting || !token.trim()}>
              {submitting && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              Connect
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
