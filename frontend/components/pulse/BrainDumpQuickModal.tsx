"use client";
/**
 * BrainDumpQuickModal — modal-shaped brain-dump composer for /pulse.
 *
 * Operator request 2026-04-29 night: clicking Capture on /pulse should
 * open the brain-dump modal so the capture path stays inside Pulse.
 * Reuses the existing parse + commit API helpers
 * (lib/brain-dump.ts) so the heuristic + binding tiers behave
 * identically to the onboarding fullscreen flow — same parser, same
 * tier1_auto / tier2_ask logic, just packaged as a Dialog.
 *
 * Two-step inner flow:
 *   1. dump   — textarea, "Parse" button. Empty submit shows error.
 *   2. confirm — preview parsed items + binding pills, "Lock in"
 *                commits + closes the modal + invalidates queries so
 *                the rest of the dashboard reflects the new state.
 *
 * On commit success, fires onCompleted() — caller is responsible for
 * invalidating ['tasks', today] / ['deadlines'] / ['me']. We invalidate
 * inside the modal too as a belt-and-braces measure.
 */
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  parseBrainDump,
  commitBrainDump,
  type BrainDumpBindingSuggestion,
  type BrainDumpFailedItem,
  type BrainDumpParsedItem,
} from "@/lib/brain-dump";
import {
  bindingKey,
  buildBrainDumpCommitBindings,
  buildBrainDumpCommitItems,
  chooseBrainDumpBinding,
  failureCopy,
  initialBindingChoices,
  localIsoNow,
  pad2,
  type BrainDumpBindingChoice,
} from "@/lib/brain-dump-ui";
import { invalidateBrainDumpCommitCaches } from "@/lib/query-keys";

type Step = "dump" | "confirm" | "review_failures";

/** Pulse-specific retry hints; shared failure wording lives in brain-dump-ui. */
function retryCopy(hint: string | null): string {
  switch (hint) {
    case "schedule_tomorrow_same_time":
      return "Try scheduling tomorrow at the same time.";
    case "edit_when_local":
      return "Edit the time here, or adjust it later from the calendar.";
    case "remove_deadline_binding":
      return "Unbind from the deadline and retry.";
    case "use_existing_deadline":
      return "No duplicate deadline was created.";
    default:
      return "";
  }
}

function newCommitKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `brain-dump-${crypto.randomUUID()}`;
  }
  return `brain-dump-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function toDateTimeInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso.slice(0, 16);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(
    date.getDate()
  )}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

function moveLocalInputByDays(value: string | null, days: number): string | null {
  const base = value ? new Date(value) : new Date();
  if (Number.isNaN(base.getTime())) return value;
  base.setDate(base.getDate() + days);
  return `${base.getFullYear()}-${pad2(base.getMonth() + 1)}-${pad2(
    base.getDate()
  )}T${pad2(base.getHours())}:${pad2(base.getMinutes())}:${pad2(
    base.getSeconds()
  )}`;
}

function fmtWhen(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function bindingTargetLabel(b: BrainDumpBindingSuggestion): string {
  return b.target_kind === "existing_deadline"
    ? "existing obligation"
    : "same dump";
}

export interface BrainDumpQuickModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-populate the textarea with this text (e.g. text from the
   *  inline Quick Capture footer). Empty string = blank. */
  seedText?: string;
  /** Optional callback fired after a successful commit. Useful for
   *  showing a banner / toast on the parent surface. */
  onCompleted?: (counts: {
    tasks: number;
    deadlines: number;
    bindings: number;
  }) => void;
}

export function BrainDumpQuickModal({
  open,
  onOpenChange,
  seedText = "",
  onCompleted,
}: BrainDumpQuickModalProps) {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>("dump");
  // LYR-114 fix 2026-04-30: failures from /commit surface here so the
  // user sees what didn't land instead of the modal silently closing
  // with a partial commit.
  const [failures, setFailures] = useState<BrainDumpFailedItem[]>([]);
  const [committedSummary, setCommittedSummary] = useState<{
    tasks: number;
    deadlines: number;
    bindings: number;
  } | null>(null);
  const [rawText, setRawText] = useState(seedText);
  const [items, setItems] = useState<BrainDumpParsedItem[]>([]);
  const [bindings, setBindings] = useState<BrainDumpBindingSuggestion[]>([]);
  const [bindingChoices, setBindingChoices] = useState<
    Record<string, BrainDumpBindingChoice>
  >({});
  const [parsing, setParsing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const commitKeyRef = useRef<string | null>(null);
  const commitInFlightRef = useRef(false);

  // Sync the textarea + step when the modal opens / seed changes.
  useEffect(() => {
    if (open) {
      setStep("dump");
      setRawText(seedText);
      setItems([]);
      setBindings([]);
      setBindingChoices({});
      setFailures([]);
      setCommittedSummary(null);
      setError(null);
      commitKeyRef.current = null;
      commitInFlightRef.current = false;
      // Focus the textarea on next tick so the autofocus lands after
      // the dialog's mount animation.
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [open, seedText]);

  async function handleParse() {
    if (parsing) return;
    setError(null);
    if (!rawText.trim()) {
      setError("Type something first — at least one task or deadline.");
      return;
    }
    setParsing(true);
    try {
      const res = await parseBrainDump(rawText, localIsoNow());
      setItems(res.items);
      setBindings(res.bindings);
      setFailures([]);
      setCommittedSummary(null);
      commitKeyRef.current = newCommitKey();
      // Tier 1 auto-bindings start pre-checked yes.
      setBindingChoices(initialBindingChoices(res.bindings));
      if (res.items.length === 0) {
        setError(
          "Couldn't pull anything out. Try one item per line — 'submit assignment Friday', 'read chapter 3 tomorrow'."
        );
        setParsing(false);
        return;
      }
      setStep("confirm");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Parse failed. Try again.");
    } finally {
      setParsing(false);
    }
  }

  async function handleCommit() {
    if (committing || commitInFlightRef.current) return;
    commitInFlightRef.current = true;
    setError(null);
    setCommitting(true);
    try {
      const commitItems = buildBrainDumpCommitItems(items);
      const commitBindings = buildBrainDumpCommitBindings(
        bindings,
        bindingChoices,
      );
      if (!commitKeyRef.current) {
        commitKeyRef.current = newCommitKey();
      }
      const res = await commitBrainDump(
        commitItems,
        commitBindings,
        commitKeyRef.current,
      );
      // Invalidate every cache key the dashboard depends on so the
      // moment the modal closes (or the review_failures step lands)
      // the new rows are visible behind the modal.
      void invalidateBrainDumpCommitCaches(qc);
      onCompleted?.({
        tasks: res.tasks_created,
        deadlines: res.deadlines_created,
        bindings: res.bindings_applied,
      });
      // LYR-114 fix: pause close on failures so the user actually
      // sees what didn't land. If everything committed cleanly,
      // close as before.
      if (res.failed_items && res.failed_items.length > 0) {
        setFailures(res.failed_items);
        setCommittedSummary({
          tasks: res.tasks_created,
          deadlines: res.deadlines_created,
          bindings: res.bindings_applied,
        });
        setStep("review_failures");
        commitInFlightRef.current = false;
        setCommitting(false);
        return;
      }
      onOpenChange(false);
    } catch (e: unknown) {
      commitInFlightRef.current = false;
      setError(e instanceof Error ? e.message : "Couldn't save. Try again.");
      setCommitting(false);
    }
  }

  function setBindingChoice(
    binding: BrainDumpBindingSuggestion,
    choice: "yes" | "no",
  ) {
    setBindingChoices((s) =>
      chooseBrainDumpBinding(s, bindings, binding, choice),
    );
  }

  function updateItem(
    itemId: string,
    patch: Partial<Pick<BrainDumpParsedItem, "title" | "when_local" | "duration_minutes">>,
  ) {
    setItems((current) =>
      current.map((item) =>
        item.item_id === itemId ? { ...item, ...patch } : item,
      ),
    );
    commitKeyRef.current = newCommitKey();
  }

  function removeItem(itemId: string) {
    const nextBindings = bindings.filter(
      (binding) =>
        binding.task_item_id !== itemId && binding.deadline_item_id !== itemId,
    );
    setItems((current) => current.filter((item) => item.item_id !== itemId));
    setBindings(nextBindings);
    setBindingChoices(initialBindingChoices(nextBindings));
    commitKeyRef.current = newCommitKey();
  }

  function retryFailedItems(options?: { movePastToTomorrow?: boolean }) {
    const failedIds = new Set(failures.map((failure) => failure.item_id));
    const failedById = new Map(
      failures.map((failure) => [failure.item_id, failure]),
    );
    const nextItems = items
      .filter((item) => failedIds.has(item.item_id))
      .map((item) => {
        const failure = failedById.get(item.item_id);
        if (
          options?.movePastToTomorrow &&
          failure?.retry_hint === "schedule_tomorrow_same_time"
        ) {
          return {
            ...item,
            when_local: moveLocalInputByDays(item.when_local, 1),
          };
        }
        return item;
      });
    const nextBindings = bindings.filter(
      (binding) =>
        failedIds.has(binding.task_item_id) ||
        (binding.deadline_item_id !== null &&
          failedIds.has(binding.deadline_item_id)),
    );

    setItems(nextItems);
    setBindings(nextBindings);
    setBindingChoices(initialBindingChoices(nextBindings));
    setFailures([]);
    setCommittedSummary(null);
    setError(null);
    commitKeyRef.current = newCommitKey();
    setStep("confirm");
  }

  const tasksParsed = items.filter((i) => i.kind === "task");
  const deadlinesParsed = items.filter((i) => i.kind === "deadline");
  const bindingsForTask: Record<string, BrainDumpBindingSuggestion[]> = {};
  for (const b of bindings) {
    (bindingsForTask[b.task_item_id] ||= []).push(b);
  }
  const tier2Unanswered = bindings.some(
    (b) => b.tier === "tier2_ask" && !bindingChoices[bindingKey(b)]
  );
  const canMoveFailedToTomorrow = failures.some(
    (failure) => failure.retry_hint === "schedule_tomorrow_same_time",
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl" data-testid="brain-dump-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-signal" />
            <span>Brain dump</span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              {step === "dump" ? "// step 1 of 2" : "// step 2 of 2 · confirm"}
            </span>
          </DialogTitle>
        </DialogHeader>

        {step === "dump" && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-dust">
              Type whatever's in your head — one item per line works best.
              Barzakh parses titles, dates, and durations. Examples: "submit
              lab 8 friday 11pm", "read chapter 3 tomorrow 30min".
            </p>
            <textarea
              data-testid="brain-dump-textarea"
              ref={textareaRef}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={8}
              placeholder="midterm friday 11pm
study chapter 3 tomorrow 30min
gym sat morning"
              className="w-full resize-y rounded-sm border border-hairline bg-void/60 px-3 py-2 font-mono text-sm text-parchment placeholder:text-dust-deep focus:border-signal/60 focus:outline-none focus:ring-0"
            />
            {error && (
              <p className="text-[11px] text-ember">{error}</p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button
                data-testid="brain-dump-cancel"
                type="button"
                onClick={() => onOpenChange(false)}
                className="rounded-sm border border-hairline bg-void-2/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-dust hover:border-signal/40 hover:text-parchment"
              >
                Cancel
              </button>
              <button
                data-testid="brain-dump-parse"
                type="button"
                onClick={handleParse}
                disabled={parsing}
                className="inline-flex items-center gap-1.5 rounded-sm border border-signal/40 bg-signal/15 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
              >
                {parsing && <Loader2 className="h-3 w-3 animate-spin" />}
                Parse
              </button>
            </div>
          </div>
        )}

        {step === "confirm" && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-dust">
              Barzakh found{" "}
              <span className="font-display text-signal">
                {tasksParsed.length}
              </span>{" "}
              {tasksParsed.length === 1 ? "task" : "tasks"}
              {deadlinesParsed.length > 0 && (
                <>
                  {" "}+{" "}
                  <span className="font-display text-signal">
                    {deadlinesParsed.length}
                  </span>{" "}
                  {deadlinesParsed.length === 1 ? "deadline" : "deadlines"}
                </>
              )}
              . Confirm the binding suggestions and lock in.
            </p>

            <ul className="flex max-h-[40vh] flex-col gap-2 overflow-y-auto">
              {items.map((it) => {
                const itemBindings = bindingsForTask[it.item_id] ?? [];
                return (
                  <li
                    key={it.item_id}
                    className="rounded-sm border border-hairline bg-void-2/40 px-3 py-2"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span
                        className={`font-display text-[9px] uppercase tracking-macro ${
                          it.kind === "deadline" ? "text-ember" : "text-signal"
                        }`}
                      >
                        <span className="opacity-50">[</span>
                        {it.kind}
                        <span className="opacity-50">]</span>
                      </span>
                      <button
                        type="button"
                        onClick={() => removeItem(it.item_id)}
                        className="rounded-sm border border-hairline px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest text-dust hover:border-ember/40 hover:text-ember"
                      >
                        Discard
                      </button>
                    </div>
                    <label className="flex flex-col gap-1">
                      <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                        Title
                      </span>
                      <input
                        data-testid={`brain-dump-item-title-${it.item_id}`}
                        value={it.title}
                        onChange={(event) =>
                          updateItem(it.item_id, { title: event.target.value })
                        }
                        className="rounded-sm border border-hairline bg-void/50 px-2 py-1 text-sm text-parchment outline-none focus:border-signal/50"
                      />
                    </label>
                    <div
                      className={`mt-2 grid gap-2 ${
                        it.kind === "task"
                          ? "sm:grid-cols-[1fr_120px]"
                          : "sm:grid-cols-1"
                      }`}
                    >
                      <label className="flex flex-col gap-1">
                        <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                          {it.kind === "deadline" ? "Due" : "Start"}
                        </span>
                        <input
                          data-testid={`brain-dump-item-when-${it.item_id}`}
                          type="datetime-local"
                          value={toDateTimeInput(it.when_local)}
                          onChange={(event) =>
                            updateItem(it.item_id, {
                              when_local: event.target.value || null,
                            })
                          }
                          className="rounded-sm border border-hairline bg-void/50 px-2 py-1 font-mono text-[12px] text-parchment outline-none focus:border-signal/50"
                        />
                      </label>
                      {it.kind === "task" && (
                        <label className="flex flex-col gap-1">
                          <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                            Minutes
                          </span>
                          <input
                            data-testid={`brain-dump-item-duration-${it.item_id}`}
                            type="number"
                            min={1}
                            max={720}
                            value={it.duration_minutes ?? ""}
                            onChange={(event) =>
                              updateItem(it.item_id, {
                                duration_minutes: event.target.value
                                  ? Number(event.target.value)
                                  : null,
                              })
                            }
                            className="rounded-sm border border-hairline bg-void/50 px-2 py-1 font-mono text-[12px] text-parchment outline-none focus:border-signal/50"
                          />
                        </label>
                      )}
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] text-dust">
                      {fmtWhen(it.when_local)}
                      {it.category && ` - ${it.category}`}
                      {it.duration_source === "research_prior_v1" && " - prior"}
                      {it.duration_minutes !== null &&
                        ` · ${it.duration_minutes}m`}
                    </div>
                    {it.duration_source === "research_prior_v1" &&
                      it.duration_basis && (
                        <div className="mt-1 text-[10px] text-dust-deep">
                          Initial duration from {it.duration_basis}; edit after
                          creation if the block is different.
                        </div>
                      )}
                    {itemBindings.length > 0 && (
                      <div className="mt-2 flex flex-col gap-1.5">
                        {itemBindings.map((b) => {
                          const choice = bindingChoices[bindingKey(b)];
                          return (
                            <div
                              key={bindingKey(b)}
                              className="flex flex-wrap items-center gap-2 text-[11px]"
                            >
                              <span className="text-dust-deep">
                                Link to {bindingTargetLabel(b)}{" "}
                                <span className="text-parchment">
                                  {b.deadline_title}
                                </span>
                                {b.target_due_at && (
                                  <span>
                                    {" "}
                                    - due {fmtWhen(b.target_due_at)}
                                  </span>
                                )}
                                ?
                              </span>
                              <button
                                data-testid={`brain-dump-binding-yes-${bindingKey(b)}`}
                                type="button"
                                onClick={() =>
                                  setBindingChoice(b, "yes")
                                }
                                className={`rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest transition-colors ${
                                  choice === "yes"
                                    ? "border-signal bg-signal/15 text-signal"
                                    : "border-hairline text-dust hover:border-signal/40 hover:text-parchment"
                                }`}
                              >
                                Yes
                              </button>
                              <button
                                data-testid={`brain-dump-binding-no-${bindingKey(b)}`}
                                type="button"
                                onClick={() =>
                                  setBindingChoice(b, "no")
                                }
                                className={`rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest transition-colors ${
                                  choice === "no"
                                    ? "border-dust-deep bg-void-2 text-dust"
                                    : "border-hairline text-dust hover:border-dust hover:text-parchment"
                                }`}
                              >
                                No
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>

            {error && <p className="text-[11px] text-ember">{error}</p>}

            <div className="flex justify-between gap-2 pt-1">
                  <button
                    data-testid="brain-dump-edit"
                    type="button"
                onClick={() => setStep("dump")}
                disabled={committing}
                className="rounded-sm border border-hairline bg-void-2/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-dust hover:border-signal/40 hover:text-parchment disabled:opacity-50"
              >
                ← Edit dump
              </button>
              <div className="flex items-center gap-2">
                {tier2Unanswered && (
                  <span className="text-[10px] text-ember/80">
                    Answer the binding questions to lock in.
                  </span>
                )}
                <button
                  data-testid="brain-dump-lock-in"
                  type="button"
                  onClick={handleCommit}
                  disabled={committing || tier2Unanswered}
                  className="inline-flex items-center gap-1.5 rounded-sm border border-signal/40 bg-signal/15 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon disabled:opacity-50"
                >
                  {committing && <Loader2 className="h-3 w-3 animate-spin" />}
                  Lock in
                </button>
              </div>
            </div>
          </div>
        )}

        {step === "review_failures" && (
          <div className="flex flex-col gap-4">
            {committedSummary && (
              <p className="text-xs text-dust">
                Saved {committedSummary.tasks} task
                {committedSummary.tasks === 1 ? "" : "s"}
                {committedSummary.deadlines > 0 &&
                  ` + ${committedSummary.deadlines} deadline${committedSummary.deadlines === 1 ? "" : "s"}`}
                . But{" "}
                <span className="text-ember">
                  {failures.length} item{failures.length === 1 ? "" : "s"}{" "}
                  need review
                </span>
                :
              </p>
            )}
            <ul
              data-testid="brain-dump-failures"
              className="flex flex-col gap-2 rounded-sm border border-ember/30 bg-ember/[0.04] p-3"
            >
              {failures.map((f) => (
                <li key={f.item_id} className="text-xs">
                  <div className="font-mono text-[11px] text-parchment">
                    {f.kind === "deadline" ? "📅 " : "▸ "}
                    {f.title}
                  </div>
                  <div className="mt-0.5 text-[11px] text-ember/80">
                    {failureCopy(f.reason, { duplicateDeadlineCopy: true })}
                    {retryCopy(f.retry_hint) && (
                      <span className="text-dust"> · {retryCopy(f.retry_hint)}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap justify-end gap-2 pt-1">
              {canMoveFailedToTomorrow && (
                <button
                  data-testid="brain-dump-move-failed-to-tomorrow"
                  type="button"
                  onClick={() =>
                    retryFailedItems({ movePastToTomorrow: true })
                  }
                  className="rounded-sm border border-signal/40 bg-signal/10 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20"
                >
                  Move to tomorrow
                </button>
              )}
              <button
                data-testid="brain-dump-edit-failed-items"
                type="button"
                onClick={() => retryFailedItems()}
                className="rounded-sm border border-hairline bg-void-2/40 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-dust hover:border-signal/40 hover:text-parchment"
              >
                Edit failed items
              </button>
              <button
                data-testid="brain-dump-failures-done"
                type="button"
                onClick={() => onOpenChange(false)}
                className="rounded-sm border border-signal/40 bg-signal/10 px-4 py-2 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
