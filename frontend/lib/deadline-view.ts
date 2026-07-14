import {
  computeOverdueDeadlines,
  sortDeadlinesActiveFirst,
  type DeadlineResponse,
  type DeadlineState,
} from "@/lib/deadlines";

export const DEADLINE_STATE_LABEL: Record<DeadlineState, string> = {
  planned: "Planned",
  active: "Active",
  completed: "Completed",
  missed: "Missed",
  skipped: "Skipped",
  voided: "Voided",
};

export const DEADLINE_STATE_TONE: Record<DeadlineState, string> = {
  planned: "text-dust",
  active: "text-signal",
  completed: "text-dust-deep",
  missed: "text-ember",
  skipped: "text-dust-deep",
  voided: "text-dust-deep",
};

export interface DeadlineSections {
  overdue: DeadlineResponse[];
  active: DeadlineResponse[];
  completed: DeadlineResponse[];
  skippedOnly: DeadlineResponse[];
}

export function formatDeadlineRelative(iso: string): string {
  const due = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = due - now;
  const days = Math.round(diffMs / 86_400_000);
  if (Math.abs(days) >= 1) {
    return days >= 0 ? `in ${days}d` : `${Math.abs(days)}d ago`;
  }
  const hours = Math.round(diffMs / 3_600_000);
  if (Math.abs(hours) >= 1) {
    return hours >= 0 ? `in ${hours}h` : `${Math.abs(hours)}h ago`;
  }
  return diffMs >= 0 ? "soon" : "overdue";
}

export function formatDeadlineAbsolute(iso: string): string {
  const deadlineDate = new Date(iso);
  return deadlineDate.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function isDeadlineMarkDoneAllowed(deadline: DeadlineResponse): boolean {
  return (
    deadline.state === "planned" ||
    deadline.state === "active" ||
    deadline.state === "missed"
  );
}

export function isMoodleDeadline(deadline: DeadlineResponse): boolean {
  return Boolean(deadline.external_source?.startsWith("moodle"));
}

export function groupDeadlineSections(
  deadlines: DeadlineResponse[],
  nowMs = Date.now()
): DeadlineSections {
  const sorted = [...deadlines].sort((a, b) => {
    const aDue = new Date(a.due_at_utc).getTime();
    const bDue = new Date(b.due_at_utc).getTime();
    return aDue - bDue;
  });

  const overdue = computeOverdueDeadlines(sorted, { nowMs })
    .map(({ deadline }) => deadline)
    .sort(
      (a, b) =>
        new Date(b.due_at_utc).getTime() - new Date(a.due_at_utc).getTime()
    );
  const overdueIds = new Set(overdue.map((deadline) => deadline.deadline_id));

  const active = sortDeadlinesActiveFirst(
    sorted.filter(
      (deadline) =>
        (deadline.state === "planned" || deadline.state === "active") &&
        !overdueIds.has(deadline.deadline_id)
    )
  );

  const completed = sorted
    .filter((deadline) => deadline.state === "completed")
    .sort(
      (a, b) =>
        new Date(b.completed_at ?? b.due_at_utc).getTime() -
        new Date(a.completed_at ?? a.due_at_utc).getTime()
    );

  const skippedOnly = sorted
    .filter((deadline) => deadline.state === "skipped")
    .sort(
      (a, b) =>
        new Date(b.due_at_utc).getTime() - new Date(a.due_at_utc).getTime()
    );

  return { overdue, active, completed, skippedOnly };
}
