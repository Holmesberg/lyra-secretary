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
import { useEffect, useRef, useState } from "react";
import { ArrowRight, CalendarPlus, PencilLine, Trash2 } from "lucide-react";
import {
  bindingKey,
  brainDumpBindingTargetLabel,
  failureCopy,
  pad2,
} from "@/lib/brain-dump-ui";
import { api } from "@/lib/api";
import { useBrainDumpFlow } from "@/lib/hooks/use-brain-dump-flow";
import { cn } from "@/lib/utils";

interface Props {
  userEmail: string;
  onCompleted: () => void;
  onSkipped: () => void;
}

/** Onboarding-specific retry hints; shared failure wording lives in brain-dump-ui. */
function retryCopy(hint: string | null): string {
  switch (hint) {
    case "schedule_tomorrow_same_time":
      return "Try scheduling tomorrow at the same time.";
    case "edit_when_local":
      return "Add or correct the date, then retry.";
    case "remove_deadline_binding":
      return "Unbind from the deadline and retry.";
    default:
      return "";
  }
}

function toDateTimeInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso.slice(0, 16);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(
    date.getDate(),
  )}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
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

export function OnboardingFlow({ userEmail, onCompleted, onSkipped }: Props) {
  const [skipping, setSkipping] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const {
    step,
    setStep,
    rawText,
    setRawText,
    items,
    bindingChoices,
    failures,
    parsing,
    committing,
    error,
    setError,
    handleParse,
    handleCommit,
    setBindingChoice,
    updateItem,
    removeItem,
    retryFailedItems,
    bindingsForTask,
    tier2Unanswered,
    canMoveFailedToTomorrow,
  } = useBrainDumpFlow({
    emptyTextError: "Type something first — at least one task or deadline.",
    emptyResultError:
      "Couldn't pull anything out of that. Try one item per line: 'submit assignment Friday', 'read chapter 3 tomorrow', etc.",
    parseError: "Parse failed. Try again.",
    commitError: "Couldn't save your plan.",
    onCleanCommit: () => onCompleted(),
  });

  useEffect(() => {
    if (step === "dump") textareaRef.current?.focus();
  }, [step]);

  async function handleSkip() {
    if (parsing || committing || skipping) return;
    setError(null);
    setSkipping(true);
    try {
      await api("/v1/users/me/skip-onboarding", { method: "POST" });
      onSkipped();
    } catch (skipError) {
      setError(
        skipError instanceof Error
          ? skipError.message
          : "Couldn't skip onboarding. Try again.",
      );
      setSkipping(false);
    }
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
              ? "LyraOS starts learning from the first plan you write."
              : step === "review_failures"
                ? "A few items need attention."
                : "Look right? Lock it in."}
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-dust md:text-base">
            {step === "dump"
              ? "Brain dump everything that's on your mind — tasks, " +
                "deadlines, half-thoughts. Times and dates inside the " +
                "text get parsed automatically. You'll review before " +
                "anything saves."
              : step === "review_failures"
                ? "Saved items stay saved. Fix only the failed rows, or continue with what landed."
                : "LyraOS split your dump into tasks and deadlines. " +
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
                  data-testid="onboarding-brain-dump-textarea"
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
                <div
                  data-testid="onboarding-brain-dump-error"
                  role="alert"
                  className="rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember"
                >
                  {error}
                </div>
              )}

              <div className="mt-2 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  data-testid="onboarding-brain-dump-skip"
                  type="button"
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
                  data-testid="onboarding-brain-dump-parse"
                  type="button"
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
                      <label className="mt-2 flex flex-col gap-1.5">
                        <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                          Title
                        </span>
                        <input
                          data-testid={`onboarding-brain-dump-item-title-${it.item_id}`}
                          value={it.title}
                          onChange={(event) =>
                            updateItem(it.item_id, { title: event.target.value })
                          }
                          className="rounded-sm border border-hairline-signal/30 bg-void/50 px-3 py-2 text-sm text-parchment outline-none focus:border-signal/60 focus:ring-1 focus:ring-signal/30"
                        />
                      </label>
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
                    <button
                      type="button"
                      title="Discard item"
                      aria-label={`Discard ${it.title}`}
                      onClick={() => removeItem(it.item_id)}
                      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-hairline-signal/30 text-dust transition-colors hover:border-ember/50 hover:text-ember focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ember/60"
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>

                  <div
                    className={cn(
                      "mt-3 grid gap-3",
                      it.kind === "task"
                        ? "sm:grid-cols-[minmax(0,1fr)_120px]"
                        : "sm:grid-cols-1",
                    )}
                  >
                    <label className="flex min-w-0 flex-col gap-1.5">
                      <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                        {it.kind === "deadline" ? "Due" : "Start"}
                      </span>
                      <input
                        data-testid={`onboarding-brain-dump-item-when-${it.item_id}`}
                        type="datetime-local"
                        value={toDateTimeInput(it.when_local)}
                        onChange={(event) =>
                          updateItem(it.item_id, {
                            when_local: event.target.value || null,
                          })
                        }
                        className="min-w-0 rounded-sm border border-hairline-signal/30 bg-void/50 px-3 py-2 font-mono text-xs text-parchment outline-none focus:border-signal/60 focus:ring-1 focus:ring-signal/30"
                      />
                    </label>
                    {it.kind === "task" && (
                      <label className="flex flex-col gap-1.5">
                        <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                          Minutes
                        </span>
                        <input
                          data-testid={`onboarding-brain-dump-item-duration-${it.item_id}`}
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
                          className="rounded-sm border border-hairline-signal/30 bg-void/50 px-3 py-2 font-mono text-xs text-parchment outline-none focus:border-signal/60 focus:ring-1 focus:ring-signal/30"
                        />
                      </label>
                    )}
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
                            Link to {brainDumpBindingTargetLabel(b, "deadline")}{" "}
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
                data-testid="onboarding-brain-dump-lock-in"
                type="button"
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
              The items that worked are already saved. Only the rows below
              will be retried. {" "}
              <span className="text-ember">
                {failures.length} item{failures.length === 1 ? "" : "s"}{" "}
                couldn&apos;t be scheduled
              </span>{" "}
              and need attention:
            </p>
            <ul
              data-testid="onboarding-brain-dump-failures"
              className="flex flex-col gap-3 rounded-sm border border-ember/30 bg-ember/[0.04] p-4"
            >
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
            <div className="flex flex-col gap-2 pt-1 sm:flex-row sm:flex-wrap sm:justify-end">
              {canMoveFailedToTomorrow && (
                <button
                  data-testid="onboarding-brain-dump-move-failed-to-tomorrow"
                  type="button"
                  onClick={() =>
                    retryFailedItems({ movePastToTomorrow: true })
                  }
                  className="cyber-pill cyber-pill-compact inline-flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
                >
                  <CalendarPlus className="h-3.5 w-3.5" aria-hidden="true" />
                  Move to tomorrow
                </button>
              )}
              <button
                data-testid="onboarding-brain-dump-edit-failed-items"
                type="button"
                onClick={() => retryFailedItems()}
                className="cyber-pill cyber-pill-compact inline-flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                <PencilLine className="h-3.5 w-3.5" aria-hidden="true" />
                Edit failed items
              </button>
              <button
                data-testid="onboarding-brain-dump-continue-saved"
                type="button"
                onClick={onCompleted}
                className="cyber-pill cyber-pill-compact cyber-pill-primary inline-flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/70"
              >
                Continue with saved items
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
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
