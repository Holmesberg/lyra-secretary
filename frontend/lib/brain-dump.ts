/**
 * Brain-dump onboarding API client (2026-04-28 evening).
 *
 * Two-step contract:
 *   1. POST /v1/brain-dump/parse  — heuristic preview, no DB writes.
 *   2. POST /v1/brain-dump/commit — persist confirmed items + bindings
 *                                    in a single transaction.
 *
 * The parse step assigns opaque `item_id` UUIDs to every parsed item.
 * The client re-sends those exact ids in the commit payload so the
 * backend can resolve task→deadline bindings without trusting any
 * client-side mapping.
 */
import { api } from "@/lib/api";

export type BrainDumpItemKind = "task" | "deadline";
export type BrainDumpBindingTier =
  | "tier1_auto"
  | "tier2_ask"
  | "tier3_skip";
export type BrainDumpBindingTargetKind =
  | "parsed_deadline"
  | "existing_deadline";

export interface BrainDumpParsedItem {
  item_id: string;
  kind: BrainDumpItemKind;
  title: string;
  description: string | null;
  /** ISO datetime in user's local TZ. Null only for low-confidence
   *  task segments — UI fills a default before commit. */
  when_local: string | null;
  duration_minutes: number | null;
  category: string | null;
  category_source: string | null;
  duration_source: string | null;
  duration_confidence: number | null;
  duration_basis: string | null;
  confidence: number;
}

export interface BrainDumpBindingSuggestion {
  binding_id: string;
  task_item_id: string;
  deadline_item_id: string;
  deadline_title: string;
  confidence: number;
  tier: BrainDumpBindingTier;
  source: string;
  target_kind: BrainDumpBindingTargetKind;
  deadline_id: string | null;
  target_due_at: string | null;
  target_state: string | null;
  target_origin: string | null;
}

export interface BrainDumpParseResponse {
  items: BrainDumpParsedItem[];
  bindings: BrainDumpBindingSuggestion[];
  parser_status: "heuristic_parsed" | "empty";
}

export interface BrainDumpCommitItem {
  item_id: string;
  kind: BrainDumpItemKind;
  title: string;
  description?: string | null;
  when_local?: string | null;
  duration_minutes?: number | null;
  category?: string | null;
  category_source?: string | null;
  duration_source?: string | null;
  duration_confidence?: number | null;
  duration_basis?: string | null;
}

export interface BrainDumpCommitBinding {
  task_item_id: string;
  deadline_item_id?: string | null;
  deadline_id?: string | null;
  target_kind?: BrainDumpBindingTargetKind;
}

/** LYR-114 surface (2026-04-30): per-item failure shape so the
 *  frontend can render a retry-or-edit panel instead of silently
 *  dropping items the backend rejected. */
export interface BrainDumpFailedItem {
  item_id: string;
  kind: BrainDumpItemKind;
  title: string;
  /** Machine-readable reason — see backend BrainDumpFailedItem schema:
   *  "past_time" | "missing_when" | "deadline_terminal_state"
   *  | "deadline_not_found" | "validation" | "conflict_blocked" | "internal" */
  reason: string;
  detail: string;
  /** UX hint — what the frontend should offer as a one-click recovery:
   *  "schedule_tomorrow_same_time" | "edit_when_local"
   *  | "remove_deadline_binding" | null */
  retry_hint: string | null;
}

export interface BrainDumpCommitOutcome {
  item_id: string;
  kind: BrainDumpItemKind;
  title: string;
  status: "created" | "reused" | "rejected" | "failed";
  canonical_id: string | null;
  reason: string | null;
  detail: string | null;
  retry_hint: string | null;
}

export interface BrainDumpCommitResponse {
  tasks_created: number;
  deadlines_created: number;
  bindings_applied: number;
  task_ids: string[];
  deadline_ids: string[];
  /** Optional while a newer frontend is paired with a lagging backend. */
  outcomes?: BrainDumpCommitOutcome[];
  /** LYR-114 fix 2026-04-30: empty when all items committed cleanly. */
  failed_items: BrainDumpFailedItem[];
}

export async function parseBrainDump(
  rawText: string,
  currentLocalIso: string,
): Promise<BrainDumpParseResponse> {
  return api<BrainDumpParseResponse>("/v1/brain-dump/parse", {
    method: "POST",
    body: JSON.stringify({
      raw_text: rawText,
      current_local_iso: currentLocalIso,
    }),
  });
}

export async function commitBrainDump(
  items: BrainDumpCommitItem[],
  bindings: BrainDumpCommitBinding[],
  idempotencyKey?: string,
): Promise<BrainDumpCommitResponse> {
  const key =
    idempotencyKey ??
    (typeof crypto !== "undefined" && "randomUUID" in crypto
      ? `brain-dump-${crypto.randomUUID()}`
      : `brain-dump-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  return api<BrainDumpCommitResponse>("/v1/brain-dump/commit", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": key,
    },
    body: JSON.stringify({ items, bindings }),
  });
}
