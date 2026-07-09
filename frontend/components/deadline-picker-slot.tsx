"use client";

import { useQuery } from "@tanstack/react-query";

import {
  listDeadlines,
  sortDeadlinesActiveFirst,
  type DeadlinePreviewResponse,
} from "@/lib/deadlines";
import { queryKeys } from "@/lib/query-keys";

interface DeadlinePickerSlotProps {
  deadlineId: string | null;
  suggestion: DeadlinePreviewResponse | null;
  showPicker: boolean;
  onConfirmSuggestion: () => void;
  onDismissSuggestion: () => void;
  onClearBinding: () => void;
  onTogglePicker: () => void;
  onPick: (deadlineId: string) => void;
}

export function DeadlinePickerSlot({
  deadlineId,
  suggestion,
  showPicker,
  onConfirmSuggestion,
  onDismissSuggestion,
  onClearBinding,
  onTogglePicker,
  onPick,
}: DeadlinePickerSlotProps) {
  // Bindable deadlines = state in {planned, active}, voided_at IS NULL.
  // Backend's list endpoint already filters voided by default; we filter
  // state client-side because the list endpoint accepts only one state
  // at a time and we want both planned and active.
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.deadlinesBindable,
    queryFn: () => listDeadlines(),
    enabled: showPicker,
  });
  const bindable = sortDeadlinesActiveFirst(
    (data?.deadlines ?? []).filter(
      (d) => d.state === "planned" || d.state === "active",
    ),
  );

  const boundDeadline = bindable.find((d) => d.deadline_id === deadlineId);

  if (deadlineId) {
    return (
      <div className="rounded-sm border border-signal/40 bg-signal/5 p-3 text-xs text-signal">
        <div className="flex items-center justify-between gap-2">
          <span>
            Bound to{" "}
            <span className="font-medium text-parchment">
              {boundDeadline?.title ?? "deadline"}
            </span>
          </span>
          <button
            type="button"
            onClick={onClearBinding}
            className="rounded-sm bg-void-2 px-2 py-1 text-[11px] text-dust hover:text-parchment"
          >
            Clear
          </button>
        </div>
      </div>
    );
  }

  if (suggestion?.deadline_id && !showPicker) {
    const conf = suggestion.deadline_match_confidence ?? 0;
    return (
      <div
        data-testid="new-task-deadline-suggestion"
        className="rounded-sm border border-hairline-signal/40 bg-void-2/40 p-3 text-xs text-dust"
      >
        <div>
          LyraOS thinks this binds to{" "}
          <span className="font-medium text-parchment">
            {suggestion.deadline_title}
          </span>
          {" "}— {Math.round(conf * 100)}% match
        </div>
        <div className="mt-2 flex gap-2">
          <button
            data-testid="new-task-deadline-confirm-suggestion"
            type="button"
            onClick={onConfirmSuggestion}
            className="rounded-sm bg-signal/20 px-2 py-1 text-[11px] font-medium text-parchment transition-colors hover:bg-signal/30"
          >
            Confirm
          </button>
          <button
            data-testid="new-task-deadline-pick-another"
            type="button"
            onClick={onTogglePicker}
            className="rounded-sm bg-void-2 px-2 py-1 text-[11px] text-dust transition-colors hover:bg-void hover:text-parchment"
          >
            Pick another
          </button>
          <button
            data-testid="new-task-deadline-no-deadline"
            type="button"
            onClick={onDismissSuggestion}
            className="rounded-sm bg-void-2 px-2 py-1 text-[11px] text-dust-deep transition-colors hover:text-dust"
          >
            No deadline
          </button>
        </div>
      </div>
    );
  }

  if (showPicker) {
    return (
      <div className="rounded-sm border border-hairline bg-void-2/40 p-3 text-xs text-dust">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
            Pick a deadline
          </span>
          <button
            type="button"
            onClick={onTogglePicker}
            className="text-[11px] text-dust-deep hover:text-dust"
          >
            Cancel
          </button>
        </div>
        {isLoading ? (
          <div className="text-[11px] text-dust-deep">Loading…</div>
        ) : bindable.length === 0 ? (
          <div className="text-[11px] text-dust-deep">
            No active deadlines. Create one from /deadlines first.
          </div>
        ) : (
          <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
            {bindable.map((d) => (
              <button
                data-testid="new-task-deadline-option"
                data-deadline-id={d.deadline_id}
                data-deadline-title={d.title}
                key={d.deadline_id}
                type="button"
                onClick={() => onPick(d.deadline_id)}
                className="flex items-center justify-between gap-2 rounded-sm border border-hairline bg-void-2 px-2 py-1 text-left text-[11px] text-dust transition-colors hover:border-signal/40 hover:text-parchment"
              >
                <span className="truncate">{d.title}</span>
                <span className="shrink-0 text-dust-deep">
                  {new Date(d.due_at_utc).toLocaleDateString()}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={onTogglePicker}
      className="self-start rounded-sm text-[11px] text-dust-deep transition-colors hover:text-dust"
    >
      + Bind to a deadline
    </button>
  );
}
