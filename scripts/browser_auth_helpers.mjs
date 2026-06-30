import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const repoRoot = path.resolve(__dirname, "..");
export const frontendRequire = createRequire(
  path.join(repoRoot, "frontend", "package.json"),
);

export function userRef(userId) {
  return createHash("sha256").update(String(userId)).digest("hex").slice(0, 12);
}

export function parseCookieHeader(header, frontendOrigin) {
  const pairs = [];
  const normalized = String(header || "").trim().replace(/^cookie:\s*/i, "");
  for (const rawPart of normalized.split(";")) {
    const part = rawPart.trim();
    if (!part || !part.includes("=")) continue;
    const index = part.indexOf("=");
    const name = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (!name || !value) continue;
    pairs.push({ name, value });
  }
  if (!pairs.length && normalized) {
    pairs.push({
      name: frontendOrigin.startsWith("https://")
        ? "__Secure-next-auth.session-token"
        : "next-auth.session-token",
      value: normalized,
    });
  }
  return pairs;
}

export function expandNextAuthCookieAliases(cookies, frontendOrigin) {
  const out = [];
  const seen = new Set();
  const publicHttps = frontendOrigin.startsWith("https://");

  function add(name, value) {
    const key = `${name}=${value}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ name, value, url: frontendOrigin });
  }

  for (const cookie of cookies) {
    if (publicHttps || (
      !cookie.name.startsWith("__Secure-")
      && !cookie.name.startsWith("__Host-")
    )) {
      add(cookie.name, cookie.value);
    }
    if (publicHttps && cookie.name === "next-auth.session-token") {
      add("__Secure-next-auth.session-token", cookie.value);
    }
    if (cookie.name.startsWith("__Secure-")) {
      add(cookie.name.replace("__Secure-", ""), cookie.value);
    }
    if (cookie.name.startsWith("__Host-")) {
      add(cookie.name.replace("__Host-", ""), cookie.value);
    }
  }
  return out;
}

export function parseAndExpandCookies(cookieHeader, frontendOrigin) {
  return expandNextAuthCookieAliases(
    parseCookieHeader(cookieHeader, frontendOrigin),
    frontendOrigin,
  );
}

export function assertCookieHeaderLooksUsable(label, cookieHeader, minLength = 300) {
  if (!cookieHeader || String(cookieHeader).trim().length < minLength) {
    throw new Error(`${label} is missing or looks truncated`);
  }
}

export async function apiFetch(apiOrigin, token, pathname, init = {}) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(init.headers || {}),
  };
  const response = await fetch(`${apiOrigin}${pathname}`, { ...init, headers });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { response, body };
}

export async function resolveBackendToken(page) {
  const session = await page.evaluate(async () => {
    const response = await fetch("/api/auth/session");
    const text = await response.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = { parse_error: text.slice(0, 120) };
    }
    return {
      status: response.status,
      contentType: response.headers.get("content-type"),
      body,
    };
  });
  const token = session?.body?.backendToken;
  if (!token) {
    throw Object.assign(
      new Error("no backend token resolved"),
      {
        detail: {
          sessionStatus: session?.status,
          sessionContentType: session?.contentType,
          sessionKeys: Object.keys(session?.body || {}),
        },
      },
    );
  }
  return token;
}
