#!/usr/bin/env node
import { spawn } from "node:child_process";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const command = process.argv[2];
const validCommands = new Set(["build", "start"]);

if (!validCommands.has(command)) {
  console.error("Usage: node scripts/public-topology.mjs <build|start>");
  process.exit(1);
}

function gitShortSha() {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], {
      cwd: path.resolve(__dirname, "..", ".."),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "dev";
  }
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
  NEXT_PUBLIC_BUILD_ID: process.env.NEXT_PUBLIC_BUILD_ID || gitShortSha(),
  NEXT_DIST_DIR: process.env.NEXT_DIST_DIR || ".next-public",
};

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

child.on("exit", (code, signal) => {
  if (signal) {
    console.error(`[public-topology] next ${command} exited via ${signal}`);
    process.exit(1);
  }
  process.exit(code ?? 0);
});
