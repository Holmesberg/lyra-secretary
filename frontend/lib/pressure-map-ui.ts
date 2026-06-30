import type { AcademicPressureItem } from "@/lib/academic";

export function fmtHours(lowMinutes: number, highMinutes: number): string {
  const low = Math.round(lowMinutes / 30) / 2;
  const high = Math.round(highMinutes / 30) / 2;
  if (low === high) return `${low}h`;
  return `${low}-${high}h`;
}

export function fmtDue(days: number): string {
  if (days < 0) return "overdue";
  if (days < 1) return "due today";
  if (days < 2) return "due tomorrow";
  return `in ${Math.round(days)}d`;
}

export function fmtTiming(item: AcademicPressureItem): string {
  const isTask = item.source_class === "lyra_task";
  const days = item.days_until_due;
  if (!isTask) return fmtDue(days);
  if (days < 0) return "started";
  if (days < 1) return "scheduled today";
  if (days < 2) return "scheduled tomorrow";
  return `scheduled in ${Math.round(days)}d`;
}

export function pressureClass(item: AcademicPressureItem): string {
  if (item.pressure_level === "overdue") return "border-ember/50 bg-ember/10";
  if (item.pressure_level === "high") return "border-ember/30 bg-ember/5";
  return "border-hairline bg-void-2/40";
}

export function fmtTrust(trust: AcademicPressureItem["trust_state"]): string {
  if (trust === "verified_reachable") return "source reachable";
  if (trust === "requires_user_confirmation") return "needs confirmation";
  if (trust === "verified_exact") return "source verified";
  return trust.replaceAll("_", " ");
}

export function genericPressureCopy(copy: string): string {
  return copy
    .replaceAll("visible academic load", "visible load")
    .replaceAll("academic load", "visible load")
    .replaceAll("academic pressure", "visible pressure")
    .replaceAll("academic ranges", "visible ranges")
    .replaceAll("academic obligations", "obligations")
    .replaceAll("academic tasks", "linked tasks")
    .replaceAll("Academic obligations", "Obligations")
    .replaceAll("Academic tasks", "Linked tasks")
    .replaceAll("study blocks", "focus blocks");
}
