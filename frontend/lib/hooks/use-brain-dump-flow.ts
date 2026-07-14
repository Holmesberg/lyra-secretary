"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import {
  commitBrainDump,
  parseBrainDump,
  type BrainDumpBindingSuggestion,
  type BrainDumpCommitResponse,
  type BrainDumpFailedItem,
  type BrainDumpParsedItem,
} from "@/lib/brain-dump";
import {
  bindingKey,
  buildBrainDumpCommitBindings,
  buildBrainDumpCommitItems,
  chooseBrainDumpBinding,
  initialBindingChoices,
  localIsoNow,
  pad2,
  type BrainDumpBindingChoice,
} from "@/lib/brain-dump-ui";

export type BrainDumpFlowStep = "dump" | "confirm" | "review_failures";

export interface BrainDumpCommitSummary {
  tasks: number;
  deadlines: number;
  bindings: number;
}

interface BrainDumpFlowOptions {
  emptyTextError: string;
  emptyResultError: string;
  parseError: string;
  commitError: string;
  useStableCommitKey?: boolean;
  onCommitResult?: (response: BrainDumpCommitResponse) => void;
  onCleanCommit?: (response: BrainDumpCommitResponse) => void;
}

function newCommitKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `brain-dump-${crypto.randomUUID()}`;
  }
  return `brain-dump-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function moveLocalInputByDays(value: string | null, days: number): string | null {
  const base = value ? new Date(value) : new Date();
  if (Number.isNaN(base.getTime())) return value;
  base.setDate(base.getDate() + days);
  return `${base.getFullYear()}-${pad2(base.getMonth() + 1)}-${pad2(
    base.getDate(),
  )}T${pad2(base.getHours())}:${pad2(base.getMinutes())}:${pad2(
    base.getSeconds(),
  )}`;
}

export function useBrainDumpFlow(options: BrainDumpFlowOptions) {
  const [step, setStep] = useState<BrainDumpFlowStep>("dump");
  const [rawText, setRawText] = useState("");
  const [items, setItems] = useState<BrainDumpParsedItem[]>([]);
  const [bindings, setBindings] = useState<BrainDumpBindingSuggestion[]>([]);
  const [bindingChoices, setBindingChoices] = useState<
    Record<string, BrainDumpBindingChoice>
  >({});
  const [failures, setFailures] = useState<BrainDumpFailedItem[]>([]);
  const [committedSummary, setCommittedSummary] =
    useState<BrainDumpCommitSummary | null>(null);
  const [parsing, setParsing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const commitKeyRef = useRef<string | null>(null);
  const commitInFlightRef = useRef(false);

  const rotateCommitKey = useCallback(() => {
    if (options.useStableCommitKey) {
      commitKeyRef.current = newCommitKey();
    }
  }, [options.useStableCommitKey]);

  const reset = useCallback((nextRawText = "") => {
    setStep("dump");
    setRawText(nextRawText);
    setItems([]);
    setBindings([]);
    setBindingChoices({});
    setFailures([]);
    setCommittedSummary(null);
    setError(null);
    setParsing(false);
    setCommitting(false);
    commitKeyRef.current = null;
    commitInFlightRef.current = false;
  }, []);

  const handleParse = useCallback(async () => {
    if (parsing) return;
    setError(null);
    if (!rawText.trim()) {
      setError(options.emptyTextError);
      return;
    }
    setParsing(true);
    try {
      const res = await parseBrainDump(rawText, localIsoNow());
      setItems(res.items);
      setBindings(res.bindings);
      setFailures([]);
      setCommittedSummary(null);
      rotateCommitKey();
      setBindingChoices(initialBindingChoices(res.bindings));
      if (res.items.length === 0) {
        setError(options.emptyResultError);
        setParsing(false);
        return;
      }
      setStep("confirm");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : options.parseError);
    } finally {
      setParsing(false);
    }
  }, [
    options.emptyResultError,
    options.emptyTextError,
    options.parseError,
    parsing,
    rawText,
    rotateCommitKey,
  ]);

  const handleCommit = useCallback(async () => {
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
      if (options.useStableCommitKey && !commitKeyRef.current) {
        commitKeyRef.current = newCommitKey();
      }
      const res = await commitBrainDump(
        commitItems,
        commitBindings,
        options.useStableCommitKey ? commitKeyRef.current ?? undefined : undefined,
      );
      options.onCommitResult?.(res);
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
      options.onCleanCommit?.(res);
    } catch (e: unknown) {
      commitInFlightRef.current = false;
      setError(e instanceof Error ? e.message : options.commitError);
      setCommitting(false);
    }
  }, [
    bindingChoices,
    bindings,
    committing,
    items,
    options,
  ]);

  const setBindingChoice = useCallback(
    (binding: BrainDumpBindingSuggestion, choice: BrainDumpBindingChoice) => {
      setBindingChoices((current) =>
        chooseBrainDumpBinding(current, bindings, binding, choice),
      );
    },
    [bindings],
  );

  const updateItem = useCallback(
    (
      itemId: string,
      patch: Partial<
        Pick<BrainDumpParsedItem, "title" | "when_local" | "duration_minutes">
      >,
    ) => {
      setItems((current) =>
        current.map((item) =>
          item.item_id === itemId ? { ...item, ...patch } : item,
        ),
      );
      rotateCommitKey();
    },
    [rotateCommitKey],
  );

  const removeItem = useCallback(
    (itemId: string) => {
      const nextBindings = bindings.filter(
        (binding) =>
          binding.task_item_id !== itemId && binding.deadline_item_id !== itemId,
      );
      setItems((current) => current.filter((item) => item.item_id !== itemId));
      setBindings(nextBindings);
      setBindingChoices(initialBindingChoices(nextBindings));
      rotateCommitKey();
    },
    [bindings, rotateCommitKey],
  );

  const retryFailedItems = useCallback(
    (retryOptions?: { movePastToTomorrow?: boolean }) => {
      const failedIds = new Set(failures.map((failure) => failure.item_id));
      const failedById = new Map(
        failures.map((failure) => [failure.item_id, failure]),
      );
      const nextItems = items
        .filter((item) => failedIds.has(item.item_id))
        .map((item) => {
          const failure = failedById.get(item.item_id);
          if (
            retryOptions?.movePastToTomorrow &&
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
      rotateCommitKey();
      setStep("confirm");
    },
    [bindings, failures, items, rotateCommitKey],
  );

  const clearFailures = useCallback(() => {
    setFailures([]);
    setCommittedSummary(null);
  }, []);

  const bindingsForTask = useMemo(() => {
    const map: Record<string, BrainDumpBindingSuggestion[]> = {};
    for (const binding of bindings) {
      (map[binding.task_item_id] ||= []).push(binding);
    }
    return map;
  }, [bindings]);

  const tier2Unanswered = useMemo(
    () =>
      bindings.some(
        (binding) =>
          binding.tier === "tier2_ask" &&
          !bindingChoices[bindingKey(binding)],
      ),
    [bindingChoices, bindings],
  );

  return {
    step,
    setStep,
    rawText,
    setRawText,
    items,
    bindings,
    bindingChoices,
    failures,
    committedSummary,
    parsing,
    committing,
    error,
    setError,
    reset,
    handleParse,
    handleCommit,
    setBindingChoice,
    updateItem,
    removeItem,
    retryFailedItems,
    clearFailures,
    tasksParsed: items.filter((item) => item.kind === "task"),
    deadlinesParsed: items.filter((item) => item.kind === "deadline"),
    bindingsForTask,
    tier2Unanswered,
    canMoveFailedToTomorrow: failures.some(
      (failure) => failure.retry_hint === "schedule_tomorrow_same_time",
    ),
  };
}
