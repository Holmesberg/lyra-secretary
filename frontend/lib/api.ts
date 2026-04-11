/**
 * Backend API client. Reads the next-auth session, pulls the
 * backendToken minted in lib/auth.ts, and forwards it as Bearer.
 */
import { getSession } from "next-auth/react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Error thrown by the api() helper for non-2xx responses. Carries the
 * HTTP status so callers can distinguish e.g. a 401 expired session
 * from a genuine network failure (which throws a plain TypeError).
 */
export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const session = await getSession();
  const token = (session as any)?.backendToken as string | undefined;

  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    let msg = `${res.status}: ${text}`;
    try {
      const body = JSON.parse(text);
      const detail = body?.detail;
      if (typeof detail === "string") msg = detail;
      else if (detail?.message) msg = detail.message;
    } catch {}
    throw new ApiError(msg, res.status);
  }
  return (await res.json()) as T;
}
