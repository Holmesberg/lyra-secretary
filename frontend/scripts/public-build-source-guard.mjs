import fs from "node:fs";
import path from "node:path";

const GUARDED_BUILD_INPUTS = ["tsconfig.json", "next-env.d.ts"];

export function snapshotPublicBuildInputs(
  frontendRoot,
  relativePaths = GUARDED_BUILD_INPUTS
) {
  return relativePaths.map((relativePath) => {
    const absolutePath = path.join(frontendRoot, relativePath);
    if (!fs.existsSync(absolutePath)) {
      return { absolutePath, existed: false };
    }

    const stat = fs.statSync(absolutePath);
    return {
      absolutePath,
      existed: true,
      contents: fs.readFileSync(absolutePath),
      mode: stat.mode,
    };
  });
}

export function restorePublicBuildInputs(snapshot) {
  for (const entry of snapshot) {
    if (!entry.existed) {
      fs.rmSync(entry.absolutePath, { force: true });
      continue;
    }

    fs.writeFileSync(entry.absolutePath, entry.contents);
    fs.chmodSync(entry.absolutePath, entry.mode);
  }
}
