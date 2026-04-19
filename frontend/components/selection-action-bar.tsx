"use client";
import { Button } from "@/components/ui/button";

interface Props {
  count: number;
  onVoid: () => void;
  onCancel: () => void;
}

export function SelectionActionBar({ count, onVoid, onCancel }: Props) {
  if (count === 0) return null;

  return (
    <div className="mb-3 flex items-center justify-between rounded-sm border border-signal/30 bg-signal/5 px-4 py-2">
      <span className="font-mono text-xs uppercase tracking-widest text-signal">
        {count} selected
      </span>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="destructive" size="sm" onClick={onVoid}>
          Void selected
        </Button>
      </div>
    </div>
  );
}
