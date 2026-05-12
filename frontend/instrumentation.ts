/**
 * Next.js instrumentation hook (runs once on server start).
 *
 * Force IPv4-only outbound networking. Operator's WSL2 (and the
 * eventual EC2 host if the VPC isn't IPv6-enabled) returns IPv6
 * addresses for Google's OAuth endpoints from `getaddrinfo` even
 * when IPv6 routing is dead. Node 18+'s `dns.lookup` follows the OS
 * order, leading to `AggregateError: internalConnectMultiple` on the
 * NextAuth signin callback because Happy Eyeballs races IPv4 and
 * IPv6 in parallel and aborts when both fail.
 *
 * **2026-04-29 amendment** — `dns.setDefaultResultOrder("ipv4first")`
 * alone was insufficient because `undici` (the fetch implementation
 * used by `openid-client` / NextAuth) maintains its OWN connection
 * pool and does not honor `dns.setDefaultResultOrder`. After the
 * Apr 29 cold-restart, OAuth started failing again with the same
 * AggregateError despite the dns-order setting. Fix: also install
 * an undici global dispatcher with `connect.autoSelectFamily=false`
 * and `family=4`, which forces IPv4-only at the socket level.
 *
 * Drop this file when:
 *   - we deploy to a host with native IPv6 (and verify), OR
 *   - we move OAuth out of the Node runtime (e.g. backend-mediated)
 *
 * Symptom of need: frontend stdout spamming
 *   [next-auth][error][SIGNIN_OAUTH_ERROR]
 *   AggregateError at internalConnectMultiple
 */
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  // Belt: dns.lookup ordering. Affects code paths that go through
  // Node's built-in DNS (e.g. legacy http.request).
  try {
    const nodeRequire = eval("require") as NodeRequire;
    const dns = nodeRequire("dns") as typeof import("dns");
    dns.setDefaultResultOrder("ipv4first");
  } catch {
    // Local/dev bundlers can analyze instrumentation.ts before the node
    // runtime is available. NODE_OPTIONS below remains the load-bearing
    // IPv4 guard, so this hook should never make the app fail to boot.
  }

  // Suspenders: --no-network-family-autoselection in NODE_OPTIONS
  // (package.json scripts) is what actually carries the load on Node
  // 20+. It disables Happy Eyeballs at the libuv level, so undici
  // never even attempts IPv6. Originally this hook also tried to
  // install an undici global dispatcher, but undici isn't a published
  // package on this project (only bundled with Node), and trying to
  // require it from instrumentation.ts spammed warnings without
  // adding any real protection beyond what the Node flag provides.
}
