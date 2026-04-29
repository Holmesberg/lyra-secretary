"use client";
/**
 * BrainDumpQuickModal — modal-shaped brain-dump composer for /pulse.
 *
 * Operator request 2026-04-29 night: clicking Capture on /pulse should
 * open the brain-dump modal so the magic fires more often without a
 * full nav to /today. Reuses the existing parse + commit API helpers
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
  type BrainDumpCommitBinding,
  type BrainDumpCommitItem,
  type BrainDumpParsedItem,
} from "@/lib/brain-dump";

type Step = "dump" | "confirm";

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function localIsoNow(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(
    d.getDate()
  )}T${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
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
  const [rawText, setRawText] = useState(seedText);
  const [items, setItems] = useState<BrainDumpParsedItem[]>([]);
  const [bindings, setBindings] = useState<BrainDumpBindingSuggestion[]>([]);
  const [bindingChoices, setBindingChoices] = useState<
    Record<string, "yes" | "no">
  >({});
  const [parsing, setParsing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Sync the textarea + step when the modal opens / seed changes.
  useEffect(() => {
    if (open) {
      setStep("dump");
      setRawText(seedText);
      setItems([]);
      setBindings([]);
      setBindingChoices({});
      setError(null);
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
      // Tier 1 auto-bindings start pre-checked yes.
      const initial: Record<string, "yes" | "no"> = {};
      for (const b of res.bindings) {
        if (b.tier === "tier1_auto") {
          initial[b.task_item_id] = "yes";
        }
      }
      setBindingChoices(initial);
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
    if (committing) return;
    setError(null);
    setCommitting(true);
    try {
      const commitItems: BrainDumpCommitItem[] = items.map((i) => ({
        item_id: i.item_id,
        kind: i.kind,
        title: i.title,
        description: i.description,
        when_local: i.when_local,
        duration_minutes: i.duration_minutes,
      }));
      const commitBindings: BrainDumpCommitBinding[] = bindings
        .filter((b) => bindingChoices[b.task_item_id] === "yes")
        .map((b) => ({
          task_item_id: b.task_item_id,
          deadline_item_id: b.deadline_item_id,
        }));
      const res = await commitBrainDump(commitItems, commitBindings);
      // Invalidate every cache key the dashboard depends on so the
      // moment the modal closes the new rows appear.
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["deadlines"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["tasks-range"] });
      onCompleted?.({
        tasks: res.tasks_created,
        deadlines: res.deadlines_created,
        bindings: res.bindings_applied,
      });
      onOpenChange(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Couldn't save. Try again.");
      setCommitting(false);
    }
  }

  function setBindingChoice(taskItemId: string, choice: "yes" | "no") {
    setBindingChoices((s) => ({ ...s, [taskItemId]: choice }));
  }

  const tasksParsed = items.filter((i) => i.kind === "task");
  const deadlinesParsed = items.filter((i) => i.kind === "deadline");
  const bindingsForTask: Record<string, BrainDumpBindingSuggestion[]> = {};
  for (const b of bindings) {
    (bindingsForTask[b.task_item_id] ||= []).push(b);
  }
  const tier2Unanswered = bindings.some(
    (b) => b.tier === "tier2_ask" && !bindingChoices[b.task_item_id]
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
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
              Lyra parses titles, dates, and durations. Examples: "submit
              lab 8 friday 11pm", "read chapter 3 tomorrow 30min".
            </p>
            <textarea
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
                type="button"
                onClick={() => onOpenChange(false)}
                className="rounded-sm border border-hairline bg-void-2/40 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-dust hover:border-signal/40 hover:text-parchment"
              >
                Cancel
              </button>
              <button
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
              Lyra found{" "}
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
                    <div className="flex items-baseline gap-2">
                      <span
                        className={`font-display text-[9px] uppercase tracking-macro ${
                          it.kind === "deadline" ? "text-ember" : "text-signal"
                        }`}
                      >
                        <span className="opacity-50">[</span>
                        {it.kind}
                        <span className="opacity-50">]</span>
                      </span>
                      <span className="text-sm text-parchment">{it.title}</span>
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] text-dust">
                      {fmtWhen(it.when_local)}
                      {it.duration_minutes !== null &&
                        ` · ${it.duration_minutes}m`}
                    </div>
                    {itemBindings.length > 0 && (
                      <div className="mt-2 flex flex-col gap-1.5">
                        {itemBindings.map((b) => {
                          const choice = bindingChoices[b.task_item_id];
                          return (
                            <div
                              key={b.deadline_item_id}
                              className="flex items-center gap-2 text-[11px]"
                            >
                              <span className="text-dust-deep">
                                Link to{" "}
                                <span className="text-parchment">
                                  {b.deadline_title}
                                </span>
                                ?
                              </span>
                              <button
                                type="button"
                                onClick={() =>
                                  setBindingChoice(b.task_item_id, "yes")
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
                                type="button"
                                onClick={() =>
                                  setBindingChoice(b.task_item_id, "no")
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
      </DialogContent>
    </Dialog>
  );
}
