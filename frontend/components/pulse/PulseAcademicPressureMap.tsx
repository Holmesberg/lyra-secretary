"use client";

import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  ShieldQuestion,
} from "lucide-react";
import type {
  AcademicPressureItem,
  AcademicPressureMapResponse,
} from "@/lib/academic";

export interface PulseAcademicPressureMapProps {
  pressure: AcademicPressureMapResponse | null;
  loading?: boolean;
}

function fmtHours(lowMinutes: number, highMinutes: number): string {
  const low = Math.round(lowMinutes / 30) / 2;
  const high = Math.round(highMinutes / 30) / 2;
  if (low === high) return `${low}h`;
  return `${low}-${high}h`;
}

function fmtDue(days: number): string {
  if (days < 0) return "overdue";
  if (days < 1) return "due today";
  if (days < 2) return "due tomorrow";
  return `in ${Math.round(days)}d`;
}

function fmtTiming(item: AcademicPressureItem): string {
  const isTask = item.source_class === "lyra_task";
  const days = item.days_until_due;
  if (!isTask) return fmtDue(days);
  if (days < 0) return "started";
  if (days < 1) return "scheduled today";
  if (days < 2) return "scheduled tomorrow";
  return `scheduled in ${Math.round(days)}d`;
}

function pressureClass(item: AcademicPressureItem): string {
  if (item.pressure_level === "overdue") return "border-ember/50 bg-ember/10";
  if (item.pressure_level === "high") return "border-ember/30 bg-ember/5";
  return "border-hairline bg-void-2/40";
}

function fmtTrust(trust: AcademicPressureItem["trust_state"]): string {
  if (trust === "verified_reachable") return "source reachable";
  if (trust === "requires_user_confirmation") return "needs confirmation";
  if (trust === "verified_exact") return "source verified";
  return trust.replaceAll("_", " ");
}

export function PulseAcademicPressureMap({
  pressure,
  loading = false,
}: PulseAcademicPressureMapProps) {
  const items = pressure?.items.slice(0, 4) ?? [];
  const hasItems = items.length > 0;

  return (
    <div className="terminal-panel flex h-full flex-col p-5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <div className="font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          <span className="opacity-50">[ </span>
          Academic pressure
          <span className="opacity-50"> ]</span>
        </div>
        <span className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
          {pressure ? `${pressure.horizon_days}d map` : "14d map"}
        </span>
      </div>

      {loading ? (
        <div className="flex flex-1 items-center text-sm text-dust">
          Reading academic load...
        </div>
      ) : !pressure ? (
        <div className="flex flex-1 items-center text-sm text-dust">
          Pressure map unavailable.
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-signal/30 bg-signal/10 text-signal">
              <CalendarClock size={16} />
            </div>
            <div className="min-w-0">
              <p className="text-[15px] leading-snug text-parchment">
                {pressure.pressure_summary || pressure.headline}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
                {fmtHours(
                  pressure.estimated_low_minutes,
                  pressure.estimated_high_minutes
                )}{" "}
                visible load / {pressure.source_summary.external_obligation_count} external /{" "}
                {pressure.source_summary.native_obligation_count} native /{" "}
                {pressure.source_summary.academic_task_count} academic /{" "}
                {pressure.source_summary.study_task_count} study
              </p>
            </div>
          </div>

          {pressure.compression_points.length > 0 && (
            <div className="mb-3 rounded-sm border border-hairline bg-void-2/30 px-3 py-2">
              <div className="mb-1 flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                <ShieldQuestion size={12} className="text-signal" />
                Why the week feels compressed
              </div>
              <p className="text-[12px] leading-snug text-dust">
                {pressure.compression_points[0].detail}
              </p>
            </div>
          )}

          {hasItems ? (
            <ul className="flex flex-col gap-2">
              {items.map((item) => (
                <li
                  key={item.obligation_id}
                  className={`rounded-sm border px-3 py-2 ${pressureClass(item)}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] text-parchment">
                        {item.title}
                      </p>
                      <p className="mt-1 font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                        {item.obligation_type} / {item.complexity_tier} /{" "}
                        {fmtTrust(item.trust_state)}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="font-display text-[13px] text-signal">
                        {fmtHours(
                          item.estimate.low_minutes,
                          item.estimate.high_minutes
                        )}
                      </p>
                      <p className="font-mono text-[9px] uppercase tracking-widest text-dust-deep">
                        {fmtTiming(item)}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-1 items-center gap-3 rounded-sm border border-hairline bg-void-2/40 px-3 py-4 text-sm text-dust">
              <CheckCircle2 size={16} className="shrink-0 text-signal" />
              No active academic obligations in this window.
            </div>
          )}

          {pressure.recovery_options.length > 0 && (
            <div className="mt-3 rounded-sm border border-signal/20 bg-signal/5 px-3 py-2">
              <div className="mb-1 flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-signal">
                <ClipboardCheck size={12} />
                Next recovery option
              </div>
              <p className="text-[12px] font-medium text-parchment">
                {pressure.recovery_options[0].label}
              </p>
              <p className="mt-1 text-[11px] leading-snug text-dust">
                {pressure.recovery_options[0].detail}
              </p>
            </div>
          )}

          <div className="mt-3 flex items-start gap-2 border-t border-hairline pt-3 text-[11px] leading-relaxed text-dust">
            <AlertTriangle size={14} className="mt-0.5 shrink-0 text-ember" />
            <p>
              Ranges are structure priors, not personal truth.{" "}
              {pressure.coverage_questions.length} coverage question
              {pressure.coverage_questions.length === 1 ? "" : "s"} need
              confirmation before this becomes a plan.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
