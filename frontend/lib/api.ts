/**
 * Backend API client. Reads the next-auth session, pulls the
 * backendToken minted in lib/auth.ts, and forwards it as Bearer.
 */
import { getSession } from "next-auth/react";
import { clearPersistedCache } from "@/lib/clear-persisted-cache";

const LOCAL_API_BASE = "http://localhost:8000";
const PUBLIC_API_BASE = "https://api.lyraos.org";
const CONFIGURED_API_BASE = process.env.NEXT_PUBLIC_API_URL || LOCAL_API_BASE;
const SESSION_TOKEN_TTL_MS = 30_000;
const SESSION_TOKEN_RETRY_ATTEMPTS = 5;
const SESSION_TOKEN_RETRY_DELAY_MS = 100;

let cachedBackendToken: string | undefined;
let cachedBackendTokenUntil = 0;
let sessionTokenPromise: Promise<string | undefined> | null = null;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "lyraos.org" || host.endsWith(".lyraos.org")) {
      return PUBLIC_API_BASE;
    }
    if (host === "localhost" || host === "127.0.0.1") {
      return CONFIGURED_API_BASE;
    }
  }
  return CONFIGURED_API_BASE;
}

export function primeBackendToken(token: string | undefined, ttlMs = SESSION_TOKEN_TTL_MS) {
  cachedBackendToken = token;
  cachedBackendTokenUntil = token ? Date.now() + ttlMs : 0;
}

export function clearBackendTokenCache() {
  cachedBackendToken = undefined;
  cachedBackendTokenUntil = 0;
  sessionTokenPromise = null;
}

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
        cachedBackendTokenUntil = token ? Date.now() + SESSION_TOKEN_TTL_MS : 0;
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
  let token = await getBackendToken();
  if (!token && typeof window !== "undefined") {
    for (let attempt = 0; attempt < SESSION_TOKEN_RETRY_ATTEMPTS && !token; attempt += 1) {
      await sleep(SESSION_TOKEN_RETRY_DELAY_MS);
      token = await getBackendToken();
    }
  }

  if (!token) {
    const msg = "not authenticated";
    clearBackendTokenCache();
    clearPersistedCache();
    _pushRecentError({ path, status: 401, message: msg });
    throw new ApiError(msg, 401);
  }

  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${getApiBase()}${path}`, { ...init, headers });
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
      clearBackendTokenCache();
      clearPersistedCache();
    }
    throw new ApiError(msg, res.status);
  }
  return (await res.json()) as T;
}

export async function ackExposureRender(
  exposureId: string | null | undefined,
  details?: {
    surfaceId?: string;
    contentSnapshot?: Record<string, unknown>;
    clientEventId?: string;
    keepalive?: boolean;
  }
): Promise<boolean> {
  if (!exposureId) return false;
  try {
    await api(`/v1/exposures/${encodeURIComponent(exposureId)}/ack/render`, {
      method: "POST",
      keepalive: details?.keepalive,
      body: JSON.stringify({
        surface_id: details?.surfaceId,
        content_snapshot: details?.contentSnapshot,
        client_event_id: details?.clientEventId,
      }),
    });
    return true;
  } catch {
    // Render acknowledgements are governance telemetry. They must retry safely
    // when called again, but they should never block the user's current view.
    return false;
  }
}

export async function ackExposureSuppression(
  exposureId: string | null | undefined,
  details?: { suppressionReason?: string; keepalive?: boolean }
): Promise<boolean> {
  if (!exposureId) return false;
  try {
    await api(`/v1/exposures/${encodeURIComponent(exposureId)}/ack/suppress`, {
      method: "POST",
      keepalive: details?.keepalive,
      body: JSON.stringify({
        suppression_reason: details?.suppressionReason || "client_discarded_before_render",
      }),
    });
    return true;
  } catch {
    // Like render acknowledgement, suppression telemetry must never block the
    // user's current action. Missing suppression stays visible in /operator.
    return false;
  }
}

export function queueExposureSuppressionBeacon(
  exposureId: string | null | undefined,
): boolean {
  if (
    !exposureId ||
    typeof navigator === "undefined" ||
    typeof navigator.sendBeacon !== "function"
  ) {
    return false;
  }
  try {
    const body = new Blob(
      [JSON.stringify({ exposure_id: exposureId })],
      { type: "application/json" },
    );
    return navigator.sendBeacon("/api/exposures/suppress", body);
  } catch {
    return false;
  }
}
