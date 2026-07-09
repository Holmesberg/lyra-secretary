"use client";
/**
 * LlmEnrichmentChip — magic-for-alpha Workstream 1 (2026-04-28).
 *
 * Renders post-create on a TaskRow when the LLM enrichment worker has
 * populated `task.llm_*` fields. Three tiers of progressive revelation
 * (operator-locked 2026-04-28; Tier 2 copy restored to operator's
 * Q2 preview verbatim 2026-04-28 evening after I drifted to "Possible
 * match" without explicit re-confirmation):
 *
 *   Tier 1 — confidence ≥ LLM_TIER1 (0.85): silent auto-bind chip
 *     "📎 Bound to {top.title} · {pct}% match · [Confirm] [Change]"
 *   Tier 2 — 0.45 ≤ confidence < 0.85: soft MCQ radio list
 *     "📎 Related to one of these?                   [×]"
 *     "   ○ {candidate[0].title}        87%"
 *     "   ○ {candidate[1].title}        52%   (up to 5)"
 *     "   ○ None of these"
 *     Each radio is clickable — click binds (or rejects). No separate
 *     Confirm button at this tier; selection IS the action.
 *   Tier 3 — confidence < 0.45 OR no candidates:
 *     If user description had bullets / deadline-token keywords, show
 *     ONE quiet grey line: "Still learning from your patterns."
 *     Otherwise render nothing.
 *
 * Plus four kill-switch render conditions (return null):
 *   - llm_parse_status not 'enriched' (excl. quiet hint while pending)
 *   - llm_binding_rejected_at != null (user said no)
 *   - deadline_match_source NOT IN (null, 'parser_auto') — user owns it
 *   - llm_inferred_deadline_id == task.deadline_id — already bound, no question
 *
 * Per feedback_trust_copy_register memory: drop numeric percentage at
 * Tier 2 hedged framing ("Possible match" not "92% match"). Keep
 * percentage at Tier 1 high confidence (it's a credibility signal, not
 * false precision).
 *
 * Per feedback_dismiss_not_mute memory: ship 3 actions max — no
 * permanent user-level mute. [Confirm] / [Not relevant] / [Dismiss this
 * once]. Tier 4 manual override stays via the existing deadline picker
 * flow (NewTaskModal); not duplicated here.
 *
 * Per docs/manifesto_alignment_audit_2026_04_28.md: every chip
 * impression writes a reflection_view_log row (NOT YET WIRED — backend
 * /reflection_view endpoints exist; this commit logs to the DB via
 * the chip-action endpoints. The "no-action dismiss" path is local-state
 * only by design, no log write — it's the "I saw it, ignored it" signal,
 * captured by absence of llm_binding_rejected_at when llm_parse_status
 * is 'enriched' for an old task).
 */
import { useEffect, useState } from "react";
import { Paperclip, Check, X, ChevronDown, ChevronRight } from "lucide-react";

import {
  confirmLlmBinding,
  rejectLlmBinding,
  type TaskRow,
  type LlmDeadlineCandidate,
} from "@/lib/tasks";

const LLM_TIER1 = 0.85;
const LLM_TIER2 = 0.45;
// Bullets / deadline keywords trigger the Tier 3 quiet "still learning"
// fallback — only when the user clearly expected intelligence.
// Tested against title + description (2026-04-28): operator pointed out
// most users won't fill in description, so title-only signals like
// "BCI paper writeup due Friday" must also light the Tier 3 line.
const RICH_DESCRIPTION_RE = /(^[\s]*[-*•·]|due\b|deadline\b|by\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)|\bnext\s+\w+)/im;

function expectsIntelligence(task: { title: string; description: string | null }): boolean {
  const haystack = `${task.title}\n${task.description ?? ""}`;
  return RICH_DESCRIPTION_RE.test(haystack);
}

export interface LlmEnrichmentChipProps {
  task: TaskRow;
  /** Called after a successful confirm/reject so the parent can
   * optimistically update its task list (or refetch). */
  onChanged?: () => void;
}

