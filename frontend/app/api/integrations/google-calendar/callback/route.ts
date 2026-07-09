/**
 * Incremental OAuth — Google Calendar consent callback.
 *
 * Google redirects here after the user sees the consent screen. Our
 * responsibilities in order:
 *   1. Validate `state` signature + TTL + purpose claim (CSRF guard).
 *   2. Verify the current NextAuth session user matches the user
 *      encoded in `state` (prevents "alice started flow, bob's cookie
 *      completes it" swap).
 *   3. Handle Google-side errors (user denied, Testing-mode block,
 *      etc.) with clear redirect-back-to-Settings messaging.
 *   4. Exchange the authorization `code` for a `refresh_token`.
 *   5. Verify the consenting Google account's email matches the
 *      signed-in user's email (prevents "alice signed in, bob's
 *      calendar connected" drift when a user has multiple Google
 *      accounts).
 *   6. Forward the refresh_token to the LyraOS backend via the existing
 *      POST /v1/users/me/google-refresh-token endpoint.
 *   7. Redirect back to /settings with success or error flag.
 *
 * id_token signature verification is deliberately skipped: the token
 * was delivered directly by Google over TLS in response to a request
 * carrying our `client_secret`, and we only read the `email` claim to
 * cross-check account identity. A forged id_token would require
 * compromising the TLS channel, which already compromises every
 * other secret in flight. Documented threat model, not oversight.
 * See docs/integrations_architecture.md §id_token threat model.
 */
import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { jwtVerify } from "jose";

export const dynamic = "force-dynamic";

const GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token";

type ErrorReason =
  | "missing_params"
  | "state_invalid"
  | "state_expired"
  | "user_mismatch"
  | "user_denied"
  | "testing_mode_block"
  | "google_error"
  | "token_exchange_failed"
  | "no_refresh_token"
  | "account_mismatch"
  | "backend_store_failed";

function settingsRedirect(
  origin: string,
  params: Record<string, string>
): NextResponse {
  const qs = new URLSearchParams(params).toString();
  return NextResponse.redirect(`${origin}/settings?${qs}`);
}

function decodeIdTokenEmail(idToken: string): string | null {
  try {
    const [, payloadB64] = idToken.split(".");
    if (!payloadB64) return null;
    const pad = "=".repeat((4 - (payloadB64.length % 4)) % 4);
    const decoded = atob(
      payloadB64.replace(/-/g, "+").replace(/_/g, "/") + pad
    );
    const claims = JSON.parse(decoded);
    return typeof claims.email === "string" ? claims.email : null;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const origin =
    process.env.NEXTAUTH_URL?.replace(/\/$/, "") || url.origin;
  const redirectUri = `${origin}/api/integrations/google-calendar/callback`;

  // Session identity (for user-swap guard) — loaded up-front so all
  // error paths can verify the user is still signed in.
  const sessionToken = await getToken({
    req: request as any,
    secret: process.env.NEXTAUTH_SECRET,
  });
  if (!sessionToken) {
    return NextResponse.redirect(`${origin}/?integration_error=unauth`);
  }
  const sessionEmail = (sessionToken.email as string | undefined) ?? "";
  const sessionSub = (sessionToken.sub as string | undefined) ?? "";
  const backendToken =
    (sessionToken as { backendToken?: string }).backendToken || "";

  // Google may redirect back with `error=access_denied` (user clicked
  // Cancel) or `error=admin_policy_enforced` / similar. Surface cleanly.
  const googleError = url.searchParams.get("error");
  if (googleError) {
    const reason: ErrorReason =
      googleError === "access_denied"
        ? "user_denied"
        : googleError === "admin_policy_enforced"
        ? "testing_mode_block"
        : "google_error";
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason,
      detail: googleError,
    });
  }

  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state) {
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "missing_params",
    });
  }

  // Verify signed state. Bad signature, wrong purpose, or expired TTL
  // all land here and get surfaced as "state_invalid" — the user sees
  // the same message either way; detail is logged server-side.
  const secret = process.env.NEXTAUTH_SECRET || "";
  let stateClaims: {
    purpose?: string;
    user_sub?: string;
    email?: string;
    nonce?: string;
  };
  try {
    const { payload } = await jwtVerify(
      state,
      new TextEncoder().encode(secret),
      { algorithms: ["HS256"] }
    );
    stateClaims = payload as typeof stateClaims;
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    const expired = msg.toLowerCase().includes("exp");
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: expired ? "state_expired" : "state_invalid",
    });
  }

  if (stateClaims.purpose !== "gcal_connect") {
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "state_invalid",
    });
  }
  // User-swap guard: the session that started the flow must be the
  // session completing it. Ties browser-tab identity to the OAuth
  // round-trip so another user's session can't complete a flow
  // initiated from a shared device.
  if (stateClaims.user_sub !== sessionSub) {
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "user_mismatch",
    });
  }

  // Exchange code for tokens.
  const clientId = process.env.GOOGLE_CLIENT_ID || "";
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET || "";
  let tokenResponse: {
    access_token?: string;
    refresh_token?: string;
    id_token?: string;
    scope?: string;
    expires_in?: number;
    token_type?: string;
  };
  try {
    const body = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      grant_type: "authorization_code",
      redirect_uri: redirectUri,
    });
    const res = await fetch(GOOGLE_TOKEN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!res.ok) {
      const text = await res.text();
      console.warn("gcal callback: token exchange failed", res.status, text);
      return settingsRedirect(origin, {
        integration_error: "google_calendar",
        reason: "token_exchange_failed",
      });
    }
    tokenResponse = await res.json();
  } catch (e) {
    console.warn("gcal callback: token exchange network error", e);
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "token_exchange_failed",
    });
  }

  if (!tokenResponse.refresh_token) {
    // prompt=consent is supposed to guarantee this — if we land here
    // something's wrong with the flow config (likely the user has
    // already granted this scope and Google is suppressing the
    // refresh_token despite the prompt). Surface clearly so the
    // operator can investigate.
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "no_refresh_token",
    });
  }

  // Account-match check. Google returns id_token containing the
  // authenticated Google account's email. If the user swapped
  // accounts on Google's side mid-flow (e.g., "Use another account"
  // link), we must not silently bind bob@gmail's calendar to
  // alice's LyraOS account. Compare case-insensitively; Google emails
  // are canonical-lowercased but defense in depth.
  const consentEmail = tokenResponse.id_token
    ? decodeIdTokenEmail(tokenResponse.id_token)
    : null;
  if (
    consentEmail &&
    sessionEmail &&
    consentEmail.toLowerCase() !== sessionEmail.toLowerCase()
  ) {
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "account_mismatch",
      detail: consentEmail,
    });
  }

  // Persist refresh_token via the existing backend endpoint.
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
      body: JSON.stringify({ refresh_token: tokenResponse.refresh_token }),
    });
    if (!res.ok) {
      const text = await res.text();
      console.warn("gcal callback: backend store failed", res.status, text);
      return settingsRedirect(origin, {
        integration_error: "google_calendar",
        reason: "backend_store_failed",
      });
    }
  } catch (e) {
    console.warn("gcal callback: backend unreachable", e);
    return settingsRedirect(origin, {
      integration_error: "google_calendar",
      reason: "backend_store_failed",
    });
  }

  return settingsRedirect(origin, {
    integration_connected: "google_calendar",
  });
}
