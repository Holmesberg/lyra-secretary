"use client";
/**
 * QuickCaptureStrip — persistent footer-strip CTA on /pulse that
 * routes to the existing brain-dump flow.
 *
 * Doesn't open an inline composer (that'd duplicate brain-dump's
 * multi-parse + auto-bind state machine). Just a link styled as a
 * persistent capture target so the user always knows where to dump
 * something without scrolling back to /today. Operator can later
 * decide whether to inline a composer.
 */
import Link from "next/link";

export function QuickCaptureStrip() {
  return (
    <Link
      href="/today"
      className="group flex items-center gap-3 rounded-sm border border-hairline bg-void-2/40 px-5 py-3 transition-colors hover:border-signal/40 hover:bg-void-2/70"
    >
      <span
        aria-hidden
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-signal/30 bg-signal/10 font-mono text-sm text-signal transition-all group-hover:border-signal-neon group-hover:text-signal-neon"
      >
        +
      </span>
      <div className="flex-1">
        <div className="font-display text-[11px] font-medium uppercase tracking-macro text-dust group-hover:text-parchment">
          <span className="opacity-50">[ </span>
          Quick capture
          <span className="opacity-50"> ]</span>
        </div>
        <div className="text-xs text-dust-deep">
          Brain dump anything — Lyra parses, sorts, and binds it.
        </div>
      </div>
      <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep group-hover:text-signal">
        Open →
      </span>
    </Link>
  );
}
