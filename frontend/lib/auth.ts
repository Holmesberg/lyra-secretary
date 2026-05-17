/**
 * NextAuth configuration. Mints an HS256 JWT signed with NEXTAUTH_SECRET
 * (which MUST equal the backend's JWT_SECRET) and exposes it on the
 * session as `backendToken`. The api wrapper in lib/api.ts reads it and
 * sends it as Authorization: Bearer.
 *
 * 2026-04-22: split identity from authorization (see
 * docs/integrations_architecture.md + docs/strategic_decisions_april_22.md).
 * Sign-in requests ONLY non-sensitive scopes (`openid email profile`).
 * Zero OAuth verification required for sign-up, so any Google account
 * can create a Lyra account without being on the Testing-mode test-user
 * list.
 *
 * Third-party scopes (Google Calendar, etc.) are acquired via
 * incremental OAuth from Settings → Integrations — a separate, user-
 * triggered consent moment. See
 * frontend/app/api/integrations/google-calendar/{connect,callback}/route.ts
 * for the per-integration flow.
 */
import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import { decodeJwt, SignJWT } from "jose";

const DEFAULT_BACKEND_JWT_SECRET = "dev-only-replace-me-with-32-byte-urlsafe-secret";
const MIN_BACKEND_JWT_SECRET_LENGTH = 32;
const BACKEND_TOKEN_REFRESH_WINDOW_SECONDS = 10 * 60;

function getBackendJwtSecret(): string {
  const secret = process.env.NEXTAUTH_SECRET || "";
  if (
    !secret ||
    secret === DEFAULT_BACKEND_JWT_SECRET ||
    secret.length < MIN_BACKEND_JWT_SECRET_LENGTH
  ) {
    throw new Error(
      `NEXTAUTH_SECRET must be configured to a non-default value of at least ${MIN_BACKEND_JWT_SECRET_LENGTH} characters before minting backend tokens.`
    );
  }
  return secret;
}

async function mintBackendToken(payload: { sub: string; email: string }) {
  const key = new TextEncoder().encode(getBackendJwtSecret());
  return await new SignJWT({ email: payload.email, sub: payload.sub })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(payload.sub)
    .setIssuedAt()
    .setExpirationTime("12h")
    .sign(key);
}

function backendTokenNeedsRefresh(token: unknown): boolean {
  if (typeof token !== "string" || !token) {
    return true;
  }
  try {
    const decoded = decodeJwt(token);
    const exp = typeof decoded.exp === "number" ? decoded.exp : 0;
    const now = Math.floor(Date.now() / 1000);
    return exp - now <= BACKEND_TOKEN_REFRESH_WINDOW_SECONDS;
  } catch {
    return true;
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
      authorization: {
        params: {
          // Identity-only scopes. Non-sensitive; no Google OAuth
          // verification needed, so Testing mode never blocks sign-up.
          // Integration-specific scopes (calendar.readonly, etc.) are
          // requested incrementally from the Integrations panel.
          scope: "openid email profile",
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
      }
      if (
        token.sub &&
        token.email &&
        backendTokenNeedsRefresh(token.backendToken)
      ) {
        token.backendToken = await mintBackendToken({
          sub: token.sub as string,
          email: token.email as string,
        });
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).backendToken = token.backendToken;
      (session.user as any).googleId = token.sub;
      return session;
    },
  },
};
