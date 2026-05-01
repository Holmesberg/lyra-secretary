"use client";
/**
 * Moodle connect modal — bundled iCal + Web Services flow.
 *
 * One modal, one flow, two capabilities:
 *   - iCal subscription URL → import deadlines (alembic 041, 2026-04-29)
 *   - Web Services token    → auto-mark complete on submission (alembic 043, 2026-05-01)
 *
 * Why bundled (operator 2026-05-01 — "could u bundle both in a single
 * button?"): the standalone WS sub-row was easy to miss. One Connect
 * button on the Moodle card opens this modal; whichever sides are
 * unconnected get inputs, whichever are connected get skipped.
 *
 * Trust-first copy: no research vocabulary. Show the value
 * proposition concretely ("found N assignments"; "+ auto-mark
 * complete when you submit") before asking for credentials.
 */
import { useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import {
  connectMoodle,
  connectMoodleWS,
  previewMoodle,
  type MoodlePreviewEvent,
  type MoodlePreviewResponse,
} from "@/lib/integrations";

type Step = "instructions" | "paste" | "preview" | "success";

const ERROR_COPY: Record<string, string> = {
  url_empty: "Paste the URL in the box first.",
  url_too_long: "That URL is too long to be a Moodle calendar export.",
  url_not_http: "The URL needs to start with https://.",
  url_not_moodle_export:
    "That doesn't look like a Moodle calendar export URL. It should contain '/calendar/export_execute.php'.",
  url_missing_authtoken:
    "The URL is missing the authtoken. Make sure you copied the full subscription URL, not just the page link.",
  http_401:
    "Moodle rejected the URL — the authtoken may have expired. Get a fresh URL from Moodle and try again.",
  http_403:
    "Moodle wouldn't let us read this calendar. Check that the URL is for your own user.",
  http_404:
    "Moodle returned 'not found'. The URL might be malformed.",
  fetch_failed:
    "Couldn't reach Moodle. Check your internet connection and try again.",
  fetch_unknown: "Something unexpected went wrong fetching the URL.",
  parse_failed:
    "We reached Moodle but couldn't read the calendar format. The URL might point to the wrong page.",
  // WS errors
  ws_token_too_short:
    "That token looks too short. Moodle WS tokens are 32-character hex strings.",
  moodle_ws_base_url_missing:
    "Moodle base URL isn't configured server-side yet. Contact the operator.",
  ws_token_rejected_invalidtoken:
    "Moodle rejected that token. Generate a fresh one in Moodle → Preferences → Security keys.",
  ws_token_rejected_accessexception:
    "Moodle says your account doesn't have permission for that service. Contact your LMS admin.",
  ws_validation_failed_TimeoutError:
    "Couldn't reach Moodle in time. Try again, or check your network.",
};

function copyForError(detail: string): string {
  const composite = detail.replace(/[: ]+/g, "_");
  return ERROR_COPY[composite] ?? ERROR_COPY[detail] ?? detail;
}

export interface MoodleConnectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: (result: { ical: number | null; ws: boolean }) => void;
  /** When iCal is already connected, the URL input is hidden and we
   *  only collect a WS token. */
  existingIcalConnected?: boolean;
  /** When WS is already connected, the token input is hidden and we
   *  only collect an iCal URL. */
  existingWSConnected?: boolean;
}

