import playwright from "../frontend/node_modules/playwright/index.js";
import fs from "node:fs/promises";

const { chromium } = playwright;
const failures = [];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
page.on("requestfailed", (request) => {
  failures.push({
    url: request.url(),
    failure: request.failure()?.errorText ?? "unknown",
  });
});
page.on("response", (response) => {
  if (response.status() >= 400 && response.url().includes("/_next/")) {
    failures.push({ url: response.url(), status: response.status() });
  }
});

await page.goto("https://lyraos.org/pulse", { waitUntil: "domcontentloaded", timeout: 60_000 });
await page.waitForTimeout(8_000);
await page.screenshot({ path: "tmp/public-recovery-pulse.png", fullPage: true });
await browser.close();

const relevantFailures = failures.filter((item) => {
  if (item.url.includes("cloudflareinsights")) return false;
  if (item.url.includes("?_rsc=") && item.failure === "net::ERR_ABORTED") return false;
  return true;
});
await fs.writeFile(
  "tmp/public-recovery-check.json",
  JSON.stringify({ ok: relevantFailures.length === 0, failures: relevantFailures }, null, 2)
);
if (relevantFailures.length) {
  console.error(relevantFailures);
  process.exit(1);
}
