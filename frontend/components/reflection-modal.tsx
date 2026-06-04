"use client";

import { useState, type ReactNode } from "react";
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
  { value: 1, label: "Very poor - barely focused the whole time" },
  { value: 2, label: "Weak - distracted more than working" },
  { value: 3, label: "Average - some flow, some drift" },
  { value: 4, label: "Focused - solid deep work" },
  { value: 5, label: "Excellent - sharpest I've been all day" },
];

type ScopeOutcome = "stuck_to_plan" | "expanded" | "reduced";

const SCOPE_OPTIONS: { value: ScopeOutcome; label: string }[] = [
  { value: "stuck_to_plan", label: "Stuck to plan" },
  { value: "expanded", label: "Expanded scope" },
  { value: "reduced", label: "Reduced scope" },
];

interface Props {
  open: boolean;
  taskTitle: string;
  earlyStop?: {
    elapsed: number;
    planned: number;
    message: string;
  } | null;
  description?: ReactNode;
  contextNote?: ReactNode;
  completionRequired?: boolean;
  scopeRequired?: boolean;
  confirmLabel?: string;
  onConfirm: (
    rating: number,
    opts?: { confirmed?: boolean; completionPct?: number; scopeOutcome?: ScopeOutcome }
  ) => Promise<void> | void;
  onCancel: () => void;
}

export function ReflectionModal({
  open,
  taskTitle,
  earlyStop,
  description,
  contextNote,
  completionRequired = false,
  scopeRequired = false,
  confirmLabel,
  onConfirm,
  onCancel,
}: Props) {
  const [value, setValue] = useState<number | null>(null);
  const [pct, setPct] = useState<string>("");
  const [scope, setScope] = useState<ScopeOutcome | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const completionValid = !completionRequired || pct !== "";
  const scopeValid = !scopeRequired || scope !== null;
  const canSubmit = value !== null && completionValid && scopeValid && !submitting;

  const submit = async () => {
    if (value === null || !completionValid || !scopeValid) return;
    let clampedPct: number | undefined;
    if (pct !== "") {
      const n = Number(pct);
      clampedPct = Number.isFinite(n)
        ? Math.max(0, Math.min(100, Math.round(n)))
        : undefined;
    }
    setSubmitting(true);
    try {
      await onConfirm(value, {
        confirmed: !!earlyStop,
        completionPct: clampedPct,
        scopeOutcome: scope ?? undefined,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent
        onKeyDown={async (e) => {
          if (e.key !== "Enter") return;
          if (e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
          if ((e.target as HTMLElement).tagName === "TEXTAREA") return;
          if (!canSubmit) return;
          e.preventDefault();
          await submit();
        }}
      >
        <DialogHeader>
          <DialogTitle>How was your focus?</DialogTitle>
          <DialogDescription>
            {description ?? (
              <>
                Reflecting on <span className="text-parchment">{taskTitle}</span>.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {contextNote && (
          <div className="rounded-sm border border-signal/35 bg-signal/5 p-3 text-xs leading-relaxed text-dust">
            {contextNote}
          </div>
        )}

        {earlyStop && (
          <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
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
                "flex items-center gap-3 rounded-sm border px-3 py-2 text-left text-sm transition-colors",
                value === a.value
                  ? "border-signal/60 bg-signal/10 text-parchment"
                  : "border-hairline text-dust hover:border-signal/40 hover:text-parchment"
              )}
            >
              <span className="w-5 font-mono text-xs text-dust-deep">{a.value}</span>
              <span>{a.label}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-xs text-dust">
          <label htmlFor="pct">
            Completion % {completionRequired ? "(required)" : "(optional)"}
          </label>
          <input
            id="pct"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            placeholder="0-100"
            value={pct}
            onChange={(e) => {
              const raw = e.target.value.replace(/[^0-9]/g, "");
              if (raw === "") {
                setPct("");
                return;
              }
              const n = parseInt(raw, 10);
              setPct(String(Math.min(100, n)));
            }}
            className="h-8 w-20 rounded-sm border border-hairline-signal/30 bg-transparent px-2 text-sm text-parchment"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-dust">
            Scope {scopeRequired ? "(required)" : "(optional)"}
          </span>
          <div className="flex gap-2">
            {SCOPE_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setScope(scope === o.value ? null : o.value)}
                className={cn(
                  "rounded-sm border px-3 py-1.5 text-xs transition-colors",
                  scope === o.value
                    ? "border-signal/60 bg-signal/10 text-parchment"
                    : "border-hairline text-dust hover:border-signal/40 hover:text-parchment"
                )}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button disabled={!canSubmit} onClick={submit}>
            {confirmLabel ?? (earlyStop ? "Confirm early stop" : "Stop timer")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
