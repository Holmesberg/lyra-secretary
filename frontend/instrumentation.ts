/**
 * Next.js instrumentation hook (runs once on server start).
 *
 * Force IPv4-first DNS resolution. Operator's WSL2 (and the eventual
 * EC2 host if the VPC isn't IPv6-enabled) returns IPv6 addresses for
 * Google's OAuth endpoints from `getaddrinfo` even when IPv6 routing
 * is dead. Node 18+'s `dns.lookup` follows the OS order, leading to
 * `AggregateError: internalConnectMultiple` on the NextAuth signin
 * callback because the IPv6 connection fails before Node falls back
 * to IPv4.
 *
 * Setting `dns.setDefaultResultOrder('ipv4first')` here makes every
 * downstream `dns.lookup` (including the openid-client / NextAuth
 * fetcher) try IPv4 first. Effective immediately on next-server
 * startup; survives all child-process spawns within the runtime.
 *
 * Drop this file when:
 *   - we deploy to a host with native IPv6 (and verify), OR
 *   - we move OAuth out of the Node runtime (e.g. backend-mediated)
 *
 * Symptom of need: backend log spamming
 *   [next-auth][error][SIGNIN_OAUTH_ERROR]
 *   AggregateError at internalConnectMultiple
 */
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const dns = await import("node:dns");
    dns.setDefaultResultOrder("ipv4first");
  }
}
