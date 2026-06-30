export function formatLocal(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

/** Round up to the next 5-minute boundary. 2:06 -> 2:10; 2:58 -> 3:00. */
export function defaultStart(from: Date = new Date()) {
  const d = new Date(from);
  const mins = d.getMinutes();
  const next5 = Math.ceil(mins / 5) * 5;
  if (next5 >= 60) {
    d.setHours(d.getHours() + 1, 0, 0, 0);
  } else {
    d.setMinutes(next5, 0, 0);
  }
  return formatLocal(d);
}

export function defaultStartForDate(targetDateStr: string, now: Date = new Date()) {
  const [y, m, d] = targetDateStr.split("-").map(Number);
  const base = new Date(y, m - 1, d, now.getHours(), now.getMinutes(), 0, 0);
  const mins = base.getMinutes();
  const next5 = Math.ceil(mins / 5) * 5;
  if (next5 >= 60) {
    base.setHours(base.getHours() + 1, 0, 0, 0);
  } else {
    base.setMinutes(next5, 0, 0);
  }
  return formatLocal(base);
}

export function addMinutes(localStr: string, mins: number): string {
  const d = new Date(localStr);
  d.setMinutes(d.getMinutes() + mins);
  return formatLocal(d);
}

export function diffMinutes(startStr: string, endStr: string): number {
  return Math.round((new Date(endStr).getTime() - new Date(startStr).getTime()) / 60_000);
}

export function timeOfDay(localStr: string): string {
  const h = new Date(localStr).getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 21) return "evening";
  return "night";
}

export function roundTo5(n: number): number {
  return Math.round(n / 5) * 5 || 5;
}

export function formatPlanDeltaFromFactor(factor: number | null | undefined): string {
  if (factor === null || factor === undefined || Number.isNaN(factor)) {
    return "unknown";
  }
  const pct = Math.round((factor - 1) * 100);
  if (pct === 0) return "on plan";
  return `${Math.abs(pct)}% ${pct > 0 ? "over" : "under"} plan`;
}
