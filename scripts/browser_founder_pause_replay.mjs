#!/usr/bin/env node
import { spawn } from "node:child_process";
import { open, mkdir } from "node:fs/promises";
import path from "node:path";

import {
  apiFetch,
  assertCookieHeaderLooksUsable,
  frontendRequire,
  parseAndExpandCookies,
  repoRoot,
  resolveBackendTokenFromContext,
  userRef,
} from "./browser_auth_helpers.mjs";
import {
  assertAggregateOnly,
  assertNoPrivateValues,
} from "./pause_replay_artifact_contract.mjs";

const { chromium } = frontendRequire("playwright");

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function normalize(value) {
  return String(value || "").replace(/\/$/, "");
}

function runEvaluator(python, exported) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, ["scripts/run_founder_pause_replay.py"], {
      cwd: path.join(repoRoot, "backend"),
      env: {
        ...process.env,
        PYTHONPATH: path.join(repoRoot, "backend"),
      },
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    const stdout = [];
    const stderr = [];
    child.stdout.on("data", (value) => stdout.push(value));
    child.stderr.on("data", (value) => stderr.push(value));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`pause replay evaluator exited ${code}: ${Buffer.concat(stderr).toString("utf8").slice(0, 1000)}`));
        return;
      }
      try {
        resolve(JSON.parse(Buffer.concat(stdout).toString("utf8")));
      } catch (error) {
        reject(new Error(`pause replay evaluator returned invalid JSON: ${error.message}`));
      }
    });
    child.stdin.end(JSON.stringify(exported));
  });
}

const frontendOrigin = normalize(arg("--frontend", "https://lyraos.org"));
const apiOrigin = normalize(arg("--api", "https://api.lyraos.org"));
const python = arg("--python");
const outputArg = arg("--out-file");
const outFile = outputArg ? path.resolve(outputArg) : null;
const methodCommit = arg("--method-commit");
const cookieHeader = process.env.LYRA_COOKIE_ALINASSERSABRY || "";

if (!python || !outFile || !methodCommit) {
  throw new Error("--python, --out-file, and --method-commit are required");
}
assertCookieHeaderLooksUsable("LYRA_COOKIE_ALINASSERSABRY", cookieHeader);
await mkdir(path.dirname(outFile), { recursive: true });
const reservation = await open(outFile, "wx");
await reservation.writeFile(`${JSON.stringify({ status: "reserved", method_commit: methodCommit })}\n`);

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await context.addCookies(parseAndExpandCookies(cookieHeader, frontendOrigin));
  const token = await resolveBackendTokenFromContext(context, frontendOrigin);
  const [me, exported, frontendTopology, backendTopology] = await Promise.all([
    apiFetch(apiOrigin, token, "/v1/users/me"),
    apiFetch(apiOrigin, token, "/v1/users/me/export"),
    fetch(`${frontendOrigin}/api/topology`).then((response) => response.json()),
    fetch(`${apiOrigin}/v1/health/topology`).then((response) => response.json()),
  ]);
  if (!me.response.ok || me.body?.is_operator !== true) {
    throw new Error("operator cookie did not resolve to the read-only operator account");
  }
  if (!exported.response.ok || !exported.body || typeof exported.body !== "object") {
    throw new Error(`operator export failed with status ${exported.response.status}`);
  }

  const analysis = await runEvaluator(python, exported.body);
  assertAggregateOnly(analysis);
  assertNoPrivateValues(analysis, exported.body);
  const result = {
    schema_version: 1,
    status: "complete",
    topology: "hosted-public-read-only",
    method_commit: methodCommit,
    operator_user_ref: userRef(me.body?.user_id),
    frontend_build_id: frontendTopology?.build_id || null,
    backend_build_id: backendTopology?.build_id || null,
    source_section_counts: Object.fromEntries(
      Object.entries(exported.body)
        .filter(([, value]) => Array.isArray(value))
        .map(([key, value]) => [key, value.length])
        .sort(([left], [right]) => left.localeCompare(right)),
    ),
    analysis,
  };
  assertAggregateOnly(result);
  assertNoPrivateValues(result, exported.body);
  const resultText = `${JSON.stringify(result, null, 2)}\n`;
  await reservation.truncate(0);
  await reservation.write(resultText, 0, "utf8");
  console.log(JSON.stringify({
    ok: true,
    out_file: path.relative(repoRoot, outFile).replaceAll("\\", "/"),
    status: analysis.status,
    holdout_evaluated: analysis.holdout_evaluated,
    visible_runtime_enabled: analysis.visible_runtime_enabled ?? false,
  }));
  await context.close();
} catch (error) {
  const failure = {
    schema_version: 1,
    status: "failed_reserved",
    method_commit: methodCommit,
    error_class: error?.name || "Error",
    error: String(error?.message || error).slice(0, 1000),
  };
  const failureText = `${JSON.stringify(failure, null, 2)}\n`;
  await reservation.truncate(0);
  await reservation.write(failureText, 0, "utf8");
  throw error;
} finally {
  await reservation.close();
  await browser?.close();
}
