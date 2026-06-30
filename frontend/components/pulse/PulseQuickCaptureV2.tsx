"use client";
/**
 * PulseQuickCaptureV2 - inline quick-capture command bar for /pulse v2.
 *
 * One instance only. It lives near the top of Pulse so capture is reachable
 * before planning/recovery review, and it shrinks while a timer is active so
 * the current session remains the visual center.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Flag, Link as LinkIcon, Mic } from "lucide-react";
import { BrainDumpQuickModal } from "@/components/pulse/BrainDumpQuickModal";
import { getStopwatchStatus, type StopwatchStatus } from "@/lib/tasks";
import { queryKeys } from "@/lib/query-keys";

export function PulseQuickCaptureV2() {
  const statusQ = useQuery<StopwatchStatus>({
    queryKey: queryKeys.stopwatchStatus,
    queryFn: getStopwatchStatus,
    refetchInterval: 5_000,
    refetchOnWindowFocus: true,
  });

  const [text, setText] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [seedText, setSeedText] = useState("");
  const [bannerCount, setBannerCount] = useState<{
    tasks: number;
    deadlines: number;
  } | null>(null);

  const compact = !!statusQ.data?.active;

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
    setTimeout(() => setBannerCount(null), 4000);
  }

  return (
    <>
      <form
        id="quick-capture"
        onSubmit={openModal}
        className={`terminal-panel flex scroll-mt-6 flex-wrap items-center gap-3 ${
          compact ? "px-4 py-2" : "px-5 py-3"
        }`}
      >
        <span className="font-display text-[10px] font-medium uppercase tracking-macro text-signal/80">
          <span className="opacity-50">[ </span>
          {compact ? "Capture" : "Quick capture"}
          <span className="opacity-50"> ]</span>
        </span>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            compact
              ? "Capture a thought without breaking the session."
              : "Brain dump anything - Lyra parses, sorts, and binds it."
          }
          className={`min-w-[200px] flex-1 border-0 bg-transparent px-2 text-parchment placeholder:text-dust-deep focus:outline-none focus:ring-0 ${
            compact ? "py-0.5 text-xs" : "py-1 text-sm"
          }`}
        />
        <div
          className={`items-center gap-1.5 text-dust-deep ${
            compact ? "hidden xl:flex" : "flex"
          }`}
        >
          <ChipButton icon={FileText} label="Tasks" onClick={openModal} />
          <ChipButton icon={Flag} label="Deadlines" onClick={openModal} />
          <ChipButton icon={LinkIcon} label="Link" disabled />
          <ChipButton icon={Mic} label="Voice" disabled />
        </div>
        <button
          type="submit"
          className={`rounded-sm border border-signal/40 bg-signal/15 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon ${
            compact ? "px-3 py-1" : "px-3.5 py-1.5"
          }`}
        >
          Capture -&gt;
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
