function newIdempotencyKey(scope: string): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${scope}:${random}`;
}

export function idempotencyHeaders(scope: string, idempotencyKey?: string) {
  return {
    "X-Idempotency-Key": idempotencyKey ?? newIdempotencyKey(scope),
  };
}
