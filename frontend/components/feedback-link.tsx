"use client";
/**
 * Feedback widget link (alembic 040, 2026-04-28).
 *
 * Tiny grey link that opens the FeedbackModal. Drop wherever the user
 * email is shown — Settings page, user-dropdown, etc. Self-contained
 * (manages its own modal state).
 *
 * Operator request 2026-04-28: "tiny 'report bug' or 'feedback to
 * improve LyraOS' in grey beneath the email address."
 */
import { useState } from "react";
import { FeedbackModal } from "./feedback-modal";

interface Props {
  /** Optional className override for layout-specific tweaking. */
  className?: string;
  /** Defaults to the operator-approved phrasing. */
  label?: string;
}

export function FeedbackLink({
  className = "",
  label = "Report a bug · Send feedback",
}: Props) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          "rounded-sm text-[10px] font-medium text-white underline-offset-2 transition-colors hover:text-signal hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/70 " +
          className
        }
      >
        {label}
      </button>
      <FeedbackModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
