import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth";

// Opt out of Next.js 15's static-paths analysis pass. next-auth v4's handler
// parses request bodies internally; when Next tries to pre-render the
// catch-all with a mocked empty request, `JSON.parse('')` throws
// "Unexpected end of JSON input" and Next logs "Failed to generate static
// paths for /api/auth/[...nextauth]" (4x cosmetic errors per page load).
// Forcing dynamic skips the analysis entirely without changing runtime
// behavior — the route was already dynamic in practice (uses cookies).
export const dynamic = "force-dynamic";

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
