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

// Source of truth: openclaw/skills/lyra-secretary/SKILL.md. The behavioral
// anchors are deliberate — purely numeric labels collapsed onto "3" and
// destroyed the readiness signal. Do not replace with "1=bad / 5=sharp".
const ANCHORS = [
  { value: 1, label: "Can barely focus, would rather sleep" },
  { value: 2, label: "Distracted, will struggle to start" },
  { value: 3, label: "Neutral, can work but not peak" },
  { value: 4, label: "Focused, ready to execute" },
  { value: 5, label: "Sharp, this is the best I'll feel today" },
];

interface Props {
  open: boolean;
  taskTitle: string;
  onConfirm: (rating: number) => Promise<void> | void;
  onCancel: () => void;
}

export function ReadinessModal({ open, taskTitle, onConfirm, onCancel }: Props) {
  const [value, setValue] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>How ready do you feel?</DialogTitle>
          <DialogDescription>
            About to start <span className="text-white">{taskTitle}</span>. Pick
            the line that best fits how you feel right now.
          </DialogDescription>
        </DialogHeader>
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
        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button
            disabled={value === null || submitting}
            onClick={async () => {
              if (value === null) return;
              setSubmitting(true);
              try {
                await onConfirm(value);
              } finally {
                setSubmitting(false);
              }
            }}
          >
            Start timer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
