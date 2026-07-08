"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  createTask,
  type CreateTaskInput,
  type CreateTaskResponse,
} from "@/lib/tasks";
import {
  nudgePayloadFromDecision,
  type NudgeDecisionData,
} from "@/lib/creation-nudge";

export interface PausedConflict {
  taskId: string;
  title: string;
  blockingTitles: string[];
}

export interface SoftConflict {
  reasons: string[];
  overlapTitles: string[];
  executingTitles: string[];
  duplicateTitle: string | null;
}

export interface NewTaskSubmitDraft {
  title: string;
  start: string;
  end: string;
  category: string;
  description: string;
  deadlineId: string | null;
  nudgeDecisionData: NudgeDecisionData | null;
}

export type NewTaskSubmitResult =
  | { kind: "created" }
  | { kind: "interruptionCreated" }
  | { kind: "pausedConflict"; conflict: PausedConflict }
  | { kind: "softConflict"; conflict: SoftConflict }
  | { kind: "error"; message: string };

type SubmitMode = "normal" | "force" | "interruption";

interface IdempotencyEntry {
  fingerprint: string;
  key: string;
}

interface InFlightEntry {
  fingerprint: string;
  promise: Promise<NewTaskSubmitResult>;
}

interface UseNewTaskSubmitControllerOptions {
  open: boolean;
  onReset: () => void;
  onCreated: () => void;
  onClose: () => void;
  onInterruptionCreated?: (taskId: string, taskTitle: string) => void;
}

