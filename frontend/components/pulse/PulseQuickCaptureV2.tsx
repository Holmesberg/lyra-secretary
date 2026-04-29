"use client";
/**
 * PulseQuickCaptureV2 — inline quick-capture footer matching the
 * reference image. Text input on the left, action chips on the right.
 *
 * v1 was a link-only CTA. v2 inlines the input but routes to the
 * existing brain-dump flow on submit (passes the text via the URL
 * `?seed=...` query so /today's brain-dump can pre-populate). Doesn't
 * try to parse inline — that'd duplicate the brain-dump multi-parse +
 * auto-bind state machine.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FileText, Flag, Link as LinkIcon, Mic } from "lucide-react";

export function PulseQuickCaptureV2() {
  const router = useRouter();
  const [text, setText] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) {
      router.push("/today");
      return;
    }
    router.push(`/today?seed=${encodeURIComponent(trimmed)}`);
  }

  return (
    <form
      onSubmit={submit}
      className="terminal-panel flex flex-wrap items-center gap-3 px-5 py-3"
    >
      <span className="font-display text-[10px] font-medium uppercase tracking-macro text-signal/80">
        <span className="opacity-50">[ </span>
        Quick capture
        <span className="opacity-50"> ]</span>
      </span>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Brain dump anything — Lyra parses, sorts, and binds it."
        className="min-w-[200px] flex-1 border-0 bg-transparent px-2 py-1 text-sm text-parchment placeholder:text-dust-deep focus:outline-none focus:ring-0"
      />
      <div className="flex items-center gap-1.5 text-dust-deep">
        <ChipButton icon={FileText} label="Tasks" />
        <ChipButton icon={Flag} label="Deadlines" />
        <ChipButton icon={LinkIcon} label="Link" />
        <ChipButton icon={Mic} label="Voice" disabled />
      </div>
      <button
        type="submit"
        className="rounded-sm border border-signal/40 bg-signal/15 px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon"
      >
        Capture →
      </button>
    </form>
  );
}

function ChipButton({
  icon: Icon,
  label,
  disabled,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      title={disabled ? `${label} (coming soon)` : label}
      className={`flex items-center gap-1.5 rounded-sm border border-hairline bg-void-2/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors ${
        disabled
          ? "cursor-not-allowed text-dust-deep/50"
          : "text-dust hover:border-signal/40 hover:text-signal"
      }`}
    >
      <Icon className="h-3 w-3" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
