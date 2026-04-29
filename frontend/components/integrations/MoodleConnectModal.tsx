"use client";
/**
 * Moodle LMS connect modal — paste-URL flow for the .ics subscription.
 *
 * Shipped 2026-04-29 (alembic 041) as the LMS-wedge integration.
 * Three steps:
 *   1. Instructions for grabbing the URL from Moodle's "Export calendar"
 *   2. Paste + Test (calls /preview, shows count + sample)
 *   3. Confirm Connect (calls /connect, persists URL + immediate sync)
 *
 * Trust-first copy: no research vocabulary. The flow makes the value
 * proposition concrete ("found N assignments") before asking the user
 * to commit.
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
import {
  connectMoodle,
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
};

export interface MoodleConnectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: (createdCount: number) => void;
}

export function MoodleConnectModal({
  open,
  onOpenChange,
  onConnected,
}: MoodleConnectModalProps) {
  const [step, setStep] = useState<Step>("instructions");
  const [url, setUrl] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [previewData, setPreviewData] = useState<MoodlePreviewResponse | null>(
    null
  );
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [createdCount, setCreatedCount] = useState(0);

  function reset() {
    setStep("instructions");
    setUrl("");
    setPreviewing(false);
    setConnecting(false);
    setPreviewData(null);
    setErrorCode(null);
    setCreatedCount(0);
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
      // Backend HTTPException details land here as e.message — surface
      // raw if no friendly mapping.
      setErrorCode(msg.includes("400") ? "fetch_failed" : msg);
    } finally {
      setPreviewing(false);
    }
  }

  async function handleConnect() {
    setErrorCode(null);
    setConnecting(true);
    try {
      const data = await connectMoodle(url.trim());
      setCreatedCount(data.sync.created);
      setStep("success");
      onConnected?.(data.sync.created);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorCode(msg);
    } finally {
      setConnecting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Connect Moodle</DialogTitle>
        </DialogHeader>

        {step === "instructions" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-dust">
              Lyra reads your Moodle calendar through a private URL — your
              password stays with Moodle.
            </p>
            <ol className="ml-4 list-decimal space-y-2 text-sm text-parchment">
              <li>Log in to your Moodle.</li>
              <li>Open the Calendar.</li>
              <li>
                Click <span className="font-medium">Export calendar</span> on
                the right side.
              </li>
              <li>
                Choose <span className="font-medium">Events: All</span> and{" "}
                <span className="font-medium">Time: Recent and upcoming</span>.
              </li>
              <li>
                Click <span className="font-medium">Get calendar URL</span>.
              </li>
              <li>Copy the URL it shows you and paste it here.</li>
            </ol>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button onClick={() => setStep("paste")}>I have the URL →</Button>
            </div>
          </div>
        )}

        {step === "paste" && (
          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-2 text-sm text-parchment">
              Paste your Moodle calendar URL
              <Input
                type="url"
                placeholder="https://lms.your-school.edu/calendar/export_execute.php?..."
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setErrorCode(null);
                }}
                autoFocus
              />
            </label>
            {errorCode && (
              <p className="text-xs text-ember">
                {ERROR_COPY[errorCode] ?? errorCode}
              </p>
            )}
            <p className="text-[11px] text-dust-deep">
              We&apos;ll fetch a sample first so you can see what gets
              imported before anything is saved.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setStep("instructions")}>
                ← Back
              </Button>
              <Button
                onClick={handlePreview}
                disabled={!url.trim() || previewing}
              >
                {previewing && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Test connection
              </Button>
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
                  <p className="text-[11px] uppercase tracking-wide text-dust-deep">
                    Sample
                  </p>
                  <ul className="space-y-2">
                    {previewData.sample.map((e) => (
                      <SampleRow key={e.external_id} event={e} />
                    ))}
                  </ul>
                  {previewData.count > previewData.sample.length && (
                    <p className="text-[11px] italic text-dust-deep">
                      …and {previewData.count - previewData.sample.length} more
                      not shown.
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
                  <li>Never write back to Moodle</li>
                </ul>
              </div>
            </div>
            {errorCode && (
              <p className="text-xs text-ember">
                {ERROR_COPY[errorCode] ?? errorCode}
              </p>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setStep("paste")}>
                ← Back
              </Button>
              <Button onClick={handleConnect} disabled={connecting}>
                {connecting && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Connect
              </Button>
            </div>
          </div>
        )}

        {step === "success" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-parchment">
              <span className="font-semibold text-signal">Connected.</span>{" "}
              {createdCount > 0
                ? `${createdCount} ${
                    createdCount === 1 ? "deadline" : "deadlines"
                  } imported.`
                : "Lyra found nothing to import yet — that's fine, new assignments will arrive on the next sync."}
            </p>
            <p className="text-[11px] text-dust">
              Lyra will check Moodle every 6 hours. You can disconnect anytime
              from Settings.
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
  // Naive UTC ISO → local-format display. We render in the user's locale
  // since Moodle deadlines are usually shown in their local timezone in
  // the source UI. Pass through any tz adjustment via toLocaleString.
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
          <p className="text-[10px] text-dust-deep">{event.category_hint}</p>
        )}
      </div>
      <p className="shrink-0 text-[11px] text-dust">{dueLabel}</p>
    </li>
  );
}
