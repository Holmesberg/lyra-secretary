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

async function fetchJson(url, init = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20_000);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
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

  const frontend = await fetchJson(`${topology.frontend_origin}/api/topology`);
  if (!frontend.response.ok) {
    fail(`frontend topology endpoint failed for ${topologyName}`, frontend.response.status);
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

  const backend = await fetchJson(`${topology.api_origin}/v1/health/topology`, {
    headers: { Origin: topology.frontend_origin },
  });
  if (!backend.response.ok) {
    fail(`backend topology endpoint failed for ${topologyName}`, backend.response.status);
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

  const auth = await fetchJson(`${topology.frontend_origin}/api/auth/providers`);
  if (!auth.response.ok) {
    fail(`auth provider endpoint failed for ${topologyName}`, auth.response.status);
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
        detail: error.detail ?? null,
      },
      null,
      2
    )
  );
  process.exit(1);
}
