#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");

const onboarding = read("frontend/components/onboarding-flow.tsx");
const layout = read("frontend/app/(app)/layout.tsx");
const users = read("backend/app/api/v1/endpoints/users.py");
const browser = read("scripts/browser_holmesberg_product_loop_dogfood.mjs");
const wrapper = read("scripts/run_holmesberg_product_loop_dogfood.ps1");

const skipStart = onboarding.indexOf("async function handleSkip()");
const skipEnd = onboarding.indexOf("\n  return (", skipStart);
assert(skipStart >= 0 && skipEnd > skipStart, "onboarding skip handler must remain inspectable");
const skipHandler = onboarding.slice(skipStart, skipEnd);
const requestIndex = skipHandler.indexOf('await api("/v1/users/me/skip-onboarding"');
const completionIndex = skipHandler.indexOf("onSkipped()");
assert(requestIndex >= 0, "skip must await the canonical backend acknowledgement");
assert(
  completionIndex > requestIndex,
  "session bypass must happen only after the backend acknowledges the skip",
);
assert(
  skipHandler.includes("catch (skipError)")
    && skipHandler.includes("setSkipping(false)"),
  "failed skip must remain retryable",
);
assert(
  onboarding.includes('data-testid="onboarding-brain-dump-skip"')
    && onboarding.includes('data-testid="onboarding-brain-dump-error"')
    && onboarding.includes('role="alert"'),
  "skip and retryable error must expose stable mounted-browser selectors",
);

assert(
  users.includes('if user.onboarding_completed_at is None:')
    && users.includes('invalidate_me(user.user_id)  # onboarding_completed_at flips'),
  "backend skip must remain first-write-wins and invalidate only on the first write",
);
assert(
  layout.includes('const ONBOARDING_SKIP_SESSION_KEY = "lyra:onboarding-skip-this-session"')
    && layout.includes("!onboardingSkippedThisSession")
    && layout.includes("(!me.onboarding_completed_at || !me.has_active_task_history)"),
  "skip must preserve session-only bypass and next-visit re-engagement for empty accounts",
);

assert(
  browser.includes('const onboardingSkipProofOnly = args.get("onboarding-skip-proof-only") === "true"')
    && browser.includes("async function runOnboardingSkipProof(")
    && browser.includes('proof_scope: "onboarding_skip_failure_retry_fixture"'),
  "browser harness must retain focused failure-then-retry proof",
);
assert(
  wrapper.includes("[switch]$OnboardingSkipProofOnly")
    && wrapper.includes('$args += "--onboarding-skip-proof-only"'),
  "PowerShell wrapper must expose the focused skip proof",
);

console.log("onboarding skip contract: ok");