export function MoodleConnectModal({
  open,
  onOpenChange,
  onConnected,
  existingIcalConnected = false,
  existingWSConnected = false,
}: MoodleConnectModalProps) {
  // If both are already connected, the modal still lets the user paste
  // a fresh URL or token (e.g., to reconnect after a token expired).
  // Default starting state: instructions, unless a side is already set
  // up — then jump straight to paste for the missing side.
  const initialStep: Step =
    existingIcalConnected && existingWSConnected ? "paste" : "instructions";

  const [step, setStep] = useState<Step>(initialStep);
  const [url, setUrl] = useState("");
  const [wsToken, setWsToken] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [previewData, setPreviewData] = useState<MoodlePreviewResponse | null>(
    null
  );
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [wsErrorCode, setWsErrorCode] = useState<string | null>(null);
  const [createdCount, setCreatedCount] = useState<number | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const showUrlInput = !existingIcalConnected;
  const showWsInput = !existingWSConnected;

  function reset() {
    setStep(initialStep);
    setUrl("");
    setWsToken("");
    setPreviewing(false);
    setConnecting(false);
    setPreviewData(null);
    setErrorCode(null);
    setWsErrorCode(null);
    setCreatedCount(null);
    setWsConnected(false);
  }

  function handleClose(nextOpen: boolean) {
    if (!nextOpen) reset();
    onOpenChange(nextOpen);
  }

  async function handlePreview() {
    setErrorCode(null);
    setPreviewing(true);
    try {
      const data = await previewMoodle(url.trim());
      if (!data.ok) {
        setErrorCode(data.error || "fetch_failed");
        setPreviewData(null);
        return;
      }
      setPreviewData(data);
      setStep("preview");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorCode(msg.includes("400") ? "fetch_failed" : msg);
    } finally {
      setPreviewing(false);
    }
  }

  // Connect both sides in sequence. iCal first because it has a
  // preview step that already confirmed the URL works; WS validation
  // happens server-side at connect time.
  async function handleConnect() {
    setErrorCode(null);
    setWsErrorCode(null);
    setConnecting(true);
    let icalCreated: number | null = null;
    let wsOk = false;
    try {
      if (showUrlInput && url.trim()) {
        const data = await connectMoodle(url.trim());
        icalCreated = data.sync.created;
      }
      if (showWsInput && wsToken.trim()) {
        try {
          await connectMoodleWS(wsToken.trim());
          wsOk = true;
        } catch (e) {
          const detail =
            e instanceof ApiError
              ? e.message
              : e instanceof Error
                ? e.message
                : "Couldn't connect.";
          setWsErrorCode(detail);
          // Fall through — iCal may still have succeeded; show success
          // with WS error inline.
        }
      }
      setCreatedCount(icalCreated);
      setWsConnected(wsOk);
      setStep("success");
      onConnected?.({ ical: icalCreated, ws: wsOk });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorCode(msg);
    } finally {
      setConnecting(false);
    }
  }

  // Connect button is disabled until at least one side has a value.
  const canConnect =
    (showUrlInput && previewData !== null) ||
    (!showUrlInput && showWsInput && wsToken.trim().length > 0);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {existingIcalConnected && !existingWSConnected
              ? "Add submission auto-detect"
              : !existingIcalConnected && existingWSConnected
                ? "Connect Moodle calendar"
                : "Connect Moodle"}
          </DialogTitle>
        </DialogHeader>

        {step === "instructions" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-dust">
              Lyra connects to Moodle in two ways — both optional. We
              never write back to Moodle, never modify your courses.
            </p>

            {showUrlInput && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-parchment">
                  1. Calendar URL <span className="text-dust">— imports your deadlines</span>
                </p>
                <ol className="ml-4 list-decimal space-y-1.5 text-xs text-dust">
                  <li>Log in to your Moodle, open the Calendar.</li>
                  <li>
                    Click <span className="font-medium text-parchment">Export calendar</span> on the right.
                  </li>
                  <li>
                    Choose <span className="font-medium text-parchment">Events: All</span>,{" "}
                    <span className="font-medium text-parchment">Time: Recent and upcoming</span>.
                  </li>
                  <li>
                    Click <span className="font-medium text-parchment">Get calendar URL</span> and copy it.
                  </li>
                </ol>
              </div>
            )}

            {showWsInput && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-parchment">
                  {showUrlInput ? "2. " : "1. "}Web Services token{" "}
                  <span className="text-dust">— auto-marks complete on submission</span>
                </p>
                <ol className="ml-4 list-decimal space-y-1.5 text-xs text-dust">
                  <li>
                    Top-right avatar → <span className="font-medium text-parchment">Preferences</span>.
                  </li>
                  <li>
                    Under <span className="font-medium text-parchment">User account</span>, click{" "}
                    <span className="font-medium text-parchment">Security keys</span>.
                  </li>
                  <li>
                    Copy the token next to{" "}
                    <span className="font-medium text-parchment">Moodle mobile web service</span>{" "}
                    (32 chars).
                  </li>
                </ol>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button onClick={() => setStep("paste")}>I have what I need →</Button>
            </div>
          </div>
        )}

        {step === "paste" && (
          <div className="flex flex-col gap-4">
            {showUrlInput && (
              <div className="flex flex-col gap-2">
                <label htmlFor="moodle-url" className="text-xs font-semibold uppercase tracking-wide text-parchment">
                  Calendar URL
                </label>
                <Input
                  id="moodle-url"
                  type="url"
                  placeholder="https://lms.your-school.edu/calendar/export_execute.php?..."
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setErrorCode(null);
                  }}
                  autoFocus
                />
                {errorCode && (
                  <p className="text-xs text-ember">
                    {ERROR_COPY[errorCode] ?? errorCode}
                  </p>
                )}
                <p className="text-[11px] text-dust">
                  We&apos;ll fetch a sample so you can see what gets imported before saving.
                </p>
              </div>
            )}

            {showWsInput && (
              <div className="flex flex-col gap-2">
                <label htmlFor="moodle-ws-token" className="text-xs font-semibold uppercase tracking-wide text-parchment">
                  Web Services token{" "}
                  {showUrlInput && <span className="font-normal normal-case tracking-normal text-dust">(optional)</span>}
                </label>
                <input
                  id="moodle-ws-token"
                  type="password"
                  value={wsToken}
                  onChange={(e) => {
                    setWsToken(e.target.value);
                    setWsErrorCode(null);
                  }}
                  placeholder="32-character hex"
                  className="w-full rounded-sm border border-hairline bg-void-2/60 px-3 py-2 font-mono text-xs text-parchment placeholder:text-dust focus:border-signal/60 focus:outline-none"
                  autoComplete="off"
                  spellCheck={false}
                />
                {wsErrorCode && (
                  <p className="text-xs text-ember">{copyForError(wsErrorCode)}</p>
                )}
                <p className="text-[11px] text-dust">
                  Lets Lyra check Moodle every 6h and auto-mark deadlines complete when you submit. Stored as-is for now (encrypted-at-rest in v2).
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setStep("instructions")}>
                ← Back
              </Button>
              {showUrlInput ? (
                <Button
                  onClick={handlePreview}
                  disabled={!url.trim() || previewing}
                >
                  {previewing && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                  Test connection
                </Button>
              ) : (
                <Button
                  onClick={handleConnect}
                  disabled={!wsToken.trim() || connecting}
                >
                  {connecting && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                  Connect
                </Button>
              )}
            </div>
          </div>
        )}

        {step === "preview" && previewData && (
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-sm text-parchment">
                Found{" "}
                <span className="font-semibold text-signal">
                  {previewData.count}
                </span>{" "}
                {previewData.count === 1 ? "item" : "items"} in your Moodle.
              </p>
              {previewData.sample.length > 0 && (
                <div className="mt-3 space-y-2">
                  <p className="text-[11px] uppercase tracking-wide text-dust">
                    Sample
                  </p>
                  <ul className="space-y-2">
                    {previewData.sample.map((e) => (
                      <SampleRow key={e.external_id} event={e} />
                    ))}
                  </ul>
                  {previewData.count > previewData.sample.length && (
                    <p className="text-[11px] italic text-dust">
                      …and {previewData.count - previewData.sample.length} more not shown.
                    </p>
                  )}
                </div>
              )}
              <div className="mt-4 rounded-sm border border-hairline bg-void-2/40 p-3 text-[11px] text-dust">
                <p className="mb-1 font-semibold text-parchment">
                  When you connect, Lyra will:
                </p>
                <ul className="ml-4 list-disc space-y-0.5">
                  <li>Add these as deadlines on /deadlines</li>
                  <li>Re-sync every 6 hours</li>
                  {showWsInput && wsToken.trim() && (
                    <li className="text-signal/90">Auto-mark complete when Moodle confirms submission</li>
                  )}
                  <li>Never write back to Moodle</li>
                </ul>
              </div>
            </div>
            {errorCode && (
              <p className="text-xs text-ember">
                {ERROR_COPY[errorCode] ?? errorCode}
              </p>
            )}
            {wsErrorCode && (
              <p className="text-xs text-ember">{copyForError(wsErrorCode)}</p>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setStep("paste")}>
                ← Back
              </Button>
              <Button onClick={handleConnect} disabled={connecting || !canConnect}>
                {connecting && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Connect
              </Button>
            </div>
          </div>
        )}

        {step === "success" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-parchment">
              <span className="font-semibold text-signal">Connected.</span>
            </p>
            <ul className="ml-4 list-disc space-y-1 text-xs text-parchment">
              {createdCount !== null && (
                <li>
                  Calendar:{" "}
                  {createdCount > 0
                    ? `${createdCount} ${createdCount === 1 ? "deadline" : "deadlines"} imported`
                    : "no new deadlines yet — next sync will catch them"}
                </li>
              )}
              {wsConnected && (
                <li>
                  Auto-mark on submission: <span className="text-signal">on</span>
                </li>
              )}
              {wsErrorCode && !wsConnected && (
                <li className="text-ember">
                  Auto-mark on submission: {copyForError(wsErrorCode)}
                </li>
              )}
            </ul>
            <p className="text-[11px] text-dust">
              Lyra checks Moodle every 6 hours. Disconnect anytime from Settings.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button onClick={() => handleClose(false)}>Done</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function SampleRow({ event }: { event: MoodlePreviewEvent }) {
  const due = new Date(event.due_at_utc + "Z");
  const dueLabel = due.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  return (
    <li className="flex items-baseline justify-between gap-2 border-b border-hairline pb-2 last:border-b-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs text-parchment">{event.title}</p>
        {event.category_hint && (
          <p className="text-[10px] text-dust">{event.category_hint}</p>
        )}
      </div>
      <p className="shrink-0 text-[11px] text-dust">{dueLabel}</p>
    </li>
  );
}
