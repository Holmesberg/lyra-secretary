"use client";
/**
 * Onboarding surface — two-step brain-dump.
 *
 * REWRITE 2026-04-28 evening (operator-locked: "less magic, more
 * deterministic; catches the user from the get-go").
 *
 * Step 1 — Brain dump
 *   Single textarea. The user pastes everything that's on their mind
 *   (deadlines, tasks, half-thoughts) in any format. NO title field,
 *   NO start/end picker. Category and initial duration are inferred
 *   in preview when the user omits them. The parser splits on commas /
 *   newlines / semicolons / "then" and classifies each segment as
 *   task or deadline. Multiple times in the dump are parsed to each
 *   item's anchor.
 *
 * Step 2 — Confirm
 *   Cards for every parsed item — kind chip (task/deadline), title,
 *   when_local, confidence. Suggested task→deadline bindings render
 *   beneath each task as one-tap [Yes] / [No] pills. User submits the
 *   block; the commit endpoint writes deadlines first, then tasks
 *   bound to confirmed deadlines, all in one transaction.
 *
 * No meta "Plan your week" task is created — that prior implementation
 * was the wrong abstraction. The user just planned; we don't need to
 * tell them to plan again.
 *
 * Skip path is preserved via POST /v1/users/me/skip-onboarding so the
 * user can always bypass. The 2026-05-21 kill-criterion query reads
 * onboarding_completed_at as a binary signal regardless of which path
 * stamped it.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  BrainDumpBindingSuggestion,
  BrainDumpCommitBinding,
  BrainDumpCommitItem,
  BrainDumpFailedItem,
  BrainDumpParsedItem,
  commitBrainDump,
  parseBrainDump,
} from "@/lib/brain-dump";
import {
  bindingKey,
  initialBindingChoices,
  localIsoNow,
  type BrainDumpBindingChoice,
} from "@/lib/brain-dump-ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  userEmail: string;
  onCompleted: () => void;
  onSkipped: () => void;
}

type Step = "dump" | "confirm" | "review_failures";

/** Same vocabulary as BrainDumpQuickModal — keep in sync if changed. */
function failureCopy(reason: string): string {
  switch (reason) {
    case "past_time":
      return "the time is already in the past";
    case "missing_when":
      return "no due date was parsed";
    case "deadline_terminal_state":
      return "the linked deadline is already finished";
    case "deadline_not_found":
      return "couldn't find the linked deadline";
    case "conflict_blocked":
      return "blocked by a hard conflict with an active session";
    case "validation":
      return "didn't pass scheduling rules";
    default:
      return "couldn't be saved";
  }
}

function retryCopy(hint: string | null): string {
  switch (hint) {
    case "schedule_tomorrow_same_time":
      return "Try scheduling tomorrow at the same time.";
    case "edit_when_local":
      return "You can edit this in /today after onboarding.";
    case "remove_deadline_binding":
      return "Unbind from the deadline and retry.";
    default:
      return "";
  }
}

