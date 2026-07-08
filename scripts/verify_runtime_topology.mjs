#!/usr/bin/env node
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const contractPath = path.join(repoRoot, "runtime_topology.json");
const contract = JSON.parse(fs.readFileSync(contractPath, "utf8"));
const frontendRequire = createRequire(path.join(repoRoot, "frontend", "package.json"));
const { chromium } = frontendRequire("playwright");

function argValue(name, fallback = null) {
  const index = process.argv.indexOf(name);
  if (index >= 0 && process.argv[index + 1]) return process.argv[index + 1];
  return fallback;
}

const topologyArg = argValue("--topology", "public");
const skipBrowser = process.argv.includes("--skip-browser");
const selected =
  topologyArg === "both"
    ? Object.keys(contract.topologies)
    : topologyArg.split(",").map((value) => value.trim()).filter(Boolean);

function fail(message, detail = undefined) {
  const err = new Error(message);
  err.detail = detail;
  throw err;
}

function normalize(value) {
  return String(value || "").replace(/\/$/, "");
}

function relativePath(filePath) {
  return path.relative(repoRoot, filePath).replace(/\\/g, "/");
}

function tailText(value, maxChars = 4_000) {
  const text = String(value ?? "");
  if (text.length <= maxChars) return text;
  return text.slice(text.length - maxChars);
}

function readTailIfExists(filePath, maxChars = 4_000) {
  try {
    if (!fs.existsSync(filePath)) return null;
    const stat = fs.statSync(filePath);
    if (!stat.isFile()) return null;
    return {
      path: relativePath(filePath),
      tail: tailText(fs.readFileSync(filePath, "utf8"), maxChars),
    };
  } catch (error) {
    return {
      path: relativePath(filePath),
      read_error: error.message,
    };
  }
}

function localFrontendLogTails() {
  const logs = [];
  const directCandidates = [
    path.join(repoRoot, "tmp", "frontend-dev-3000.log"),
    path.join(repoRoot, "tmp", "frontend-dev-3000.err.log"),
  ];
  for (const candidate of directCandidates) {
    const tail = readTailIfExists(candidate);
    if (tail) logs.push(tail);
  }

  const devLogDir = path.join(repoRoot, "tmp", "local-frontend-dev");
  try {
    if (fs.existsSync(devLogDir)) {
      const recent = fs
        .readdirSync(devLogDir)
        .filter((name) => name.endsWith(".log"))
        .map((name) => {
          const filePath = path.join(devLogDir, name);
          return { filePath, mtimeMs: fs.statSync(filePath).mtimeMs };
        })
        .sort((a, b) => b.mtimeMs - a.mtimeMs)
        .slice(0, 4);
      for (const item of recent) {
        const tail = readTailIfExists(item.filePath);
        if (tail) logs.push(tail);
      }
    }
  } catch (error) {
    logs.push({
      path: relativePath(devLogDir),
      read_error: error.message,
    });
  }
  return logs;
}

function bodyExcerpt(body) {
  if (body == null) return null;
  const text = typeof body === "string" ? body : JSON.stringify(body);
  return tailText(text, 1_500);
}

function endpointFailureDetail(topologyName, endpointName, url, result) {
  const status = result?.response?.status ?? null;
  const detail = {
    classification: "topology/deployment_bug",
    topology: topologyName,
    endpoint: endpointName,
    url,
    status,
    body_excerpt: bodyExcerpt(result?.body),
  };

  if (topologyName === "local" && endpointName === "frontend" && status >= 500) {
    const logs = localFrontendLogTails();
    const combinedLogs = logs.map((entry) => entry.tail || entry.read_error || "").join("\n");
    const nextCacheSignals = [
      "app-paths-manifest.json",
      "_buildManifest.js.tmp",
      ".next",
      "ENOENT",
    ].filter((signal) => combinedLogs.includes(signal));

    detail.classification = "verifier/topology_bug";
    detail.likely_cause = nextCacheSignals.length
      ? "local Next dev cache/build artifact state is stale or corrupted"
      : "local frontend returned a server error before topology could be verified";
    detail.detected_signals = nextCacheSignals;
    detail.suggested_recovery = [
      "Stop the local frontend dev server on port 3000.",
      "From frontend/, run npm run dev:clean, or rerun the authorized local frontend restart helper.",
      "Rerun the same browser verifier; do not classify this as a product invariant failure until topology passes.",
    ];
    detail.log_tails = logs;
  }

  return detail;
}

async function fetchJson(url, init = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20_000);
  try {
    let response;
    try {
      response = await fetch(url, { ...init, signal: controller.signal });
    } catch (error) {
      error.detail = {
        url,
        method: init.method ?? "GET",
        cause_message: error.cause?.message,
        cause_code: error.cause?.code,
        cause_host: error.cause?.hostname ?? error.cause?.host,
        cause_port: error.cause?.port,
      };
      throw error;
    }
    const text = await response.text();
    let body = null;
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
    return { response, body };
  } finally {
    clearTimeout(timeout);
  }
}

function assertNoCrossTopologyPoison(topologyName, urls) {
  const otherOrigins = Object.entries(contract.topologies)
    .filter(([name]) => name !== topologyName)
    .flatMap(([, topology]) => [topology.frontend_origin, topology.api_origin, topology.nextauth_url])
    .map(normalize);
  const poisoned = urls.filter((url) =>
    otherOrigins.some((origin) => origin && normalize(url).startsWith(origin))
  );
  if (poisoned.length) {
    fail(`cross-topology request detected for ${topologyName}`, poisoned);
  }
}

