"use client";
/**
 * Archetype survey overlay — 29-item instrument battery.
 *
 * Fires between ConsentModal and TutorialOverlay for post-launch users
 * (per layout.tsx gate). Also reachable from the Settings retrofit
 * banner as an inline-modal for pre-launch users.
 *
 * Flow: 4 screens (one per instrument), linear navigation. Skip button
 * on every screen. Submit on final screen posts to
 * /v1/users/me/archetype/survey; Skip posts to /archetype/skip.
 *
 * Design choices (ultrathought):
 * - Radio-button option rows, not sliders. Sliders on Likert invite
 *   mid-range clustering and add cognitive load for people who don't
 *   naturally translate a position on a track to "fairly agree."
 * - Items shown one-per-scroll with a persistent progress rail. No
 *   "next item" auto-advance — user clicks an answer, sees the choice
 *   reflected, then explicitly clicks Next. Prevents accidental
 *   double-tap skips on mobile.
 * - Reverse-keying is invisible to the user. All BSCS items read
 *   naturally in their original direction ("I have trouble
 *   concentrating" answered as Disagree maps to high self-control
 *   via server-side (6-raw) inversion).
 * - Skip is always visible, one tap, confirmation dialog on click.
 *   Per Rule 13 skip-path, defaults user to Diffuse Average (1.30)
 *   which is the population midpoint — better than flat 1.0.
 * - No identity-framing — survey doesn't say "this will classify you
 *   as a Procrastinator." Reveal is v1.1 (VT-25 gate).
 *
 * Research note: tour exposure logged to reflection_view_log as
 * `reflection_type='archetype_survey'` for future VT-21 stratification
 * (does survey exposure correlate with retention?). Not wired in v1;
 * the survey is submission-telemetered only.
 */
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import {
  BFI_C_ITEMS,
  BSCS_ITEMS,
  GP_ITEMS,
  MEQ_ITEMS,
  skipArchetypeSurvey,
  submitArchetypeSurvey,
  type SurveyItem,
} from "@/lib/archetype";
import { queryKeys } from "@/lib/query-keys";

type InstrumentSection = {
  key: "meq" | "bfi_c" | "bscs" | "gp";
  title: string;
  subtitle: string;
  items: SurveyItem[];
};

const SECTIONS: InstrumentSection[] = [
  {
    key: "meq",
    title: "Sleep rhythm",
    subtitle:
      "When you feel most alert vs. most tired. Five questions, one minute.",
    items: MEQ_ITEMS,
  },
  {
    key: "bfi_c",
    title: "Work approach",
    subtitle: "Two questions about how you see yourself getting things done.",
    items: BFI_C_ITEMS,
  },
  {
    key: "bscs",
    title: "Self-control",
    subtitle:
      "Thirteen statements. Rate how much each matches you — there are no right answers.",
    items: BSCS_ITEMS,
  },
  {
    key: "gp",
    title: "Task starts",
    subtitle:
      "Nine statements about how you handle things that need doing. Almost there.",
    items: GP_ITEMS,
  },
];

export interface ArchetypeSurveyProps {
  /** Called when survey completes (answered fully) or is skipped.
   *  Parent refetches /me to pick up the new archetype_id. */
  onFinished: () => void;
}