export function LlmEnrichmentChip({ task, onChanged }: LlmEnrichmentChipProps) {
  const [busy, setBusy] = useState(false);
  const [resolved, setResolved] = useState<"confirmed" | "rejected" | "dismissed" | null>(null);
  const [expanded, setExpanded] = useState(false);

  // Bug Hunt #24 cleanup: without this, the resolved=confirmed ack chip
  // ("Bound. Thanks for confirming.") never clears even after the parent
  // refetches new task data, because resolved is local state checked
  // FIRST in the render dispatch. After 1100ms reset confirmed/rejected
  // so the chip falls through to the post-resolution suppress logic
  // (deadline_match_source != null/parser_auto → returns null cleanly).
  //
  // Bug Hunt #36 (caught in same edit): dismissed must NOT auto-reset.
  // Dismiss = "hide for this session, no DB write" — if we reset it
  // after 1.1s the chip re-appears 1 second later, defeating the
  // dismiss UX. Dismissed persists for the component's lifetime.
  useEffect(() => {
    if (resolved === null || resolved === "dismissed") return;
    const t = setTimeout(() => setResolved(null), 1100);
    return () => clearTimeout(t);
  }, [resolved]);
  const [error, setError] = useState<string | null>(null);

  // ── Pending state with no candidate data → "LyraOS is reading…"
  // When pending but heuristic has pre-populated candidates (operator's
  // 2026-04-28 instant-tier directive), fall through to render the
  // chip immediately. The async LLM may refresh candidates later.
  const hasCandidateData =
    (task.llm_deadline_candidates?.length ?? 0) > 0;
  if (task.llm_parse_status === "pending" && !hasCandidateData) {
    return (
      <div className="text-[10px] text-dust-deep italic">
        LyraOS is reading this…
      </div>
    );
  }

  // ── Kill-switch conditions — no chip at all
  // Note: 'pending' status with candidates falls through (handled above)
  // so the chip can render Tier 1/2/3 from heuristic data while LLM
  // enrichment is still in flight.
  const llmAvailable =
    task.llm_parse_status === "enriched" ||
    (task.llm_parse_status === "pending" && hasCandidateData);
  if (
    !llmAvailable ||
    task.llm_binding_rejected_at !== null ||
    resolved === "rejected" ||
    resolved === "dismissed"
  ) {
    // Tier 3 quiet fallback — only when user wrote something rich + LLM
    // came back empty/low-confidence. Skip if status isn't enriched at
    // all, since "still learning" implies the LLM ran.
    if (
      task.llm_parse_status === "enriched" &&
      (resolved !== "confirmed") &&
      expectsIntelligence(task) &&
      ((task.llm_deadline_match_confidence ?? 0) < LLM_TIER2 ||
        (task.llm_deadline_candidates?.length ?? 0) === 0) &&
      task.llm_binding_rejected_at === null &&
      (task.deadline_match_source === null || task.deadline_match_source === "parser_auto")
    ) {
      return (
        <div className="text-[10px] text-dust-deep italic">
          Still learning from your patterns.
        </div>
      );
    }
    return null;
  }

  // Trust-not-rewrite alternative-suggestion path (2026-04-28 Phase 1).
  // When user/heuristic has bound a deadline AND the LLM enrichment found
  // a stronger alternative, surface it as a soft "possible better match"
  // — never silent rewrite. User clicks [Switch] to rebind, [Keep] to
  // dismiss the suggestion. Trust-positive: explicit choice always.
  if (
    task.deadline_match_source !== null &&
    task.deadline_match_source !== "parser_auto" &&
    task.llm_alternative_suggestion
  ) {
    const alt = task.llm_alternative_suggestion;
    return (
      <ChipShell error={error}>
        <div className="flex flex-wrap items-center gap-1.5">
          <Paperclip className="h-3 w-3 shrink-0" />
          <span className="text-[11px]">
            <span className="text-dust">Possible better match: </span>
            <span className="font-medium text-parchment">{alt.title}</span>
          </span>
        </div>
        <div className="flex items-center gap-1">
          <ChipBtn
            kind="primary"
            label="Switch"
            disabled={busy}
            onClick={async () => {
              setBusy(true); setError(null);
              try {
                await confirmLlmBinding(task.task_id, {
                  acceptedFields: ["deadline"],
                  chosenDeadlineId: alt.deadline_id,
                });
                setResolved("confirmed");
                onChanged?.();
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Switch failed");
              } finally { setBusy(false); }
            }}
            icon={<Check className="h-3 w-3" />}
          />
          <ChipBtn
            kind="ghost"
            label="Keep current"
            disabled={busy}
            onClick={async () => {
              setBusy(true); setError(null);
              try {
                await rejectLlmBinding(task.task_id);
                setResolved("rejected");
                onChanged?.();
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Reject failed");
              } finally { setBusy(false); }
            }}
          />
        </div>
      </ChipShell>
    );
  }

  // User already owns the binding without an alternative suggestion —
  // no question to ask, render nothing.
  if (
    task.deadline_match_source !== null &&
    task.deadline_match_source !== "parser_auto"
  ) {
    return null;
  }

  // LLM's top match IS the existing parser_auto binding — no question to ask
  if (
    task.deadline_id !== null &&
    task.llm_inferred_deadline_id === task.deadline_id
  ) {
    return null;
  }

  // No candidates at all → Tier 3 (quiet line if rich description)
  const candidates = task.llm_deadline_candidates ?? [];
  const top = candidates[0] ?? null;
  const topConfidence = top?.confidence ?? 0;

  if (!top || topConfidence < LLM_TIER2) {
    if (
      expectsIntelligence(task) &&
      resolved !== "confirmed"
    ) {
      return (
        <div className="text-[10px] text-dust-deep italic">
          Still learning from your patterns.
        </div>
      );
    }
    return null;
  }

  // ── Resolved acknowledgment flash
  if (resolved === "confirmed") {
    return (
      <div className="flex items-center gap-1.5 rounded-sm border border-signal/30 bg-signal/5 px-2 py-1 text-[11px] text-signal">
        <Check className="h-3 w-3" />
        <span>Bound. Thanks for confirming.</span>
      </div>
    );
  }

  // ── Tier 1 (high-confidence, single auto-bind chip)
  if (topConfidence >= LLM_TIER1 && top) {
    const pct = Math.round(topConfidence * 100);
    return (
      <ChipShell error={error}>
        <div className="flex flex-wrap items-center gap-1.5">
          <Paperclip className="h-3 w-3 shrink-0" />
          <span className="text-[11px]">
            <span className="text-dust">Bound to </span>
            <span className="font-medium text-parchment">{top.title}</span>
            <span className="ml-1 text-[10px] text-dust-deep">· {pct}% match</span>
          </span>
        </div>
        <div className="flex items-center gap-1">
          <ChipBtn
            kind="primary"
            label="Confirm"
            disabled={busy}
            onClick={async () => {
              setBusy(true); setError(null);
              try {
                await confirmLlmBinding(task.task_id, {
                  acceptedFields: ["deadline"],
                });
                setResolved("confirmed");
                onChanged?.();
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Confirm failed");
              } finally { setBusy(false); }
            }}
            icon={<Check className="h-3 w-3" />}
          />
          {candidates.length > 1 && (
            <ChipBtn
              kind="secondary"
              label="Change"
              disabled={busy}
              onClick={() => setExpanded((v) => !v)}
              icon={expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            />
          )}
          <ChipBtn
            kind="ghost"
            label="Not relevant"
            disabled={busy}
            onClick={async () => {
              setBusy(true); setError(null);
              try {
                await rejectLlmBinding(task.task_id);
                setResolved("rejected");
                onChanged?.();
              } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Reject failed");
              } finally { setBusy(false); }
            }}
          />
          <button
            type="button"
            aria-label="Dismiss this once"
            disabled={busy}
            onClick={() => setResolved("dismissed")}
            className="text-dust-deep transition-colors hover:text-parchment disabled:opacity-50"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
        {expanded && candidates.length > 1 && (
          <CandidateList
            candidates={candidates.slice(1)}
            disabled={busy}
            onPick={(d) => onPickCandidate(d)}
          />
        )}
      </ChipShell>
    );
  }

  // ── Tier 2 (medium-confidence, soft MCQ radio list)
  // Operator-approved copy 2026-04-28: question header + radio list.
  // Each radio click is the action — no separate Confirm button.
  // Percentages stay on each candidate (operator's preview shows them);
  // they help disambiguate. Dismiss × is the only button — local-state
  // hide, no DB write, per feedback_dismiss_not_mute. "None of these"
  // is the model-teaching reject signal (calls /reject-llm-binding).
  return (
    <ChipShell error={error}>
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5">
          <Paperclip className="h-3 w-3 shrink-0" />
          <span className="text-[11px] font-medium text-parchment">
            Related to one of these?
          </span>
        </div>
        <button
          type="button"
          aria-label="Dismiss this once"
          disabled={busy}
          onClick={() => setResolved("dismissed")}
          className="text-dust-deep transition-colors hover:text-parchment disabled:opacity-50"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
      <div className="flex flex-col gap-0.5 pt-0.5">
        {candidates.map((c) => (
          <button
            key={c.deadline_id}
            type="button"
            disabled={busy}
            onClick={() => onPickCandidate(c)}
            className="flex items-center justify-between gap-2 rounded-sm px-1.5 py-1 text-left text-[11px] text-dust transition-colors hover:bg-void-2/60 hover:text-parchment disabled:opacity-50"
          >
            <span className="flex items-center gap-1.5 truncate">
              <span className="text-dust-deep">○</span>
              <span className="truncate">{c.title}</span>
            </span>
            <span className="shrink-0 text-[10px] text-dust-deep">
              {Math.round(c.confidence * 100)}%
            </span>
          </button>
        ))}
        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true); setError(null);
            try {
              await rejectLlmBinding(task.task_id);
              setResolved("rejected");
              onChanged?.();
            } catch (e: unknown) {
              setError(e instanceof Error ? e.message : "Reject failed");
            } finally { setBusy(false); }
          }}
          className="flex items-center gap-1.5 rounded-sm px-1.5 py-1 text-left text-[11px] text-dust-deep transition-colors hover:bg-void-2/60 hover:text-dust disabled:opacity-50"
        >
          <span>○</span>
          <span>None of these</span>
        </button>
      </div>
    </ChipShell>
  );

  async function onPickCandidate(d: LlmDeadlineCandidate) {
    setBusy(true);
    setError(null);
    try {
      await confirmLlmBinding(task.task_id, {
        acceptedFields: ["deadline"],
        chosenDeadlineId: d.deadline_id,
      });
      setResolved("confirmed");
      onChanged?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bind failed");
    } finally {
      setBusy(false);
    }
  }
}

