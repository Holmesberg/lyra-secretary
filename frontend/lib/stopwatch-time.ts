export interface StopwatchElapsedSnapshot {
  elapsed_seconds?: number | null;
  elapsed_minutes?: number | null;
}

export function getElapsedSeconds(
  snapshot: StopwatchElapsedSnapshot | null | undefined
): number {
  return snapshot?.elapsed_seconds ?? (snapshot?.elapsed_minutes ?? 0) * 60;
}
