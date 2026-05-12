/**
 * Backend API client. Reads the next-auth session, pulls the
 * backendToken minted in lib/auth.ts, and forwards it as Bearer.
 */
import { getSession } from "next-auth/react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_TOKEN_TTL_MS = 30_000;

let cachedBackendToken: string | undefined;
let cachedBackendTokenUntil = 0;
let sessionTokenPromise: Promise<string | undefined> | null = null;

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

/**
 * Rolling buffer of the last 5 API errors (path + status + message).
 * Read by the feedback widget when the user opts in to "include
 * recent errors" — gives operator a 1-screen reproduction context.
 * Buffer lives on `window.__lyraLastErrors` so it survives across
 * route changes; lost on hard refresh which is fine.
 */
function _pushRecentError(entry: { path: string; status: number; message: string }) {
  if (typeof window === "undefined") return;
  const w = window as unknown as { __lyraLastErrors?: typeof entry[] };
  if (!Array.isArray(w.__lyraLastErrors)) w.__lyraLastErrors = [];
  w.__lyraLastErrors.unshift({ ...entry, ...({ at: new Date().toISOString() } as object) });
  if (w.__lyraLastErrors.length > 5) w.__lyraLastErrors.length = 5;
}

async function getBackendToken(): Promise<string | undefined> {
  const now = Date.now();
  if (cachedBackendTokenUntil > now) {
    return cachedBackendToken;
  }
  if (!sessionTokenPromise) {
    sessionTokenPromise = getSession()
      .then((session) => (session as any)?.backendToken as string | undefined)
      .then((token) => {
        cachedBackendToken = token;
        cachedBackendTokenUntil = Date.now() + SESSION_TOKEN_TTL_MS;
        return token;
      })
      .finally(() => {
        sessionTokenPromise = null;
      });
  }
  return sessionTokenPromise;
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const token = await getBackendToken();

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
    _pushRecentError({ path, status: res.status, message: msg.slice(0, 300) });
    if (res.status === 401) {
      cachedBackendToken = undefined;
      cachedBackendTokenUntil = 0;
    }
    throw new ApiError(msg, res.status);
  }
  return (await res.json()) as T;
}
