/**
 * Incremental OAuth — initiate Google Calendar consent.
 *
 * The user is already authenticated (identity) via NextAuth with only
 * non-sensitive scopes. This route is the "Connect" button's endpoint:
 * it builds a fresh Google OAuth authorization URL that requests
 * `calendar.readonly` + `access_type=offline` + `prompt=consent`,
 * signs a short-lived `state` tying the flow to the current user, and
 * redirects the browser there.
 *
 * The complementary `/callback` route validates state, exchanges the
 * code for a refresh_token, checks the consenting Google account
 * matches the signed-in user, and forwards the refresh_token to the
 * LyraOS backend.
 *
 * State param: HS256 JWT with `{purpose:"gcal_connect", user_id,
 * email, nonce}`, 10-min TTL, signed with NEXTAUTH_SECRET. Prevents
 * CSRF (attacker-crafted callback URLs) and user-swap replay (alice's
 * state reused in bob's session).
 *
 * See docs/integrations_architecture.md §Incremental OAuth Flow.
 */
import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { SignJWT } from "jose";

export const dynamic = "force-dynamic";

const GOOGLE_OAUTH_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth";
const CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly";

export async function GET(request: Request) {
  const token = await getToken({
    req: request as any,
    secret: process.env.NEXTAUTH_SECRET,
  });
  if (!token) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  const email = (token.email as string | undefined) ?? "";
  const userSub = (token.sub as string | undefined) ?? "";
  if (!email || !userSub) {
    return NextResponse.json(
      { error: "missing identity on session" },
      { status: 401 }
    );
  }

  const clientId = process.env.GOOGLE_CLIENT_ID || "";
  if (!clientId) {
    return NextResponse.json(
      { error: "GOOGLE_CLIENT_ID unset" },
      { status: 500 }
    );
  }
  const secret = process.env.NEXTAUTH_SECRET || "";
  if (!secret) {
    return NextResponse.json(
      { error: "NEXTAUTH_SECRET unset" },
      { status: 500 }
    );
  }

  // Origin derivation — prefer NEXTAUTH_URL in production (Cloudflare
  // Tunnel strips protocol forwarding headers in some configs), fall
  // back to the request URL for localhost dev.
  const origin =
    process.env.NEXTAUTH_URL?.replace(/\/$/, "") ||
    new URL(request.url).origin;
  const redirectUri = `${origin}/api/integrations/google-calendar/callback`;

  // Sign the state — 10 minute TTL is a comfortable window for a user
  // to decide on the consent screen without keeping a replay window
  // wide enough to matter.
  const nonce = crypto.randomUUID();
  const key = new TextEncoder().encode(secret);
  const state = await new SignJWT({
    purpose: "gcal_connect",
    user_sub: userSub,
    email,
    nonce,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("10m")
    .sign(key);

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: CALENDAR_SCOPE,
    access_type: "offline",
    // Force consent screen so Google always returns a refresh_token.
    // Without this, a user who previously granted the same scope
    // (e.g., re-connected after a disconnect) would come back with
    // only an access_token and no refresh_token — then we can't
    // persist offline access. The UX cost is one extra confirmation
    // click per re-connect; the correctness gain is "we always have
    // offline access when the button says Connected."
    prompt: "consent",
    // `include_granted_scopes=true` lets Google merge this scope with
    // any previously-granted scopes on the same Google account so the
    // user isn't forced to re-grant identity scopes (which they
    // already gave to sign in).
    include_granted_scopes: "true",
    // Nudge Google to skip the account picker when the user has
    // multiple Google accounts. Doesn't prevent an account swap —
    // that's enforced server-side in the callback.
    login_hint: email,
    state,
  });

  const authUrl = `${GOOGLE_OAUTH_AUTHORIZE}?${params.toString()}`;
  return NextResponse.redirect(authUrl);
}
