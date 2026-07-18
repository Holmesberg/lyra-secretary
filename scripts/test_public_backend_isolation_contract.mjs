#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const composePath = path.join(repoRoot, "docker-compose.yml");
const restartPath = path.join(repoRoot, "scripts", "restart_backend_public.ps1");
const rebootPath = path.join(repoRoot, "scripts", "start_public_after_reboot.ps1");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function isolationFindings(config) {
  const backend = config?.services?.backend ?? {};
  const command = Array.isArray(backend.command)
    ? backend.command.join(" ")
    : String(backend.command ?? "");
  const volumes = Array.isArray(backend.volumes) ? backend.volumes : [];
  const findings = [];
  if (/--reload(?:\s|$)/.test(command)) findings.push("backend_reload_enabled");
  if (
    volumes.some(
      (volume) => volume?.type === "bind" && String(volume?.target) === "/app"
    )
  ) {
    findings.push("checkout_bound_to_public_app");
  }
  if (!backend.image) findings.push("public_image_name_missing");
  if (backend?.environment?.BUILD_ID !== "contract-test") {
    findings.push("backend_build_id_not_explicit");
  }
  if (backend?.build?.args?.BUILD_ID !== "contract-test") {
    findings.push("backend_image_build_id_not_explicit");
  }
  return findings;
}

const emptyEnvPath = path.join(os.tmpdir(), `lyra-compose-empty-${process.pid}.env`);
fs.writeFileSync(emptyEnvPath, "", "utf8");
let config;
try {
  const output = execFileSync(
    "docker",
    ["compose", "--env-file", emptyEnvPath, "-f", composePath, "config", "--format", "json"],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        BACKEND_BUILD_ID: "contract-test",
        DATABASE_URL: "sqlite:////app/data/contract.db",
        JWT_SECRET: "contract-test-secret-contract-test-secret",
        TELEGRAM_BOT_TOKEN: "",
        TELEGRAM_CHAT_ID: "",
        MOODLE_WS_TOKEN: "",
        MOODLE_WS_BASE_URL: "",
        MOODLE_WS_USERID: "",
      },
      stdio: ["ignore", "pipe", "pipe"],
    }
  );
  config = JSON.parse(output);
} finally {
  fs.rmSync(emptyEnvPath, { force: true });
}

assert(
  isolationFindings(config).length === 0,
  `public backend isolation findings: ${isolationFindings(config).join(", ")}`
);

const unsafeBind = structuredClone(config);
unsafeBind.services.backend.volumes.push({ type: "bind", source: ".", target: "/app" });
assert(
  isolationFindings(unsafeBind).includes("checkout_bound_to_public_app"),
  "negative fixture must reject a checkout bind at /app"
);

const unsafeReload = structuredClone(config);
unsafeReload.services.backend.command = ["uvicorn", "app.main:app", "--reload"];
assert(
  isolationFindings(unsafeReload).includes("backend_reload_enabled"),
  "negative fixture must reject public Uvicorn reload"
);

const missingBuildId = structuredClone(config);
delete missingBuildId.services.backend.environment.BUILD_ID;
assert(
  isolationFindings(missingBuildId).includes("backend_build_id_not_explicit"),
  "negative fixture must reject a public runtime without an explicit build id"
);

const restart = fs.readFileSync(restartPath, "utf8");
const reboot = fs.readFileSync(rebootPath, "utf8");
assert(
  restart.includes("-ApprovedPublicRestart switch"),
  "backend restart must fail closed without explicit approval"
);
assert(
  restart.includes("Refusing to deploy the public backend from a dirty tracked or untracked tree"),
  "backend restart must reject dirty source"
);
assert(
  restart.includes("Wait-ForDockerEngine") &&
    restart.includes("Docker Desktop did not become ready"),
  "backend restart must own Docker readiness for backend-only recovery"
);
assert(
  restart.includes('"build", "backend"') && restart.includes('"up", "-d", "--no-build"'),
  "backend restart must build before replacing the running container"
);
assert(
  restart.includes("Get-DockerImageBuildId") &&
    restart.includes("ConvertFrom-Json") &&
    restart.includes("org.lyraos.backend-build-id"),
  "no-build restart must parse the existing image build label structurally"
);
assert(
  !restart.includes("docker image inspect --format"),
  "backend image metadata must not depend on brittle Docker Go-template quoting"
);
assert(
  /\$expectedBuildId\s*=\s*Get-DockerImageBuildId\s+\$publicImage/.test(restart) &&
    /Reusing existing backend image build/.test(restart),
  "no-build recovery must preserve the deployed image build rather than require source HEAD"
);
assert(
  restart.includes("Restore-PreviousBackend") && restart.includes("lyra-backend-public:previous"),
  "backend restart must preserve and restore the previous image"
);
assert(
  restart.includes("Backend topology did not serve expected build id"),
  "backend restart must fail when the served build id does not match"
);
assert(
  reboot.includes("restart_backend_public.ps1") &&
    /ApprovedPublicRestart\s*=\s*\$true/.test(reboot),
  "reboot orchestration must use the authoritative approval-gated backend restart"
);
assert(
  reboot.includes("DockerWaitSeconds") && reboot.includes("DockerPollSeconds"),
  "reboot orchestration must delegate Docker readiness timing to backend recovery"
);
assert(
  reboot.includes("restart_frontend_wsl.ps1") &&
    reboot.includes("SkipPublicCheck"),
  "reboot orchestration must delegate frontend recovery to the authoritative atomic restart"
);
assert(
  !reboot.includes("npm run build:public") &&
    !/rm\s+-rf\s+["']?\$PUBLIC_NEXT_DIR/.test(reboot),
  "reboot orchestration must not duplicate or destructively replace frontend artifacts"
);

console.log(JSON.stringify({ ok: true, checked: "public_backend_isolation_contract" }));
