import assert from "node:assert/strict";

import {
  expandNextAuthCookieAliases,
  parseCookieHeader,
  parseAndExpandCookies,
  userRef,
} from "./browser_auth_helpers.mjs";

const publicOrigin = "https://lyraos.org";
const localOrigin = "http://localhost:3000";

assert.deepEqual(
  parseCookieHeader("raw-token", publicOrigin),
  [{ name: "__Secure-next-auth.session-token", value: "raw-token" }],
);

assert.deepEqual(
  parseCookieHeader("Cookie: next-auth.session-token=abc; theme=dark", publicOrigin),
  [
    { name: "next-auth.session-token", value: "abc" },
    { name: "theme", value: "dark" },
  ],
);

assert.deepEqual(
  expandNextAuthCookieAliases(
    [{ name: "next-auth.session-token", value: "abc" }],
    publicOrigin,
  ),
  [
    { name: "next-auth.session-token", value: "abc", url: publicOrigin },
    { name: "__Secure-next-auth.session-token", value: "abc", url: publicOrigin },
  ],
);

assert.deepEqual(
  expandNextAuthCookieAliases(
    [{ name: "__Secure-next-auth.session-token", value: "abc" }],
    localOrigin,
  ),
  [{ name: "next-auth.session-token", value: "abc", url: localOrigin }],
);

assert.deepEqual(
  parseAndExpandCookies("__Host-next-auth.csrf-token=csrf", localOrigin),
  [{ name: "next-auth.csrf-token", value: "csrf", url: localOrigin }],
);

assert.equal(userRef(1), "6b86b273ff34");

console.log(JSON.stringify({ ok: true, checked: "browser_auth_helpers" }));