export function ArchetypeSurvey({ onFinished }: ArchetypeSurveyProps) {
  // Answers indexed by item.id → chosen weight (1..5 depending on scale)
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [sectionIdx, setSectionIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [confirmSkip, setConfirmSkip] = useState(false);

  // After a successful survey submit / skip, the user's archetype_id
  // changes — which means every bias_factor lookup needs a fresh blend
  // AND /insights should re-render with the new prior. Invalidate all
  // archetype-dependent query keys so any open tab auto-refetches the
  // moment the user finishes. This is the "self-update" behavior the
  // operator asked for 2026-04-23.
  const qc = useQueryClient();
  function invalidateArchetypeDependent() {
    qc.invalidateQueries({ queryKey: ["insights"] });
    qc.invalidateQueries({ queryKey: queryKeys.me });
    // Bias-factor lookups are per (category, tod, planned) — we don't
    // know every key variant open tabs might have cached. Broad match
    // on the first key segment so every cached lookup invalidates.
    qc.invalidateQueries({
      predicate: (q) =>
        typeof q.queryKey[0] === "string" &&
        (q.queryKey[0] as string).startsWith("bias_factor"),
    });
  }

  const section = SECTIONS[sectionIdx];
  const totalItems = SECTIONS.reduce((s, x) => s + x.items.length, 0);
  const answeredCount = Object.keys(answers).length;
  const isFinalSection = sectionIdx === SECTIONS.length - 1;
  const sectionComplete = section.items.every((it) => answers[it.id] != null);

  useEffect(() => {
    // Reset error on navigation.
    setErr(null);
  }, [sectionIdx]);

  function setAnswer(itemId: string, value: number) {
    setAnswers((a) => ({ ...a, [itemId]: value }));
  }

  async function handleNext() {
    if (!isFinalSection) {
      setSectionIdx((i) => i + 1);
      return;
    }
    // Final section → submit
    setBusy(true);
    setErr(null);
    try {
      await submitArchetypeSurvey({
        meq: MEQ_ITEMS.map((it) => answers[it.id]),
        bfi_c: BFI_C_ITEMS.map((it) => answers[it.id]),
        bscs: BSCS_ITEMS.map((it) => answers[it.id]),
        gp: GP_ITEMS.map((it) => answers[it.id]),
      });
      invalidateArchetypeDependent();
      onFinished();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't submit — try again.");
      setBusy(false);
    }
  }

  async function handleSkip() {
    setBusy(true);
    setErr(null);
    try {
      await skipArchetypeSurvey();
      invalidateArchetypeDependent();
      onFinished();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't record skip — try again.");
      setBusy(false);
    }
  }

  const overallPct = Math.round((answeredCount / totalItems) * 100);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="archetype-survey-title"
      className="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-void/85 p-4 backdrop-blur-sm md:p-8"
    >
      <div className="w-full max-w-2xl rounded-sm border border-hairline-signal/30 bg-void-2 p-5 shadow-xl md:p-8">
        {/* Overall progress rail */}
        <div className="mb-5 flex items-center gap-3">
          <div className="flex-1">
            <div className="mb-1 flex items-center justify-between text-[11px] text-dust-deep">
              <span>
                Step {sectionIdx + 1} of {SECTIONS.length} · {section.title}
              </span>
              <span>
                {answeredCount} / {totalItems}
              </span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-void">
              <div
                className="h-full bg-signal transition-all"
                style={{ width: `${overallPct}%` }}
              />
            </div>
          </div>
          {!confirmSkip && (
            <button
              type="button"
              onClick={() => setConfirmSkip(true)}
              disabled={busy}
              className="whitespace-nowrap text-[11px] text-dust-deep underline-offset-2 transition-colors hover:text-parchment hover:underline disabled:opacity-50"
            >
              Skip survey
            </button>
          )}
        </div>

        {/* Intro on first screen */}
        {sectionIdx === 0 && (
          <div className="mb-5 rounded-sm border border-hairline bg-void/40 p-3 text-xs leading-relaxed text-dust">
            <p className="mb-1 font-medium text-parchment">
              A few quick questions — about 4 minutes.
            </p>
            <p>
              These help Lyra start with a sense of how you tend to work
              — morning vs evening, how you approach things — so the
              first time estimates aren&apos;t blind guesses. After a
              handful of sessions, Lyra stops leaning on this and starts
              learning from how you actually move through your day. Skip
              anytime: it just means a slower start.
            </p>
          </div>
        )}

        {/* Section header */}
        <h2
          id="archetype-survey-title"
          className="mb-1 text-lg font-semibold tracking-tight text-parchment"
        >
          {section.title}
        </h2>
        <p className="mb-5 text-xs text-dust">{section.subtitle}</p>

        {/* Items */}
        <div className="flex flex-col gap-5">
          {section.items.map((item) => (
            <ItemRow
              key={item.id}
              item={item}
              selected={answers[item.id] ?? null}
              onSelect={(v) => setAnswer(item.id, v)}
              disabled={busy}
            />
          ))}
        </div>

        {err && (
          <p className="mt-4 text-xs text-ember">{err}</p>
        )}

        {/* Skip confirmation */}
        {confirmSkip && (
          <div className="mt-5 rounded-sm border border-ember/40 bg-ember/5 p-3 text-xs text-ember">
            <p className="mb-2">
              Skip for now? Lyra will use a generic starting point and
              learn from your sessions. You can take the survey from
              Settings whenever — no rush.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSkip}
                disabled={busy}
                className="inline-flex h-8 items-center rounded-sm border border-ember/40 bg-ember/10 px-3 text-[11px] font-medium text-ember transition-colors hover:bg-ember/20 disabled:opacity-50"
              >
                {busy && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Yes, skip
              </button>
              <button
                type="button"
                onClick={() => setConfirmSkip(false)}
                disabled={busy}
                className="rounded-sm px-3 py-1 text-[11px] text-dust transition-colors hover:text-parchment disabled:opacity-50"
              >
                Keep taking it
              </button>
            </div>
          </div>
        )}

        {/* Nav */}
        <div className="mt-6 flex items-center justify-between gap-3">
          <div>
            {sectionIdx > 0 && (
              <button
                type="button"
                onClick={() => setSectionIdx((i) => Math.max(0, i - 1))}
                disabled={busy}
                className="rounded-sm border border-hairline-signal/40 bg-transparent px-3 py-1.5 text-xs text-parchment transition-colors hover:bg-signal/5 hover:text-signal disabled:opacity-50"
              >
                Back
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={handleNext}
            disabled={busy || !sectionComplete}
            className="inline-flex items-center gap-1 rounded-sm border border-signal/40 bg-signal/10 px-4 py-1.5 text-xs font-medium text-signal transition-colors hover:bg-signal/20 hover:text-signal-neon disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy && <Loader2 className="h-3 w-3 animate-spin" />}
            {isFinalSection ? "Finish + start" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ItemRow({
  item,
  selected,
  onSelect,
  disabled,
}: {
  item: SurveyItem;
  selected: number | null;
  onSelect: (value: number) => void;
  disabled: boolean;
}) {
  return (
    <div>
      <p className="mb-2 text-sm text-parchment">{item.text}</p>
      <div className="flex flex-col gap-1">
        {item.options.map((opt) => {
          const active = selected === opt.value;
          return (
            <button
              type="button"
              key={opt.value}
              onClick={() => onSelect(opt.value)}
              disabled={disabled}
              aria-pressed={active}
              className={
                active
                  ? "rounded-sm border border-signal/60 bg-signal/10 px-3 py-2 text-left text-[13px] text-signal transition-colors"
                  : "rounded-sm border border-hairline bg-void/40 px-3 py-2 text-left text-[13px] text-dust transition-colors hover:border-signal/40 hover:bg-signal/5 hover:text-parchment disabled:opacity-50"
              }
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
