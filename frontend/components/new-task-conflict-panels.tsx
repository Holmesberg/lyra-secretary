"use client";

import type {
  PausedConflict,
  SoftConflict,
} from "@/components/use-new-task-submit-controller";

interface PausedConflictPanelProps {
  conflict: PausedConflict;
  pendingTitle: string;
}

export function NewTaskPausedConflictPanel({
  conflict,
  pendingTitle,
}: PausedConflictPanelProps) {
  return (
    <>
      <div className="rounded-md border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
        <span className="font-medium text-parchment">{conflict.title}</span>{" "}
        is paused in this window.{" "}
        {conflict.blockingTitles.length === 0 ? (
          <>
            Start{" "}
            <span className="font-medium text-parchment">{pendingTitle}</span>{" "}
            as an interruption? It will be linked — you can resume{" "}
            <span className="font-medium text-parchment">{conflict.title}</span>{" "}
            after.
          </>
        ) : (
          <>
            To interrupt it, adjust the time to avoid the blocking conflict
            {conflict.blockingTitles.length > 1 ? "s" : ""} below.
          </>
        )}
      </div>
      {conflict.blockingTitles.length > 0 && (
        <div className="rounded border border-ember/40 bg-ember/5 p-2 text-xs text-ember">
          Also conflicts with: {conflict.blockingTitles.join(", ")}
        </div>
      )}
    </>
  );
}

export function NewTaskSoftConflictPanel({
  conflict,
}: {
  conflict: SoftConflict;
}) {
  return (
    <div className="rounded-md border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
      {conflict.executingTitles.length > 0 && (
        <div>
          Timer running on{" "}
          <span className="font-medium text-parchment">
            {conflict.executingTitles.join(", ")}
          </span>
          .
        </div>
      )}
      {conflict.overlapTitles.length > 0 && (
        <div>
          Overlaps with{" "}
          <span className="font-medium text-parchment">
            {conflict.overlapTitles.join(", ")}
          </span>
          .
        </div>
      )}
      {conflict.reasons.includes("duplicate_title") &&
        conflict.duplicateTitle && (
          <div>
            Already have{" "}
            <span className="font-medium text-parchment">
              {conflict.duplicateTitle}
            </span>{" "}
            today.
          </div>
        )}
      <div className="mt-1 text-dust">Create as planned anyway?</div>
    </div>
  );
}
