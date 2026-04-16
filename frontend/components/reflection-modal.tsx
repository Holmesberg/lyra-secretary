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
import { cn } from "@/lib/utils";

const ANCHORS = [
  { value: 1, label: "Very poor — barely focused the whole time" },
  { value: 2, label: "Weak — distracted more than working" },
  { value: 3, label: "Average — some flow, some drift" },
  { value: 4, label: "Focused — solid deep work" },
  { value: 5, label: "Excellent — sharpest I've been all day" },
];

interface Props {
  open: boolean;
  taskTitle: string;
  earlyStop?: {
    elapsed: number;
    planned: number;
    message: string;
  } | null;
  onConfirm: (
    rating: number,
    opts?: { confirmed?: boolean; completionPct?: number }
  ) => Promise<void> | void;
  onCancel: () => void;
}

export function ReflectionModal({
  open,
  taskTitle,
  earlyStop,
  onConfirm,
  onCancel,
}: Props) {
  const [value, setValue] = useState<number | null>(null);
  const [pct, setPct] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>How was your focus?</DialogTitle>
          <DialogDescription>
            Reflecting on <span className="text-white">{taskTitle}</span>.
          </DialogDescription>
        </DialogHeader>

        {earlyStop && (
          <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs text-yellow-200">
            Early stop: only {earlyStop.elapsed} of {earlyStop.planned} planned
            minutes. Confirming will close the session as-is.
          </div>
        )}

        <div className="flex flex-col gap-2">
          {ANCHORS.map((a) => (
            <button
              key={a.value}
              onClick={() => setValue(a.value)}
              className={cn(
                "flex items-center gap-3 rounded-md border px-3 py-2 text-left text-sm transition-colors",
                value === a.value
                  ? "border-white bg-white/10 text-white"
                  : "border-white/10 text-white/70 hover:border-white/30 hover:text-white"
              )}
            >
              <span className="w-5 font-mono text-xs text-white/50">{a.value}</span>
              <span>{a.label}</span>
            </button>
          ))}
        </div>

        {/* LYR-098 sibling (Apr 16 ungate): completion % input is shown on
            EVERY stop now, not just early-stop confirmations. Was gated on
            earlyStop && for the pre-4.5 flow; the ungate lets the research
            layer capture task_completion_percentage across normal/overrun
            stops too (currently null on 77% of EXECUTED tasks per Apr 16
            data audit). Input stays optional — user can leave blank. */}
        <div className="flex items-center gap-2 text-xs text-white/60">
          <label htmlFor="pct">Completion % (optional)</label>
          <input
            id="pct"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            placeholder="0–100"
            value={pct}
            onChange={(e) => {
              const raw = e.target.value.replace(/[^0-9]/g, "");
              if (raw === "") { setPct(""); return; }
              const n = parseInt(raw, 10);
              setPct(String(Math.min(100, n)));
            }}
            className="h-8 w-20 rounded-md border border-white/15 bg-transparent px-2 text-sm"
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button
            disabled={value === null || submitting}
            onClick={async () => {
              if (value === null) return;
              // Clamp completion % to [0,100]. HTML min/max only constrains
              // the spinner, not pasted/typed values — the backend enforces
              // ge/le at the Pydantic layer but we reject early so the user
              // sees the clamp instead of a 422.
              let clampedPct: number | undefined;
              if (pct !== "") {
                const n = Number(pct);
                if (!Number.isFinite(n)) {
                  clampedPct = undefined;
                } else {
                  clampedPct = Math.max(0, Math.min(100, Math.round(n)));
                }
              }
              setSubmitting(true);
              try {
                await onConfirm(value, {
                  confirmed: !!earlyStop,
                  completionPct: clampedPct,
                });
              } finally {
                setSubmitting(false);
              }
            }}
          >
            {earlyStop ? "Confirm early stop" : "Stop timer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