function ChipShell({ error, children }: { error: string | null; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-sm border border-ember/30 bg-ember/5 px-2 py-1.5 text-[11px] text-ember">
      <div className="flex flex-wrap items-center justify-between gap-2">{children}</div>
      {error && <div className="text-[10px] text-ember-deep">{error}</div>}
    </div>
  );
}

function ChipBtn({
  kind, label, disabled, onClick, icon,
}: {
  kind: "primary" | "secondary" | "ghost";
  label: string;
  disabled: boolean;
  onClick: () => void | Promise<void>;
  icon?: React.ReactNode;
}) {
  const base = "inline-flex h-6 items-center gap-1 rounded-sm px-2 text-[11px] transition-colors disabled:opacity-50";
  const variant =
    kind === "primary"
      ? "border border-signal/40 bg-signal/10 font-medium text-signal hover:bg-signal/20 hover:text-signal-neon"
      : kind === "secondary"
        ? "border border-hairline bg-void-2/60 text-dust hover:bg-void-2 hover:text-parchment"
        : "text-dust-deep hover:text-parchment";
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${base} ${variant}`}>
      {icon}
      {label}
    </button>
  );
}

function CandidateList({
  candidates, disabled, onPick,
}: {
  candidates: LlmDeadlineCandidate[];
  disabled: boolean;
  onPick: (d: LlmDeadlineCandidate) => void;
}) {
  return (
    <div className="flex flex-col gap-1 pt-1 border-t border-hairline">
      {candidates.map((c) => (
        <button
          key={c.deadline_id}
          type="button"
          disabled={disabled}
          onClick={() => onPick(c)}
          className="flex items-center justify-between gap-2 rounded-sm px-1.5 py-1 text-left text-[11px] text-dust hover:bg-void-2/60 hover:text-parchment disabled:opacity-50"
        >
          <span className="truncate">{c.title}</span>
          <span className="shrink-0 text-[10px] text-dust-deep">{Math.round(c.confidence * 100)}%</span>
        </button>
      ))}
    </div>
  );
}
