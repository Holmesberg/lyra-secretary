"use client";
/**
 * PulseQuickCaptureV2 — inline quick-capture footer for /pulse v2.
 *
 * Reference image vocabulary: text input on the left + action chips
 * + a Capture button. Operator request 2026-04-29 night: clicking
 * Capture opens the brain-dump modal (not a route nav) so the magic
 * fires more often without a page change. Seed text from the input
 * pre-populates the modal.
 */
import { useState } from "react";
import { FileText, Flag, Link as LinkIcon, Mic } from "lucide-react";
import { BrainDumpQuickModal } from "@/components/pulse/BrainDumpQuickModal";

export function PulseQuickCaptureV2() {
  const [text, setText] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [seedText, setSeedText] = useState("");
  const [bannerCount, setBannerCount] = useState<{
    tasks: number;
    deadlines: number;
  } | null>(null);

  function openModal(e?: React.FormEvent) {
    e?.preventDefault();
    setSeedText(text);
    setModalOpen(true);
  }

  function handleCompleted(counts: {
    tasks: number;
    deadlines: number;
    bindings: number;
  }) {
    setBannerCount({ tasks: counts.tasks, deadlines: counts.deadlines });
    setText("");
    // Auto-clear the success banner after 4s.
    setTimeout(() => setBannerCount(null), 4000);
  }

  return (
    <>
      <form
        onSubmit={openModal}
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
          <ChipButton icon={FileText} label="Tasks" onClick={openModal} />
          <ChipButton icon={Flag} label="Deadlines" onClick={openModal} />
          <ChipButton icon={LinkIcon} label="Link" disabled />
          <ChipButton icon={Mic} label="Voice" disabled />
        </div>
        <button
          type="submit"
          className="rounded-sm border border-signal/40 bg-signal/15 px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon"
        >
          Capture →
        </button>
      </form>

      {bannerCount && (
        <div
          role="status"
          className="rounded-sm border border-signal/40 bg-signal/5 px-4 py-2 text-[12px] text-signal"
        >
          Locked in.{" "}
          {bannerCount.tasks > 0 && (
            <>
              <span className="font-display">{bannerCount.tasks}</span>{" "}
              {bannerCount.tasks === 1 ? "task" : "tasks"}
            </>
          )}
          {bannerCount.tasks > 0 && bannerCount.deadlines > 0 && " + "}
          {bannerCount.deadlines > 0 && (
            <>
              <span className="font-display">{bannerCount.deadlines}</span>{" "}
              {bannerCount.deadlines === 1 ? "deadline" : "deadlines"}
            </>
          )}{" "}
          captured.
        </div>
      )}

      <BrainDumpQuickModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        seedText={seedText}
        onCompleted={handleCompleted}
      />
    </>
  );
}

function ChipButton({
  icon: Icon,
  label,
  disabled,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
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
