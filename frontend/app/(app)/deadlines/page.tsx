"use client";
import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type DeadlineResponse,
  type DeadlineState,
  listDeadlines,
  voidDeadline,
} from "@/lib/deadlines";
import { DeadlineModal } from "@/components/deadline-modal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const STATE_LABEL: Record<DeadlineState, string> = {
  planned: "Planned",
  active: "Active",
  completed: "Completed",
  missed: "Missed",
  skipped: "Skipped",
  voided: "Voided",
};

const STATE_TONE: Record<DeadlineState, string> = {
  planned: "text-dust",
  active: "text-signal",
  completed: "text-dust-deep",
  missed: "text-ember",
  skipped: "text-dust-deep",
  voided: "text-dust-deep",
};

function formatRelative(iso: string): string {
  const due = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = due - now;
  const days = Math.round(diffMs / 86_400_000);
  if (Math.abs(days) >= 1) {
    return days >= 0 ? `in ${days}d` : `${Math.abs(days)}d ago`;
  }
  const hours = Math.round(diffMs / 3_600_000);
  if (Math.abs(hours) >= 1) {
    return hours >= 0 ? `in ${hours}h` : `${Math.abs(hours)}h ago`;
  }
  return diffMs >= 0 ? "soon" : "overdue";
}

function formatAbsolute(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface DeadlineRowProps {
  deadline: DeadlineResponse;
  onEdit: () => void;
  onVoid: () => void;
}

function DeadlineRow({ deadline, onEdit, onVoid }: DeadlineRowProps) {
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="terminal-panel flex items-start gap-3 p-4">
      <div className="flex-1 space-y-1">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-sm font-medium text-parchment">
            {deadline.title}
          </span>
          <span
            className={cn(
              "font-mono text-[10px] uppercase tracking-widest",
              STATE_TONE[deadline.state]
            )}
          >
            {STATE_LABEL[deadline.state]}
          </span>
          {deadline.external_source === "moodle_ics" && (
            <span
              title="Imported from Moodle"
              className="rounded border border-ember/30 bg-ember/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ember"
            >
              Moodle
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-dust">
          <span>{formatAbsolute(deadline.due_at_utc)}</span>
          <span className="text-dust-deep">·</span>
          <span className="text-dust-deep">{formatRelative(deadline.due_at_utc)}</span>
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
        <button
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
                type="button"
                onClick={onVoid}
                className="rounded-sm bg-ember/20 px-2 py-1 text-[11px] text-ember hover:bg-ember/30"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded-sm bg-void-2 px-2 py-1 text-[11px] text-dust"
              >
                No
              </button>
            </div>
          ) : (
            <button
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
    queryKey: ["deadlines", "all"],
    queryFn: () => listDeadlines(),
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editing, setEditing] = useState<DeadlineResponse | null>(null);

  const deadlines = data?.deadlines ?? [];
  const sorted = useMemo(() => {
    return [...deadlines].sort((a, b) => {
      const ad = new Date(a.due_at_utc).getTime();
      const bd = new Date(b.due_at_utc).getTime();
      return ad - bd;
    });
  }, [deadlines]);

  // OVERDUE bucket — surfaced at the TOP, ember-toned, expanded by
  // default. Catches both the post-sweep `missed` rows AND the
  // pre-sweep `planned`/`active` rows whose due_at_utc has passed
  // (sweep_missed_deadlines runs hourly so there's a window where
  // state hasn't transitioned yet). Operator-flagged 2026-04-29:
  // overdue items must be impossible to overlook even on the
  // browsing surface — the /today banner alone isn't enough since
  // users come here to plan and triage. Sorted most-recently-overdue
  // first (closest to now at the top of the section).
  const nowMs = Date.now();
  const overdue = sorted
    .filter((d) => {
      if (d.state === "missed") return true;
      if (d.state === "planned" || d.state === "active") {
        return new Date(d.due_at_utc).getTime() < nowMs;
      }
      return false;
    })
    .sort(
      (a, b) =>
        new Date(b.due_at_utc).getTime() - new Date(a.due_at_utc).getTime()
    );
  const overdueIds = new Set(overdue.map((d) => d.deadline_id));

  // Active = planned/active but NOT yet overdue. Prevents double-render
  // (overdue planned rows would otherwise appear in both buckets).
  const active = sorted.filter(
    (d) =>
      (d.state === "planned" || d.state === "active") &&
      !overdueIds.has(d.deadline_id)
  );
  const completed = sorted
    .filter((d) => d.state === "completed")
    .sort(
      (a, b) =>
        new Date(b.completed_at ?? b.due_at_utc).getTime() -
        new Date(a.completed_at ?? a.due_at_utc).getTime()
    );
  // Skipped only — `missed` rows are now in the Overdue bucket above.
  // Keeping skipped separate because skipping is a deliberate user
  // signal (intentional abandonment), not a procrastination data point.
  const skippedOnly = sorted
    .filter((d) => d.state === "skipped")
    .sort(
      (a, b) =>
        new Date(b.due_at_utc).getTime() - new Date(a.due_at_utc).getTime()
    );

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
    qc.invalidateQueries({ queryKey: ["deadlines"] });
  }

  function handleSaved() {
    qc.invalidateQueries({ queryKey: ["deadlines"] });
  }

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Deadlines
        </h1>
        <Button onClick={openCreate}>+ New deadline</Button>
      </div>

      {isLoading && (
        <p className="text-sm text-dust">Loading deadlines…</p>
      )}

      {!isLoading && deadlines.length === 0 && (
        <p className="text-sm text-dust">
          Add a deadline to anchor your tasks. Lyra binds tasks automatically
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
        />
      )}

      {!isLoading && completed.length > 0 && (
        <Section
          title="Completed"
          deadlines={completed}
          onEdit={openEdit}
          onVoid={handleVoid}
          defaultOpen={false}
        />
      )}

      {!isLoading && skippedOnly.length > 0 && (
        <Section
          title="Skipped"
          deadlines={skippedOnly}
          onEdit={openEdit}
          onVoid={handleVoid}
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