function newIdempotencyKey(scope: string): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${scope}:${random}`;
}

function createPayloadFromDraft(
  draft: NewTaskSubmitDraft,
  force: boolean
): CreateTaskInput {
  return {
    title: draft.title.trim(),
    start: new Date(draft.start).toISOString(),
    end: new Date(draft.end).toISOString(),
    category: draft.category,
    description: draft.description.trim() || undefined,
    deadline_id: draft.deadlineId ?? undefined,
    force,
    ...nudgePayloadFromDecision(draft.nudgeDecisionData),
  };
}

function createPayloadFingerprint(
  mode: SubmitMode,
  payload: CreateTaskInput
): string {
  return JSON.stringify({
    mode,
    title: payload.title,
    start: payload.start,
    end: payload.end,
    category: payload.category,
    description: payload.description ?? null,
    deadline_id: payload.deadline_id ?? null,
    force: payload.force ?? false,
    nudge_decision: payload.nudge_decision ?? null,
    nudge_suggested_duration_minutes:
      payload.nudge_suggested_duration_minutes ?? null,
    nudge_bias_factor: payload.nudge_bias_factor ?? null,
    nudge_sample_size: payload.nudge_sample_size ?? null,
    nudge_viewed_at: payload.nudge_viewed_at ?? null,
  });
}

function classifyNormalConflict(
  response: CreateTaskResponse,
  draft: NewTaskSubmitDraft,
  canCreateInterruption: boolean
): NewTaskSubmitResult {
  if (response.created) {
    return { kind: "created" };
  }
  if (response.conflicts.length === 0) {
    return { kind: "error", message: "Task was not created." };
  }

  const paused = response.conflicts.filter((conflict) => conflict.state === "PAUSED");
  const startingSoon = new Date(draft.start).getTime() - Date.now() < 5 * 60_000;
  if (paused.length > 0 && canCreateInterruption && startingSoon) {
    return {
      kind: "pausedConflict",
      conflict: {
        taskId: paused[0].task_id,
        title: paused[0].title,
        blockingTitles: response.conflicts
          .filter((conflict) => conflict.state !== "PAUSED")
          .map((conflict) => conflict.title),
      },
    };
  }

  if (response.severity === "soft" || response.severity === "hard") {
    const executing = response.conflicts
      .filter(
        (conflict) =>
          conflict.gate_id === "executing_overlap" ||
          conflict.gate_id === "active_overlap"
      )
      .map((conflict) => conflict.title);
    const overlaps = response.conflicts
      .filter((conflict) => conflict.gate_id === "planned_overlap")
      .map((conflict) => conflict.title);
    const dups = response.conflicts
      .filter((conflict) => conflict.gate_id === "duplicate_title")
      .map((conflict) => conflict.title);
    return {
      kind: "softConflict",
      conflict: {
        reasons: response.soft_reasons ?? [],
        overlapTitles: overlaps,
        executingTitles: executing,
        duplicateTitle: dups[0] ?? null,
      },
    };
  }

  return {
    kind: "error",
    message: `Conflicts with: ${response.conflicts
      .map((conflict) => conflict.title)
      .join(", ")}. Adjust the time and try again.`,
  };
}

export function useNewTaskSubmitController({
  open,
  onReset,
  onCreated,
  onClose,
  onInterruptionCreated,
}: UseNewTaskSubmitControllerOptions) {
  const idempotencyRef = useRef<Partial<Record<SubmitMode, IdempotencyEntry>>>({});
  const inFlightRef = useRef<Partial<Record<SubmitMode, InFlightEntry>>>({});

  useEffect(() => {
    if (!open) {
      idempotencyRef.current = {};
      inFlightRef.current = {};
    }
  }, [open]);

  const idempotencyKeyFor = useCallback(
    (mode: SubmitMode, payload: CreateTaskInput, fingerprint?: string) => {
      const payloadFingerprint =
        fingerprint ?? createPayloadFingerprint(mode, payload);
      const current = idempotencyRef.current[mode];
      if (current?.fingerprint === payloadFingerprint) {
        return current.key;
      }
      const key = newIdempotencyKey(`new-task:${mode}`);
      idempotencyRef.current[mode] = { fingerprint: payloadFingerprint, key };
      return key;
    },
    []
  );

  const runOnceInFlight = useCallback(
    (
      mode: SubmitMode,
      payload: CreateTaskInput,
      work: (fingerprint: string) => Promise<NewTaskSubmitResult>
    ) => {
      const fingerprint = createPayloadFingerprint(mode, payload);
      const current = inFlightRef.current[mode];
      if (current?.fingerprint === fingerprint) {
        return current.promise;
      }

      const promise = work(fingerprint).finally(() => {
        if (inFlightRef.current[mode]?.fingerprint === fingerprint) {
          delete inFlightRef.current[mode];
        }
      });
      inFlightRef.current[mode] = { fingerprint, promise };
      return promise;
    },
    []
  );

  const submit = useCallback(
    async (draft: NewTaskSubmitDraft): Promise<NewTaskSubmitResult> => {
      const payload = createPayloadFromDraft(draft, false);
      return runOnceInFlight("normal", payload, async (fingerprint) => {
        const response = await createTask({
          ...payload,
          idempotencyKey: idempotencyKeyFor("normal", payload, fingerprint),
        });
        const result = classifyNormalConflict(
          response,
          draft,
          Boolean(onInterruptionCreated)
        );
        if (result.kind === "created") {
          onReset();
          onCreated();
          onClose();
        }
        return result;
      });
    },
    [
      idempotencyKeyFor,
      onClose,
      onCreated,
      onInterruptionCreated,
      onReset,
      runOnceInFlight,
    ]
  );

  const submitWithForce = useCallback(
    async (draft: NewTaskSubmitDraft): Promise<NewTaskSubmitResult> => {
      const payload = createPayloadFromDraft(draft, true);
      return runOnceInFlight("force", payload, async (fingerprint) => {
        const response = await createTask({
          ...payload,
          idempotencyKey: idempotencyKeyFor("force", payload, fingerprint),
        });
        if (!response.created) {
          return {
            kind: "error",
            message:
              response.severity === "hard"
                ? "Override rejected - an active timer now overlaps. Stop it first."
                : "Override failed.",
          };
        }
        onReset();
        onCreated();
        onClose();
        return { kind: "created" };
      });
    },
    [idempotencyKeyFor, onClose, onCreated, onReset, runOnceInFlight]
  );

  const submitAsInterruption = useCallback(
    async (draft: NewTaskSubmitDraft): Promise<NewTaskSubmitResult> => {
      const payload = createPayloadFromDraft(draft, true);
      return runOnceInFlight("interruption", payload, async (fingerprint) => {
        const response = await createTask({
          ...payload,
          idempotencyKey: idempotencyKeyFor(
            "interruption",
            payload,
            fingerprint
          ),
        });
        if (!response.created || !response.task_id) {
          return { kind: "error", message: "Failed to create interruption task." };
        }
        const createdTitle = payload.title;
        const createdId = response.task_id;
        onReset();
        onClose();
        onInterruptionCreated?.(createdId, createdTitle);
        return { kind: "interruptionCreated" };
      });
    },
    [idempotencyKeyFor, onClose, onInterruptionCreated, onReset, runOnceInFlight]
  );

  return {
    submit,
    submitWithForce,
    submitAsInterruption,
  };
}
