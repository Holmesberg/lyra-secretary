"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type DeadlineResponse,
  listDeadlines,
  updateDeadline,
  voidDeadline,
} from "@/lib/deadlines";
import {
  DEADLINE_STATE_LABEL,
  DEADLINE_STATE_TONE,
  formatDeadlineAbsolute,
  formatDeadlineRelative,
  groupDeadlineSections,
  isDeadlineMarkDoneAllowed,
  isMoodleDeadline,
} from "@/lib/deadline-view";
import { DeadlineModal } from "@/components/deadline-modal";
import { Button } from "@/components/ui/button";
import {
  invalidateDeadlineMutationCaches,
  queryKeys,
} from "@/lib/query-keys";
import { cn } from "@/lib/utils";

interface DeadlineRowProps {
  deadline: DeadlineResponse;
  onEdit: () => void;
  onVoid: () => void;
  /** Fires after a successful inline state change (mark-done). Owner
   *  refetches /v1/deadlines so the row updates. (2026-05-01) */
  onChanged?: () => void;
}

function DeadlineRow({ deadline, onEdit, onVoid, onChanged }: DeadlineRowProps) {
  const [confirming, setConfirming] = useState(false);
  const [marking, setMarking] = useState(false);
  const canMarkDone = isDeadlineMarkDoneAllowed(deadline);

  async function handleMarkDone() {
    if (marking) return;
    setMarking(true);
    try {
      await updateDeadline(deadline.deadline_id, { state: "completed" });
      onChanged?.();
    } catch {
      setMarking(false);
    }
  }
  return (
    <div
      data-testid="deadline-row"
      data-deadline-id={deadline.deadline_id}
      data-deadline-title={deadline.title}
      data-deadline-state={deadline.state}
      className="terminal-panel flex items-start gap-3 p-4"
    >
      <div className="flex-1 space-y-1">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-sm font-medium text-parchment">
            {deadline.title}
          </span>
          <span
            className={cn(
              "font-mono text-[10px] uppercase tracking-widest",
              DEADLINE_STATE_TONE[deadline.state]
            )}
          >
            {DEADLINE_STATE_LABEL[deadline.state]}
          </span>
          {isMoodleDeadline(deadline) && (
            <span
              title="Imported from Moodle"
              className="rounded border border-ember/30 bg-ember/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ember"
            >
              Moodle
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-dust">
          <span>{formatDeadlineAbsolute(deadline.due_at_utc)}</span>
          <span className="text-dust-deep">·</span>
          <span className="text-dust-deep">{formatDeadlineRelative(deadline.due_at_utc)}</span>
          {deadline.category_hint && (
            <>
              <span className="text-dust-deep">·</span>
              <span className="text-dust-deep">{deadline.category_hint}</span>
            </>
          )}
        </div>
        {deadline.description && (
          <p className="pt-1 text-xs text-dust">{deadline.description}</p>
        )}
      </div>
      <div className="flex shrink-0 flex-col gap-1">
        {/* One-click mark-done — operator pain point 2026-05-01 with
            Moodle-imported overdue items they completed out-of-
            band but LyraOS had no way to know about (iCal carries due
            dates, NOT submission status). Surfaced on planned/active
            plus missed deadlines, because missed only means the sweeper
            passed the due time; it does not prove the user failed to
            complete the real-world obligation. */}
        {canMarkDone && (
          <button
            data-testid="deadline-row-done"
            type="button"
            onClick={handleMarkDone}
            disabled={marking}
            title="Mark this deadline as completed"
            className="rounded-sm border border-signal/40 bg-signal/10 px-2 py-1 text-[11px] text-signal transition-colors hover:bg-signal/20 disabled:opacity-40"
          >
            {marking ? "Saving…" : "✓ Done"}
          </button>
        )}
        <button
          data-testid="deadline-row-edit"
          type="button"
          onClick={onEdit}
          className="rounded-sm border border-hairline bg-void-2 px-2 py-1 text-[11px] text-dust transition-colors hover:border-signal/40 hover:text-parchment"
        >
          Edit
        </button>
        {deadline.state !== "voided" &&
          (confirming ? (
            <div className="flex gap-1">
              <button
                data-testid="deadline-row-void-confirm"
                type="button"
                onClick={onVoid}
                className="rounded-sm bg-ember/20 px-2 py-1 text-[11px] text-ember hover:bg-ember/30"
              >
                Confirm
              </button>
              <button
                data-testid="deadline-row-void-cancel"
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded-sm bg-void-2 px-2 py-1 text-[11px] text-dust"
              >
                No
              </button>
            </div>
          ) : (
            <button
              data-testid="deadline-row-void"
              type="button"
              onClick={() => setConfirming(true)}
              className="rounded-sm border border-hairline bg-void-2 px-2 py-1 text-[11px] text-dust-deep transition-colors hover:border-ember/40 hover:text-ember"
            >
              Void
            </button>
          ))}
      </div>
    </div>
  );
}

interface SectionProps {
  title: string;
  deadlines: DeadlineResponse[];
  onEdit: (d: DeadlineResponse) => void;
  onVoid: (d: DeadlineResponse) => void;
  /** Fires after an inline mark-done from DeadlineRow (2026-05-01).
   *  Page-level owner re-fetches /v1/deadlines so the row updates. */
  onChanged?: () => void;
  defaultOpen?: boolean;
  /** 'ember' colors the section header red for high-attention groupings
   *  (Overdue). Default 'dust' is the calm neutral treatment. */
  tone?: "dust" | "ember";
}

function Section({
  title,
  deadlines,
  onEdit,
  onVoid,
  onChanged,
  defaultOpen = true,
  tone = "dust",
}: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  if (deadlines.length === 0) return null;
  const isEmber = tone === "ember";
  const headerCls = isEmber
    ? "text-ember hover:text-ember/80"
    : "text-dust hover:text-parchment";
  const countCls = isEmber ? "text-ember/70" : "text-dust-deep";
  // Ember (Overdue) gets the cyber-display treatment to match the /today
  // banner and the per-row pill — bracketed readout in Chakra Petch.
  // Dust (default) keeps the existing terminal-prefix style.
  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-2 text-left text-[11px] font-semibold uppercase ${
          isEmber
            ? `font-display tracking-macro ${headerCls}`
            : `tracking-widest ${headerCls}`
        }`}
      >
        {isEmber ? (
          <span className="inline-flex items-center gap-2">
            <span
              aria-hidden
              className="status-dot"
              style={{ ["--dot-color" as string]: "#FF8A3D" }}
            />
            <span>
              <span className="opacity-50">[ </span>
              {title}
              <span className="opacity-50"> ]</span>
            </span>
          </span>
        ) : (
          <span className="terminal-prefix">{title}</span>
        )}
        <span className={countCls}>({deadlines.length})</span>
        <span className={countCls}>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="space-y-2">
          {deadlines.map((d) => (
            <DeadlineRow
              key={d.deadline_id}
              deadline={d}
              onEdit={() => onEdit(d)}
              onVoid={() => onVoid(d)}
              onChanged={onChanged}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DeadlinesPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.deadlinesAll,
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editing, setEditing] = useState<DeadlineResponse | null>(null);

  const deadlines = data?.deadlines ?? [];
  const { overdue, active, completed, skippedOnly } =
    groupDeadlineSections(deadlines);

  function openCreate() {
    setEditing(null);
    setModalMode("create");
    setModalOpen(true);
  }

  function openEdit(d: DeadlineResponse) {
    setEditing(d);
    setModalMode("edit");
    setModalOpen(true);
  }

  async function handleVoid(d: DeadlineResponse) {
    await voidDeadline(d.deadline_id);
    await invalidateDeadlineMutationCaches(qc);
  }

  function handleSaved() {
    void invalidateDeadlineMutationCaches(qc);
  }

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Deadlines
        </h1>
        <Button data-testid="deadlines-new" onClick={openCreate}>
          + New deadline
        </Button>
      </div>

      {isLoading && (
        <p className="text-sm text-dust">Loading deadlines…</p>
      )}

      {!isLoading && deadlines.length === 0 && (
        <p className="text-sm text-dust">
          Add a deadline to anchor your tasks. LyraOS binds tasks automatically
          when titles match — or you can pick one explicitly when creating a
          task.
        </p>
      )}

      {!isLoading && overdue.length > 0 && (
        <div className="terminal-panel-ember alert-bar-ember rounded-sm p-4">
          <Section
            title="Overdue"
            deadlines={overdue}
            onEdit={openEdit}
            onVoid={handleVoid}
            onChanged={handleSaved}
            tone="ember"
          />
        </div>
      )}

      {!isLoading && active.length > 0 && (
        <Section
          title="Active deadlines"
          deadlines={active}
          onEdit={openEdit}
          onVoid={handleVoid}
          onChanged={handleSaved}
        />
      )}

      {!isLoading && completed.length > 0 && (
        <Section
          title="Completed"
          deadlines={completed}
          onEdit={openEdit}
          onVoid={handleVoid}
          onChanged={handleSaved}
          defaultOpen={false}
        />
      )}

      {!isLoading && skippedOnly.length > 0 && (
        <Section
          title="Skipped"
          deadlines={skippedOnly}
          onEdit={openEdit}
          onVoid={handleVoid}
          onChanged={handleSaved}
          defaultOpen={false}
        />
      )}

      <DeadlineModal
        open={modalOpen}
        mode={modalMode}
        deadline={editing}
        onClose={() => setModalOpen(false)}
        onSaved={handleSaved}
      />
    </div>
  );
}
