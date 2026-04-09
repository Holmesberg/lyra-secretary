/**
 * NextAuth configuration. Mints an HS256 JWT signed with NEXTAUTH_SECRET
 * (which MUST equal the backend's JWT_SECRET) and exposes it on the
 * session as `backendToken`. The api wrapper in lib/api.ts reads it and
 * sends it as Authorization: Bearer.
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
      return token;
    },
    async session({ session, token }) {
      (session as any).backendToken = token.backendToken;
      (session.user as any).googleId = token.sub;
      return session;
    },
  },
};
