"use client";
/**
 * Feedback widget modal (alembic 040, 2026-04-28).
 *
 * Drop-in: renders nothing when `open` is false. When open, shows a
 * small modal with kind radios + body textarea + optional context
 * checkbox + Send button. On submit:
 *   1. POST /v1/feedback (records row + fans email/Telegram)
 *   2. Flash "Thanks, Ali will see this" for 1100ms
 *   3. onClose
 *
 * Fail-soft: any error surfaces inline; the modal stays open so the
 * user can copy their text + retry.
 */
import { useEffect, useState } from "react";
import { Send, Check, X } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { submitFeedback, readRecentErrors, type FeedbackKind } from "@/lib/feedback";

interface Props {
  open: boolean;
  onClose: () => void;
}

const KIND_OPTIONS: Array<{ value: FeedbackKind; label: string; hint: string }> = [
  { value: "bug",        label: "Found a bug",  hint: "Something broke or behaved unexpectedly" },
  { value: "suggestion", label: "Suggestion",   hint: "Idea for improving Barzakh" },
  { value: "confused",   label: "Confused",     hint: "Something didn't make sense" },
  { value: "other",      label: "Other",        hint: "" },
];

export function FeedbackModal({ open, onClose }: Props) {
  const [kind, setKind] = useState<FeedbackKind>("bug");
  const [body, setBody] = useState("");
  const [includeContext, setIncludeContext] = useState(true);
  const [busy, setBusy] = useState(false);
  const [resolved, setResolved] = useState<"sent" | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reset on open so a previous unsent draft doesn't linger.
  useEffect(() => {
    if (open) {
      setKind("bug");
      setBody("");
      setIncludeContext(true);
      setBusy(false);
      setResolved(null);
      setError(null);
    }
  }, [open]);

  // Auto-close after the success flash.
  useEffect(() => {
    if (resolved !== "sent") return;
    const t = setTimeout(() => {
      setResolved(null);
      onClose();
    }, 1100);
    return () => clearTimeout(t);
  }, [resolved, onClose]);

  async function handleSend() {
    if (busy) return;
    if (body.trim().length === 0) {
      setError("Please write a quick note before sending.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await submitFeedback({
        kind,
        body: body.trim(),
        pageUrl: includeContext && typeof window !== "undefined"
          ? window.location.href : undefined,
        userAgent: includeContext && typeof navigator !== "undefined"
          ? navigator.userAgent : undefined,
        errorContext: includeContext ? readRecentErrors() : undefined,
      });
      setResolved("sent");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Send failed. Try again?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Help improve Barzakh</DialogTitle>
          <DialogDescription className="text-dust">
            Whatever you write goes straight to Ali. Bugs, suggestions, anything weird.
          </DialogDescription>
        </DialogHeader>

        {resolved === "sent" ? (
          <div className="flex items-center gap-2 rounded-sm border border-signal/40 bg-signal/5 px-3 py-3 text-sm text-signal">
            <Check className="h-4 w-4" />
            <span>Thanks — Ali will see this.</span>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              {KIND_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setKind(opt.value)}
                  className={
                    "flex items-center gap-2 rounded-sm border px-2.5 py-1.5 text-left text-xs transition-colors " +
                    (kind === opt.value
                      ? "border-signal/60 bg-signal/10 text-parchment"
                      : "border-hairline bg-void-2/40 text-dust hover:bg-void-2/70 hover:text-parchment")
                  }
                  disabled={busy}
                >
                  <span className="text-base leading-none">
                    {kind === opt.value ? "●" : "○"}
                  </span>
                  <span className="flex-1">
                    <span className="font-medium">{opt.label}</span>
                    {opt.hint && (
                      <span className="ml-1 text-[10px] text-dust-deep">— {opt.hint}</span>
                    )}
                  </span>
                </button>
              ))}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="fb-body">Tell us what happened</Label>
              <textarea
                id="fb-body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="What went wrong, what would help, or what's confusing…"
                rows={4}
                disabled={busy}
                className="rounded-sm border border-hairline-signal/30 bg-transparent px-3 py-2 text-sm text-parchment placeholder:text-dust-deep resize-none focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-dust">
              <input
                type="checkbox"
                checked={includeContext}
                onChange={(e) => setIncludeContext(e.target.checked)}
                disabled={busy}
                className="h-3.5 w-3.5 cursor-pointer accent-[#4dd4e8]"
              />
              <span>Include current page + recent errors (helps Ali reproduce)</span>
            </label>

            {error && (
              <div className="rounded-sm border border-ember/40 bg-ember/5 px-2.5 py-1.5 text-xs text-ember">
                {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClose}
                disabled={busy}
              >
                <X className="h-3.5 w-3.5 mr-1" /> Cancel
              </Button>
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={handleSend}
                disabled={busy || body.trim().length === 0}
              >
                <Send className="h-3.5 w-3.5 mr-1" />
                {busy ? "Sending…" : "Send"}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
