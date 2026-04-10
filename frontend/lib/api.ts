/**
 * Backend API client. Reads the next-auth session, pulls the
 * backendToken minted in lib/auth.ts, and forwards it as Bearer.
 */
import { getSession } from "next-auth/react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    throw new Error(msg);
  }
  return (await res.json()) as T;
}
