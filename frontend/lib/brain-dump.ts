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

export interface BrainDumpParsedItem {
  item_id: string;
  kind: BrainDumpItemKind;
  title: string;
  description: string | null;
  /** ISO datetime in user's local TZ. Null only for low-confidence
   *  task segments — UI fills a default before commit. */
  when_local: string | null;
  duration_minutes: number | null;
  confidence: number;
}

export interface BrainDumpBindingSuggestion {
  task_item_id: string;
  deadline_item_id: string;
  deadline_title: string;
  confidence: number;
  tier: BrainDumpBindingTier;
  source: string;
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
}

export interface BrainDumpCommitBinding {
  task_item_id: string;
  deadline_item_id: string;
}

export interface BrainDumpCommitResponse {
  tasks_created: number;
  deadlines_created: number;
  bindings_applied: number;
  task_ids: string[];
  deadline_ids: string[];
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
): Promise<BrainDumpCommitResponse> {
  return api<BrainDumpCommitResponse>("/v1/brain-dump/commit", {
    method: "POST",
    body: JSON.stringify({ items, bindings }),
  });
}
