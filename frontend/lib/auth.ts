/**
 * NextAuth configuration. Mints an HS256 JWT signed with NEXTAUTH_SECRET
 * (which MUST equal the backend's JWT_SECRET) and exposes it on the
 * session as `backendToken`. The api wrapper in lib/api.ts reads it and
 * sends it as Authorization: Bearer.
 *
 * 2026-04-21: Google Calendar read-only integration (see
 * docs/strategic_decisions_april_21.md §6).
 * - Scope expanded to include calendar.readonly
 * - access_type=offline + prompt=consent so Google returns a
 *   refresh_token on every consent. Without prompt=consent, a user
 *   who previously granted only profile+email would sign in silently
 *   with NO refresh_token returned (Google's OAuth optimization);
 *   we'd be stuck unable to access their calendar.
 * - Refresh token captured in the `jwt` callback on first sign-in
 *   and surfaced to the client as `session.hasRefreshToken`. A
 *   server-side API route (app/api/calendar/setup/route.ts) then
 *   forwards it to the Lyra backend for persistent storage.
 * - The token sits in the NextAuth JWT cookie for the duration
 *   between sign-in and the /api/calendar/setup POST — a single
 *   request-response cycle. It's never exposed to client JS.
 */
import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { SignJWT } from "jose";

const SECRET = process.env.NEXTAUTH_SECRET || "";

async function mintBackendToken(payload: { sub: string; email: string }) {
  const key = new TextEncoder().encode(SECRET);
  return await new SignJWT({ email: payload.email, sub: payload.sub })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(payload.sub)
    .setIssuedAt()
    .setExpirationTime("12h")
    .sign(key);
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
      authorization: {
        params: {
          scope:
            "openid email profile https://www.googleapis.com/auth/calendar.readonly",
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.email = profile.email;
        token.sub = (profile as any).sub || token.sub;
        token.backendToken = await mintBackendToken({
          sub: token.sub as string,
          email: profile.email as string,
        });
      }
      // Capture the refresh_token on every sign-in where Google
      // returned one. `prompt=consent` forces a fresh token on each
      // consent, so every sign-in after re-consent produces a new
      // one. Store it on the JWT just long enough for the
      // /api/calendar/setup route to forward it to the backend;
      // after that it's fine for this field to be absent (we don't
      // need it on subsequent token refreshes — the backend owns the
      // persistent copy).
      if (account?.refresh_token) {
        (token as any).googleRefreshToken = account.refresh_token;
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).backendToken = token.backendToken;
      (session.user as any).googleId = token.sub;
      // Expose ONLY a boolean flag to the client. The raw
      // refresh_token stays on the JWT (server-side, encrypted
      // cookie) — it's read by /api/calendar/setup via getToken()
      // and POSTed to the backend, never touching client JS.
      // `useSession()` on the client sees this flag and can
      // trigger the setup call, nothing more.
      (session as any).hasGoogleRefreshToken = !!(token as any).googleRefreshToken;
      return session;
    },
  },
};
