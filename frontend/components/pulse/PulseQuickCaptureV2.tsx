"use client";
/**
 * PulseQuickCaptureV2 - inline quick-capture command bar for /pulse v2.
 *
 * One instance only. It lives near the top of Pulse so capture is reachable
 * before planning/recovery review, and it shrinks while a timer is active so
 * the current session remains the visual center.
 */
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarDays,
  FileText,
  Flag,
  Gauge,
  Link as LinkIcon,
  Mic,
  Table2,
  X,
} from "lucide-react";
import { BrainDumpQuickModal } from "@/components/pulse/BrainDumpQuickModal";
import type { BrainDumpCommitResponse } from "@/lib/brain-dump";
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
  const [captureResult, setCaptureResult] =
    useState<BrainDumpCommitResponse | null>(null);

  const compact = !!statusQ.data?.active;

  function openModal(e?: React.FormEvent) {
    e?.preventDefault();
    setCaptureResult(null);
    setSeedText(text);
    setModalOpen(true);
  }

  function handleCompleted(result: BrainDumpCommitResponse) {
    setCaptureResult(result);
    setText("");
  }

  const outcomes = captureResult?.outcomes ?? [];
  const reusedCount = outcomes.filter((row) => row.status === "reused").length;
  const rejectedCount = outcomes.filter((row) => row.status === "rejected").length;
  const failedCount = outcomes.filter((row) => row.status === "failed").length;
  const hasAcceptedResult = Boolean(
    captureResult &&
      (captureResult.tasks_created > 0 ||
        captureResult.deadlines_created > 0 ||
        reusedCount > 0),
  );

  return (
    <>
      <form
        id="quick-capture"
        data-testid="pulse-quick-capture"
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
          data-testid="pulse-quick-capture-input"
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            compact
              ? "Capture a thought without breaking the session."
              : "Brain dump anything - LyraOS parses, sorts, and binds it."
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
          data-testid="pulse-quick-capture-submit"
          type="submit"
          className={`rounded-sm border border-signal/40 bg-signal/15 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/25 hover:text-signal-neon ${
            compact ? "px-3 py-1" : "px-3.5 py-1.5"
          }`}
        >
          Capture -&gt;
        </button>
      </form>

      {captureResult && (
        <div
          role="status"
          data-testid="brain-dump-capture-result"
          className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-sm border border-signal/40 bg-signal/5 px-4 py-3 text-[12px] text-signal"
        >
          <div className="min-w-[220px] flex-1">
            <span className="font-medium text-parchment">Capture complete.</span>{" "}
            {captureResult.tasks_created} task
            {captureResult.tasks_created === 1 ? "" : "s"} and{" "}
            {captureResult.deadlines_created} deadline
            {captureResult.deadlines_created === 1 ? "" : "s"} created
            {reusedCount > 0 && `; ${reusedCount} existing obligation reused`}
            {rejectedCount > 0 && `; ${rejectedCount} item rejected`}
            {failedCount > 0 && `; ${failedCount} item failed`}.
          </div>
          {hasAcceptedResult && (
            <nav
              aria-label="Review captured work"
              className="flex flex-wrap items-center gap-2"
            >
              <CaptureDestination
                href="/pulse#pressure-map"
                label="Open Pressure Map"
                icon={Gauge}
              />
              {captureResult.tasks_created > 0 && (
                <CaptureDestination href="/table" label="Review tasks" icon={Table2} />
              )}
              {(captureResult.deadlines_created > 0 || reusedCount > 0) && (
                <CaptureDestination
                  href="/deadlines"
                  label="Review deadlines"
                  icon={Flag}
                />
              )}
              <CaptureDestination
                href="/calendar"
                label="Open calendar"
                icon={CalendarDays}
              />
            </nav>
          )}
          <button
            type="button"
            aria-label="Dismiss capture result"
            title="Dismiss capture result"
            onClick={() => setCaptureResult(null)}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-hairline text-dust transition-colors hover:border-signal/40 hover:text-parchment"
          >
            <X className="h-3.5 w-3.5" />
          </button>
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

function CaptureDestination({
  href,
  label,
  icon: Icon,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Link
      href={href}
      className="inline-flex h-8 items-center gap-1.5 rounded-sm border border-signal/30 bg-void-2/40 px-2.5 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:border-signal/60 hover:bg-signal/10"
    >
      <Icon className="h-3 w-3" />
      {label}
      <ArrowRight className="h-3 w-3" />
    </Link>
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
