// Preload via NODE_OPTIONS=--require ./preload-ipv4.js to force IPv4-only
// outbound networking BEFORE any module loads. The Next.js instrumentation
// hook only runs for the runtime server (dev/start), not during `next build`
// — but `next/font/google` makes fetch calls during build and hits the same
// IPv6-unreachable problem on operator's WSL2.
//
// Loaded by all three scripts in package.json so dev / build / start
// behave identically. Drop this file when the host has working IPv6 OR
// when next/font is replaced with locally-bundled fonts.
//
// 2026-04-29 incident: cold-restart of `npm run start` started failing
// OAuth despite NODE_OPTIONS=--dns-result-order=ipv4first because undici
// (the fetch impl in openid-client and next/font) maintains its own
// connection pool that doesn't honor dns.setDefaultResultOrder. Then the
// rebuild also failed because next/font couldn't fetch Chakra Petch.

require("dns").setDefaultResultOrder("ipv4first");

try {
  const undici = require("undici");
  undici.setGlobalDispatcher(
    new undici.Agent({
      connect: {
        family: 4, // AF_INET only
        autoSelectFamily: false, // disable Happy Eyeballs
      },
    }),
  );
} catch (e) {
  console.warn("[preload-ipv4] undici dispatcher install failed:", e && e.message);
}
