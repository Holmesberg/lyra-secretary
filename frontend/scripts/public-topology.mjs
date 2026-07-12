#!/usr/bin/env node
import { spawn } from "node:child_process";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  restorePublicBuildInputs,
  snapshotPublicBuildInputs,
} from "./public-build-source-guard.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(__dirname, "..", "..");
const distDir = process.env.NEXT_DIST_DIR || ".next-public";
const publicBuildIdPath = path.join(frontendRoot, distDir, "LYRA_PUBLIC_BUILD_ID");

const command = process.argv[2];
const validCommands = new Set(["build", "start"]);

if (!validCommands.has(command)) {
  console.error("Usage: node scripts/public-topology.mjs <build|start>");
  process.exit(1);
}

function gitShortSha() {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], {
      cwd: repoRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "dev";
  }
}

function readArtifactBuildId() {
  try {
    const value = fs.readFileSync(publicBuildIdPath, "utf8").trim();
    return value || null;
  } catch {
    return null;
  }
}

function resolvePublicBuildId() {
  if (process.env.NEXT_PUBLIC_BUILD_ID) {
    return process.env.NEXT_PUBLIC_BUILD_ID;
  }
  if (command === "start") {
    const artifactBuildId = readArtifactBuildId();
    if (artifactBuildId) {
      return artifactBuildId;
    }
    console.error(
      `[public-topology] missing artifact build id metadata: ${publicBuildIdPath}`
    );
    console.error(
      "[public-topology] run `npm run build:public` before `npm run start:public`."
    );
    process.exit(2);
  }
  return gitShortSha();
}

const nextBin = path.resolve(
  __dirname,
  "..",
  "node_modules",
  "next",
  "dist",
  "bin",
  "next"
);

const env = {
  ...process.env,
  NEXTAUTH_URL: "https://lyraos.org",
  NEXT_PUBLIC_API_URL: "https://api.lyraos.org",
  NEXT_PUBLIC_BUILD_ID: resolvePublicBuildId(),
  NEXT_DIST_DIR: distDir,
};

const buildInputSnapshot =
  command === "build" ? snapshotPublicBuildInputs(frontendRoot) : null;

let buildInputsRestored = false;
function restoreBuildInputs() {
  if (!buildInputSnapshot || buildInputsRestored) {
    return;
  }
  restorePublicBuildInputs(buildInputSnapshot);
  buildInputsRestored = true;
}

console.log("[public-topology] NEXTAUTH_URL=https://lyraos.org");
console.log("[public-topology] NEXT_PUBLIC_API_URL=https://api.lyraos.org");
console.log(`[public-topology] NEXT_PUBLIC_BUILD_ID=${env.NEXT_PUBLIC_BUILD_ID}`);
console.log(`[public-topology] NEXT_DIST_DIR=${env.NEXT_DIST_DIR}`);

const child = spawn(
  process.execPath,
  [
    "--dns-result-order=ipv4first",
    "--no-network-family-autoselection",
    nextBin,
    command,
  ],
  {
    cwd: path.resolve(__dirname, ".."),
    env,
    stdio: "inherit",
    shell: false,
  }
);

child.on("error", (error) => {
  try {
    restoreBuildInputs();
  } catch (restoreError) {
    console.error("[public-topology] failed to restore build inputs", restoreError);
  }
  console.error("[public-topology] failed to start Next.js", error);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  try {
    restoreBuildInputs();
  } catch (error) {
    console.error("[public-topology] failed to restore build inputs", error);
    process.exit(3);
  }
  if (signal) {
    console.error(`[public-topology] next ${command} exited via ${signal}`);
    process.exit(1);
  }
  const exitCode = code ?? 0;
  if (exitCode === 0 && command === "build") {
    fs.writeFileSync(publicBuildIdPath, `${env.NEXT_PUBLIC_BUILD_ID}\n`);
    console.log(`[public-topology] wrote artifact build id ${publicBuildIdPath}`);
  }
  process.exit(exitCode);
});