function formatWhen(iso: string | null): string {
  if (!iso) return "no date";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function bindingTargetLabel(b: BrainDumpBindingSuggestion): string {
  return b.target_kind === "existing_deadline"
    ? "existing obligation"
    : "deadline";
}

export function OnboardingFlow({ userEmail, onCompleted, onSkipped }: Props) {
  const [step, setStep] = useState<Step>("dump");
  const [rawText, setRawText] = useState("");
  const [items, setItems] = useState<BrainDumpParsedItem[]>([]);
  const [bindings, setBindings] = useState<BrainDumpBindingSuggestion[]>(
    [],
  );
  // task_item_id → "yes" | "no" | null (null = not answered yet).
  // Pre-populated from parser tier: tier1_auto starts "yes",
  // tier2_ask starts unanswered (block requires resolution).
  const [bindingChoices, setBindingChoices] = useState<
    Record<string, BrainDumpBindingChoice>
  >({});
  const [parsing, setParsing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // LYR-114 fix 2026-04-30: failures from /commit surface so the
  // user knows which items didn't land before exiting onboarding.
  const [failures, setFailures] = useState<BrainDumpFailedItem[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (step === "dump") textareaRef.current?.focus();
  }, [step]);

  // Bindings grouped by task_item_id for fast lookup in the preview.
  const bindingsForTask = useMemo(() => {
    const map: Record<string, BrainDumpBindingSuggestion[]> = {};
    for (const b of bindings) {
      (map[b.task_item_id] ||= []).push(b);
    }
    return map;
  }, [bindings]);

  const tier2Unanswered = useMemo(
    () =>
      bindings.some(
        (b) => b.tier === "tier2_ask" && !bindingChoices[bindingKey(b)],
      ),
    [bindings, bindingChoices],
  );

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

      // Tier 1 auto-bindings start pre-checked "yes". Tier 2 asks
      // start unanswered — user must explicitly tap.
      setBindingChoices(initialBindingChoices(res.bindings));

      if (res.items.length === 0) {
        setError(
          "Couldn't pull anything out of that. Try one item per line: " +
            "'submit assignment Friday', 'read chapter 3 tomorrow', etc.",
        );
        setParsing(false);
        return;
      }
      setStep("confirm");
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Parse failed. Try again.",
      );
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
        category: i.category,
        category_source: i.category_source,
        duration_source: i.duration_source,
        duration_confidence: i.duration_confidence,
        duration_basis: i.duration_basis,
      }));
      const commitBindings: BrainDumpCommitBinding[] = bindings
        .filter((b) => bindingChoices[bindingKey(b)] === "yes")
        .map((b) => ({
          task_item_id: b.task_item_id,
          deadline_item_id:
            b.target_kind === "parsed_deadline" ? b.deadline_item_id : null,
          deadline_id:
            b.target_kind === "existing_deadline" ? b.deadline_id : null,
          target_kind: b.target_kind,
        }));
      const res = await commitBrainDump(commitItems, commitBindings);
      // LYR-114 fix: pause exit on failures so the user actually
      // sees which items didn't land. If everything committed
      // cleanly, exit onboarding as before.
      if (res.failed_items && res.failed_items.length > 0) {
        setFailures(res.failed_items);
        setStep("review_failures");
        setCommitting(false);
        return;
      }
      onCompleted();
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Couldn't save your plan.",
      );
      setCommitting(false);
    }
  }

  async function handleSkip() {
    if (parsing || committing || skipping) return;
    setError(null);
    setSkipping(true);
    onSkipped();
    void api("/v1/users/me/skip-onboarding", { method: "POST" });
  }

  function setBindingChoice(
    binding: BrainDumpBindingSuggestion,
    choice: "yes" | "no",
  ) {
    const key = bindingKey(binding);
    setBindingChoices((s) => {
      const next = { ...s, [key]: choice };
      if (choice === "yes") {
        for (const other of bindings) {
          const otherKey = bindingKey(other);
          if (
            other.task_item_id === binding.task_item_id &&
            otherKey !== key
          ) {
            next[otherKey] = "no";
          }
        }
      }
      return next;
    });
  }

  return (
    <div className="min-h-screen bg-void text-parchment">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <div className="mb-10">
          <p className="terminal-prefix font-mono text-[11px] font-medium uppercase tracking-widest text-signal">
            Onboarding · operative-{userEmail.split("@")[0].slice(0, 8)}
          </p>
          <h1 className="mt-6 text-3xl font-semibold leading-tight tracking-tight text-parchment md:text-4xl">
            {step === "dump"
              ? "Lyra starts learning from the first plan you write."
              : "Look right? Lock it in."}
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-dust md:text-base">
            {step === "dump"
              ? "Brain dump everything that's on your mind — tasks, " +
                "deadlines, half-thoughts. Times and dates inside the " +
                "text get parsed automatically. You'll review before " +
                "anything saves."
              : "Lyra split your dump into tasks and deadlines. " +
                "Confirm any links between them, then save."}
          </p>
        </div>

        {step === "dump" && (
          <div className="terminal-panel p-6">
            <div className="mb-5 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-signal motion-safe:animate-pulse-glow" />
              <span className="font-mono text-[10px] uppercase tracking-widest text-signal">
                Brain dump
              </span>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <textarea
                  ref={textareaRef}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder={
                    "submit assignment Friday\n" +
                    "read chapter 3 tomorrow\n" +
                    "midterm next Wednesday 10am\n" +
                    "call mom this weekend\n" +
                    "finish presentation by Thursday"
                  }
                  rows={9}
                  className="resize-none rounded-sm border border-hairline-signal/30 bg-transparent px-3 py-2 text-sm text-parchment placeholder:text-dust-deep focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40"
                />
                <p className="text-[11px] text-dust-deep">
                  One item per line works best. Commas, semicolons, and
                  &ldquo;then&rdquo; also split.
                </p>
              </div>

              {error && (
                <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
                  {error}
                </div>
              )}

              <div className="mt-2 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  onClick={handleSkip}
                  disabled={parsing || skipping}
                  className={cn(
                    "font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-parchment",
                    (parsing || skipping) && "opacity-40",
                  )}
                >
                  {skipping ? "Skipping…" : "Skip for now"}
                </button>
                <button
                  onClick={handleParse}
                  disabled={parsing || skipping || !rawText.trim()}
                  className="cyber-pill cyber-pill-compact cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
                >
                  {parsing ? "Parsing…" : "Parse my plan →"}
                </button>
              </div>
            </div>
          </div>
        )}

        {step === "confirm" && (
          <div className="flex flex-col gap-4">
            {items.map((it) => {
              const taskBindings = bindingsForTask[it.item_id] || [];
              return (
                <div key={it.item_id} className="terminal-panel p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "font-mono text-[9px] uppercase tracking-widest",
                            it.kind === "deadline"
                              ? "text-ember"
                              : "text-signal",
                          )}
                        >
                          {it.kind}
                        </span>
                        {it.confidence < 0.6 && (
                          <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                            · low confidence
                          </span>
                        )}
                      </div>
                      <div className="mt-1 text-sm font-medium text-parchment">
                        {it.title}
                      </div>
                      <div className="mt-0.5 text-xs text-dust">
                        {formatWhen(it.when_local)}
                        {it.category && (
                          <span className="text-dust-deep">
                            {" "}
                            - {it.category}
                          </span>
                        )}
                        {it.duration_source === "research_prior_v1" && (
                          <span className="text-dust-deep"> - prior</span>
                        )}
                        {it.kind === "task" &&
                          it.duration_minutes != null && (
                            <span className="text-dust-deep">
                              {" "}
                              · {it.duration_minutes} min
                            </span>
                          )}
                      </div>
                    </div>
                  </div>

                  {it.duration_source === "research_prior_v1" &&
                    it.duration_basis && (
                      <div className="mt-1 text-[10px] text-dust-deep">
                        Initial duration from {it.duration_basis}; edit after
                        creation if the block is different.
                      </div>
                    )}

                  {it.kind === "task" && taskBindings.length > 0 && (
                    <div className="mt-3 border-t border-hairline-signal/20 pt-3">
                      {taskBindings.map((b) => (
                        <div
                          key={bindingKey(b)}
                          className="flex items-center justify-between gap-2"
                        >
                          <p className="text-xs text-dust">
                            Link to {bindingTargetLabel(b)}{" "}
                            <span className="text-parchment">
                              &ldquo;{b.deadline_title}&rdquo;
                            </span>
                            {b.target_due_at && (
                              <span className="text-dust-deep">
                                {" "}
                                - due {formatWhen(b.target_due_at)}
                              </span>
                            )}
                            ?
                          </p>
                          <div className="flex gap-1">
                            <button
                              type="button"
                              onClick={() => setBindingChoice(b, "yes")}
                              className={cn(
                                "rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest transition-colors",
                                bindingChoices[bindingKey(b)] === "yes"
                                  ? "border-signal bg-signal/15 text-signal"
                                  : "border-hairline-signal/30 text-dust hover:text-parchment",
                              )}
                            >
                              Yes
                            </button>
                            <button
                              type="button"
                              onClick={() => setBindingChoice(b, "no")}
                              className={cn(
                                "rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest transition-colors",
                                bindingChoices[bindingKey(b)] === "no"
                                  ? "border-ember bg-ember/15 text-ember"
                                  : "border-hairline-signal/30 text-dust hover:text-parchment",
                              )}
                            >
                              No
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {error && (
              <div className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
                {error}
              </div>
            )}

            <div className="mt-2 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
              <button
                onClick={() => {
                  setStep("dump");
                  setError(null);
                }}
                disabled={committing}
                className={cn(
                  "font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:text-parchment",
                  committing && "opacity-40",
                )}
              >
                ← Edit dump
              </button>
              {tier2Unanswered && (
                <span className="text-[10px] text-ember/80">
                  Answer the binding questions to lock in.
                </span>
              )}
              <button
                onClick={handleCommit}
                disabled={committing || items.length === 0 || tier2Unanswered}
                className="cyber-pill cyber-pill-compact cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                {committing ? "Saving…" : "Lock in"}
              </button>
            </div>
          </div>
        )}

        {step === "review_failures" && (
          <div className="flex flex-col gap-6">
            <p className="text-sm text-dust">
              Your plan landed.{" "}
              <span className="text-ember">
                {failures.length} item{failures.length === 1 ? "" : "s"}{" "}
                couldn&apos;t be scheduled
              </span>{" "}
              and need attention:
            </p>
            <ul className="flex flex-col gap-3 rounded-sm border border-ember/30 bg-ember/[0.04] p-4">
              {failures.map((f) => (
                <li key={f.item_id} className="text-sm">
                  <div className="font-mono text-xs text-parchment">
                    {f.kind === "deadline" ? "📅 " : "▸ "}
                    {f.title}
                  </div>
                  <div className="mt-1 text-xs text-ember/85">
                    {failureCopy(f.reason)}
                    {retryCopy(f.retry_hint) && (
                      <span className="text-dust"> · {retryCopy(f.retry_hint)}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex justify-end pt-1">
              <button
                onClick={() => {
                  setFailures([]);
                  onCompleted();
                }}
                className="cyber-pill cyber-pill-compact cyber-pill-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                Continue to Lyra
              </button>
            </div>
          </div>
        )}

        <p className="mt-10 text-center font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          :: planning ritual · session 0 · patterns emerge from here
        </p>
      </div>
    </div>
  );
}
