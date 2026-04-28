> **ARCHIVED 2026-04-29.** Apr 14 verification queue — entries either shipped + browser-verified or rolled into `LYRA_BUGS.md` / `dogfood_findings_living.md`. Browser-verify discipline now lives in `memory/feedback_verification_gates.md`. Kept for the historical record; do not edit.

# Post-launch verification queue

Commits that shipped with automated gates green but **without** operator browser-verification. Walk each checklist before the next major ship — do not close an entry without a dated operator confirmation.

Related rule: `memory/feedback_verification_gates.md` §9 "Browser verify (HARD GATE for UI commits)". Entries land here when the operator is unavailable at commit time OR when verification was deferred under explicit operator sign-off. Nothing else.

---

## Status taxonomy

| Status | Meaning |
|--------|---------|
| PENDING | Commit landed, automated gates passed, operator has not yet walked the flow |
| IN_PROGRESS | Operator actively walking the checklist |
| PASS | Checklist complete, operator confirmed on dated note |
| FAIL | Defect found during walk — must be fixed and a new entry opened for the fix commit |

---

## Queue

### Settings page — commit `604580f` (two-stage delete account + anonymized research retention)

- **Status:** PENDING
- **Landed:** 2026-04-13
- **Route:** `/settings`
- **Author verification claim:** automated gates green (tsc, backend imports, endpoint smoke). NO operator browser-walk. Operator unavailable at commit time; admitted as a gap during the April 14 alignment audit.

**Export JSON checklist (3 steps):**
1. Click **Export JSON** in the Export card → file downloads as `lyra-export-YYYY-MM-DD.json`, no browser console error.
2. Open the downloaded file → JSON is well-formed and contains non-empty `tasks`, `sessions`, `reflections` arrays for the logged-in user.
3. Rename or move the file → re-open the Settings page → click **Export JSON** again → download succeeds a second time (no stuck `exporting` state).

**Delete account checklist (12 steps — do NOT complete on a live account; use a seeded throwaway user):**
1. Click **Delete account** → modal opens at Stage 1 with the red "Permanently delete your account" title.
2. Data summary populates within ~1 s — task/session/reflection counts render; "Loading data summary..." is not left stuck.
3. If the user has Notion enabled, the Notion-sync-state bullet is present; if not, it is absent.
4. The research-retention checkbox defaults to **checked** (`retainForResearch: true`).
5. The acknowledgment checkbox defaults to **unchecked**; **Continue** button is disabled until it is ticked.
6. Click **Export data first →** inline link → export download fires while the modal stays open.
7. Tick acknowledgment → **Continue** enables → click it → Stage 2 appears.
8. Stage 2 shows the email masked: first two chars + `*` pad + `@domain` (e.g. `al*****@example.com`) — NOT the full address.
9. The email input is empty and autofocused. **Permanently delete account** is disabled.
10. Type the email incorrectly → button stays disabled. Type it correctly → button enables.
11. Click **Back** → Stage 1 returns with acknowledgment state preserved; click **Continue** → Stage 2 returns with email input cleared.
12. Type the correct email → click **Permanently delete account** → Stage 3 spinner appears → on success, user is signed out and redirected to `/`. A fresh sign-in attempt rejects the credentials (user row is truly gone or anonymized per the checkbox).

**What to do with the result:**
- If all 15 steps pass → mark this entry **PASS** with the operator's initials and date, and move the block to an "Archived" section below.
- If any step fails → mark **FAIL**, open a LYR-* bug with the step number, fix, and open a new PENDING entry for the fix commit.

---

## Archived (PASS)

*(none yet)*
