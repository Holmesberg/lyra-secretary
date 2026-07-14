#!/usr/bin/env node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  restorePublicBuildInputs,
  snapshotPublicBuildInputs,
} from "../frontend/scripts/public-build-source-guard.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const scriptPath = path.join(repoRoot, "scripts", "restart_frontend_wsl.ps1");
const script = fs.readFileSync(scriptPath, "utf8");
const publicTopologyPath = path.join(
  repoRoot,
  "frontend",
  "scripts",
  "public-topology.mjs"
);
const publicTopology = fs.readFileSync(publicTopologyPath, "utf8");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(
  /PUBLIC_NEXT_DIR='\.next-public'/.test(script),
  "restart_frontend_wsl.ps1 must keep .next-public as the hosted-public artifact"
);

assert(
  script.includes('STAGING_NEXT_DIR=".next-public.staging.`$`$"'),
  "PowerShell must preserve the Bash PID in the per-run staging artifact"
);

assert(
  script.includes('FAILED_NEXT_DIR=".next-public.failed.`$`$"'),
  "PowerShell must preserve the Bash PID in failed-artifact cleanup"
);

assert(
  /PREVIOUS_NEXT_DIR='\.next-public\.previous'/.test(script),
  "public frontend restart must keep a previous artifact for failed-swap restore"
);

assert(
  /NEXT_DIST_DIR="\`\$STAGING_NEXT_DIR"\s+npm run build:public/.test(script),
  "public frontend build must target the staging artifact via NEXT_DIST_DIR"
);

assert(
  /if \[ ! -s "\`\$STAGING_NEXT_DIR\/BUILD_ID" \]/.test(script),
  "staged public artifact must be validated before swap"
);

assert(
  /mv "\`\$PUBLIC_NEXT_DIR" "\`\$PREVIOUS_NEXT_DIR"/.test(script) &&
    /mv "\`\$STAGING_NEXT_DIR" "\`\$PUBLIC_NEXT_DIR"/.test(script),
  "public frontend restart must swap staging into .next-public through a previous-artifact handoff"
);

assert(
  /restoring previous public artifact/.test(script) &&
    /mv "\`\$PREVIOUS_NEXT_DIR" "\`\$PUBLIC_NEXT_DIR"/.test(script),
  "failed swaps must restore the previous public artifact"
);

assert(
  !/rm\s+-rf\s+"\`\$PUBLIC_NEXT_DIR"/.test(script),
  "restart script must not delete .next-public directly; build into staging and swap instead"
);

assert(
  /if \[ ! -s "\`\$PUBLIC_NEXT_DIR\/BUILD_ID" \]/.test(script),
  "final public artifact BUILD_ID must be validated before next start"
);

assert(
  /LYRA_PUBLIC_BUILD_ID/.test(publicTopology),
  "public-topology.mjs must persist public build id metadata into the artifact"
);

assert(
  /fs\.writeFileSync\(publicBuildIdPath,\s*`\$\{env\.NEXT_PUBLIC_BUILD_ID\}\\n`/.test(
    publicTopology
  ),
  "public build must write NEXT_PUBLIC_BUILD_ID into artifact metadata"
);

assert(
  /if \(command === "start"\)[\s\S]*?readArtifactBuildId\(\)/.test(publicTopology),
  "public start must read build id from artifact metadata"
);

assert(
  !/NEXT_PUBLIC_BUILD_ID:\s*process\.env\.NEXT_PUBLIC_BUILD_ID\s*\|\|\s*gitShortSha\(\)/.test(
    publicTopology
  ),
  "public start must not mint topology build_id from current git when artifact metadata is absent"
);

assert(
  /if \[ ! -s "\`\$PUBLIC_NEXT_DIR\/LYRA_PUBLIC_BUILD_ID" \]/.test(script),
  "restart script must refuse unverifiable public artifacts without LYRA_PUBLIC_BUILD_ID"
);

assert(
  /EXPECTED_PUBLIC_BUILD_ID="\`\$\(cat "\`\$PUBLIC_NEXT_DIR\/LYRA_PUBLIC_BUILD_ID"\)"/.test(
    script
  ),
  "restart script must load expected public build id from artifact metadata"
);

assert(
  /topology\.get\("build_id"\) != expected_build_id/.test(script),
  "restart script must fail when served topology build_id differs from artifact metadata"
);

assert(
  /refusing to deploy from a dirty tracked or untracked tree/.test(script),
  "restart script must fail closed before deploying a dirty source tree"
);

assert(
  /git -C \$repoRoot\.Path status --porcelain --untracked-files=all/.test(script),
  "native Git must own the pre-deploy clean-tree decision"
);

assert(
  (script.match(/diff --ignore-space-at-eol --quiet/g) || []).length >= 2 &&
    (script.match(/ls-files --others --exclude-standard/g) || []).length >= 2,
  "WSL guards must ignore line-ending-only drift while rejecting tracked content and untracked files"
);

assert(
  /public build mutated tracked or untracked source files/.test(script),
  "restart script must fail before swap when a public build leaves source mutations"
);

assert(
  script.includes('$bashScript = $bashScript.Replace("`r`n", "`n")'),
  "restart script must normalize generated Bash payloads to LF before WSL execution"
);

assert(
  /snapshotPublicBuildInputs\(frontendRoot\)/.test(publicTopology) &&
    /child\.on\("error",[\s\S]*?restoreBuildInputs\(\)/.test(publicTopology) &&
    /child\.on\("exit",[\s\S]*?restoreBuildInputs\(\)/.test(publicTopology),
  "public build wrapper must restore guarded source inputs on spawn errors and exits"
);

const guardFixture = fs.mkdtempSync(
  path.join(os.tmpdir(), "lyra-public-build-source-guard-")
);
try {
  const tsconfigPath = path.join(guardFixture, "tsconfig.json");
  const nextEnvPath = path.join(guardFixture, "next-env.d.ts");
  const originalTsconfig = Buffer.from('{"compilerOptions":{}}\r\n', "utf8");
  fs.writeFileSync(tsconfigPath, originalTsconfig);

  const snapshot = snapshotPublicBuildInputs(guardFixture);
  fs.writeFileSync(tsconfigPath, '{"include":["generated/types"]}\n');
  fs.writeFileSync(nextEnvPath, "// generated by build\n");

  restorePublicBuildInputs(snapshot);

  assert(
    fs.readFileSync(tsconfigPath).equals(originalTsconfig),
    "source guard must restore existing build inputs byte-for-byte"
  );
  assert(
    !fs.existsSync(nextEnvPath),
    "source guard must remove build inputs that did not exist before the build"
  );
} finally {
  fs.rmSync(guardFixture, { recursive: true, force: true });
}

console.log(JSON.stringify({ ok: true, checked: "public_frontend_restart_contract" }));
