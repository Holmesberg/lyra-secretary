"use client";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

const VOID_REASONS = [
  { value: "test_contamination", label: "Test contamination" },
  { value: "duplicate", label: "Duplicate session" },
  { value: "system_error", label: "System error / corrupted data" },
  { value: "data_quality", label: "Data quality issue" },
  { value: "other", label: "Other (specify)" },
] as const;

interface Props {
  open: boolean;
  taskCount: number;
  onConfirm: (reason: string, detail?: string) => Promise<void> | void;
  onCancel: () => void;
}

export function VoidModal({ open, taskCount, onConfirm, onCancel }: Props) {
  const [reason, setReason] = useState("");
  const [detail, setDetail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsDetail = reason === "other";
  const canSubmit = reason && (!needsDetail || detail.trim());

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent
        onKeyDown={async (e) => {
          if (e.key !== "Enter") return;
          if (e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
          if ((e.target as HTMLElement).tagName === "TEXTAREA") return;
          if (!canSubmit || submitting) return;
          e.preventDefault();
          setSubmitting(true);
          setError(null);
          try {
            await onConfirm(reason, needsDetail ? detail.trim() : undefined);
          } catch (err: any) {
            setError(err?.message ?? "Void failed");
          } finally {
            setSubmitting(false);
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>
            Void {taskCount} session{taskCount > 1 ? "s" : ""}?
          </DialogTitle>
          <DialogDescription>
            Voiding excludes these sessions from your analytics but preserves
            them in history. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="void-reason">Reason</Label>
            <select
              id="void-reason"
              value={reason}
              onChange={(e) => { setReason(e.target.value); setError(null); }}
              className="h-9 rounded-md border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment"
            >
              <option value="" className="bg-void">Select a reason…</option>
              {VOID_REASONS.map((r) => (
                <option key={r.value} value={r.value} className="bg-void">
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {needsDetail && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="void-detail">Details (required)</Label>
              <input
                id="void-detail"
                type="text"
                value={detail}
                onChange={(e) => setDetail(e.target.value)}
                placeholder="Why are these sessions being voided?"
                className="h-9 rounded-md border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment"
              />
            </div>
          )}

          {error && (
            <div className="rounded-sm border border-ember/40 bg-ember/5 p-2 text-xs text-ember">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!canSubmit || submitting}
            onClick={async () => {
              setSubmitting(true);
              setError(null);
              try {
                await onConfirm(reason, needsDetail ? detail.trim() : undefined);
              } catch (e: any) {
                setError(e?.message ?? "Void failed");
              } finally {
                setSubmitting(false);
              }
            }}
          >
            Confirm void
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