async function verifyCors(topologyName, topology) {
  const declaredOrigins = contract.declared_browser_origins || [];
  for (const origin of declaredOrigins) {
    const { response } = await fetchJson(`${topology.api_origin}/v1/users/me`, {
      method: "OPTIONS",
      headers: {
        Origin: origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
      },
    });
    const allowed = response.headers.get("access-control-allow-origin");
    if (allowed !== origin) {
      fail(`CORS rejected declared origin ${origin} during ${topologyName} check`, {
        status: response.status,
        allowed,
      });
    }
  }

  const rogue = await fetch(`${topology.api_origin}/v1/users/me`, {
    method: "OPTIONS",
    headers: {
      Origin: "https://evil.example",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "authorization",
    },
  });
  if (rogue.headers.get("access-control-allow-origin")) {
    fail(`CORS allowed rogue origin during ${topologyName} check`, {
      status: rogue.status,
      allowed: rogue.headers.get("access-control-allow-origin"),
    });
  }
}

async function verifyTopology(topologyName) {
  const topology = contract.topologies[topologyName];
  if (!topology) fail(`unknown topology ${topologyName}`);

  const frontendUrl = `${topology.frontend_origin}/api/topology`;
  const frontend = await fetchJson(frontendUrl);
  if (!frontend.response.ok) {
    fail(
      `frontend topology endpoint failed for ${topologyName}`,
      endpointFailureDetail(topologyName, "frontend", frontendUrl, frontend)
    );
  }
  if (frontend.body.verified_topology !== true) {
    fail(`frontend topology is not verified for ${topologyName}`, frontend.body);
  }
  if (frontend.body.topology_class !== topologyName) {
    fail(`frontend topology class mismatch for ${topologyName}`, frontend.body);
  }
  if (normalize(frontend.body.frontend_origin) !== normalize(topology.frontend_origin)) {
    fail(`frontend origin mismatch for ${topologyName}`, frontend.body);
  }
  if (normalize(frontend.body.compiled_api_origin) !== normalize(topology.api_origin)) {
    fail(`compiled API origin mismatch for ${topologyName}`, frontend.body);
  }
  if (normalize(frontend.body.nextauth_url) !== normalize(topology.nextauth_url)) {
    fail(`NextAuth URL mismatch for ${topologyName}`, frontend.body);
  }

  const backendUrl = `${topology.api_origin}/v1/health/topology`;
  const backend = await fetchJson(backendUrl, {
    headers: { Origin: topology.frontend_origin },
  });
  if (!backend.response.ok) {
    fail(
      `backend topology endpoint failed for ${topologyName}`,
      endpointFailureDetail(topologyName, "backend", backendUrl, backend)
    );
  }
  if (backend.body.verified_topology !== true) {
    fail(`backend topology is not verified for ${topologyName}`, backend.body);
  }
  if (backend.body.topology_class !== topologyName) {
    fail(`backend topology class mismatch for ${topologyName}`, backend.body);
  }
  if (normalize(backend.body.api_origin) !== normalize(topology.api_origin)) {
    fail(`backend API origin mismatch for ${topologyName}`, backend.body);
  }

  const authUrl = `${topology.frontend_origin}/api/auth/providers`;
  const auth = await fetchJson(authUrl);
  if (!auth.response.ok) {
    fail(
      `auth provider endpoint failed for ${topologyName}`,
      endpointFailureDetail(topologyName, "nextauth_provider", authUrl, auth)
    );
  }
  const google = auth.body?.google;
  if (!google?.signinUrl?.startsWith(`${topology.nextauth_url}/api/auth/signin/google`)) {
    fail(`auth provider URL mismatch for ${topologyName}`, google);
  }

  await verifyCors(topologyName, topology);

  if (!skipBrowser) {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    const requests = [];
    page.on("request", (request) => requests.push(request.url()));
    await page.goto(topology.frontend_origin, { waitUntil: "domcontentloaded", timeout: 45_000 });
    await page.evaluate(async () => {
      await fetch("/api/topology");
    });
    await page.evaluate(async (apiOrigin) => {
      await fetch(`${apiOrigin}/v1/health/topology`);
    }, topology.api_origin);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    await browser.close();
    assertNoCrossTopologyPoison(topologyName, requests);
  }

  return {
    topology_class: topologyName,
    frontend_origin: topology.frontend_origin,
    api_origin: topology.api_origin,
    verified_topology: true,
    frontend_build_id: frontend.body.build_id,
    backend_build_id: backend.body.build_id,
  };
}

const results = [];
try {
  for (const topologyName of selected) {
    results.push(await verifyTopology(topologyName));
  }
  console.log(JSON.stringify({ ok: true, checked: results }, null, 2));
} catch (error) {
  console.error(
    JSON.stringify(
      {
        ok: false,
        error: error.message,
        detail:
          error.detail ??
          (error.cause
            ? {
                cause_message: error.cause.message,
                cause_code: error.cause.code,
                cause_host: error.cause.hostname ?? error.cause.host,
                cause_port: error.cause.port,
              }
            : null),
      },
      null,
      2
    )
  );
  process.exit(1);
}
