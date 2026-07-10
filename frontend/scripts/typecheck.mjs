import { spawnSync } from "node:child_process";
import { rmSync } from "node:fs";
import { resolve } from "node:path";

const root = process.cwd();
const tscBin = resolve(root, "node_modules", "typescript", "bin", "tsc");
const tscArgs = ["--noEmit", "--pretty", "false"];

function runTsc() {
  return spawnSync(process.execPath, [tscBin, ...tscArgs], {
    cwd: root,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function writeResult(result) {
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
}

function hasLocalNextTypesMissingFile(output) {
  return (
    (output.includes("TS6053") || output.includes("TS2307")) &&
    /(?:^|[\\/])\.next[\\/]types[\\/]/m.test(output)
  );
}

const first = runTsc();
if (first.status === 0) {
  writeResult(first);
  process.exit(0);
}

const firstOutput = `${first.stdout ?? ""}${first.stderr ?? ""}`;
if (hasLocalNextTypesMissingFile(firstOutput)) {
  console.warn(
    "Local .next/types appears incomplete; removing generated local route types and rerunning typecheck.",
  );
  rmSync(resolve(root, ".next", "types"), { recursive: true, force: true });
  rmSync(resolve(root, "tsconfig.tsbuildinfo"), { force: true });
  const second = runTsc();
  writeResult(second);
  process.exit(second.status ?? 1);
}

writeResult(first);
process.exit(first.status ?? 1);
