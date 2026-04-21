/**
 * Calendar setup — forwards the Google refresh_token from the
 * NextAuth server-side session to the Lyra backend.
 *
 * Client-side JS CANNOT see the refresh_token directly: the JWT
 * cookie is encrypted by NextAuth and not exposed to the browser.
 * This route runs on the Next.js server, reads the JWT via
 * `getToken`, and POSTs the refresh_token to the Lyra backend
 * authenticated with the user's backend JWT (same token the api
 * wrapper uses).
 *
 * Idempotent: calling this route multiple times overwrites the
 * backend's stored refresh_token with the latest one, which is fine
 * — Google may rotate refresh tokens on re-consent.
 *
 * Called by the /today layout (or wherever `session.hasGoogleRefreshToken`
 * is true AND `me.google_calendar_connected` is false — a fresh
 * post-consent sign-in) so the token lands in the backend within
 * ~1 request cycle of the user granting calendar access.
 */
import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const token = await getToken({
    req: request as any,
    secret: process.env.NEXTAUTH_SECRET,
  });
  if (!token) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  const refreshToken = (token as any).googleRefreshToken as string | undefined;
  const backendToken = (token as any).backendToken as string | undefined;
  if (!refreshToken) {
    // No token on the session — user hasn't granted calendar scope,
    // or the refresh_token was already forwarded on a prior call and
    // we stripped it (future hardening). Not an error — the caller
    // can just not retry.
    return NextResponse.json({ connected: false, reason: "no_refresh_token" });
  }
  if (!backendToken) {
    return NextResponse.json(
      { error: "no backend token on session" },
      { status: 500 }
    );
  }

  const apiBase =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
    "http://localhost:8000";
  try {
    const res = await fetch(`${apiBase}/v1/users/me/google-refresh-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${backendToken}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: "backend store failed", status: res.status, detail: text },
        { status: 502 }
      );
    }
    return NextResponse.json({ connected: true });
  } catch (e) {
    return NextResponse.json(
      { error: "backend unreachable", detail: String(e) },
      { status: 502 }
    );
  }
}
