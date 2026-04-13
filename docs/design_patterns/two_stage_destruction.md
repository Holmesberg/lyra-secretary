# Two-Stage Destruction Pattern

Irreversible destructive actions require two sequential stages: comprehension, then identity verification. Neither stage alone is sufficient. The pattern prevents both accidental destruction (stage 1 catches) and unauthorized destruction (stage 2 catches).

**Reference implementation:** Delete account flow, Settings page (April 14, 2026).

---

## Stage 1: Comprehension

The user must understand what they are about to destroy before they can proceed.

Requirements:
- **Scope summary** — what gets destroyed, with counts where available ("12 tasks, 8 sessions, and all reflections will be permanently deleted")
- **Irreversibility statement** — explicit text: "This cannot be undone"
- **Non-destructive alternative** — if one exists, link to it prominently ("Export your data first" link in the delete account case)
- **Explicit acknowledgment** — checkbox or equivalent interaction confirming the user read the scope. Button to proceed is disabled until acknowledgment is given
- **No action taken** — stage 1 is purely informational. Nothing is destroyed, no API call fires

## Stage 2: Identity Verification

Separated from comprehension. The user must prove they are who they claim to be.

Requirements:
- **Identity input** — type email address, enter password, or equivalent identity proof. Must match the account's stored identity
- **Verification is server-side** — the frontend sends the verification value; the backend confirms the match and rejects on mismatch
- **Final action button** — destructive-styled (red), only enabled when verification input is non-empty and stage 1 acknowledgment is complete
- **Error handling** — on verification failure, show inline error, do not close the modal, do not reset stage 1 acknowledgment

## Structural Rules

- **All stages allow reversal** — Cancel button available at every stage, returns to the non-destructive state
- **No modal-on-modal stacking** — if the trigger is already inside a modal, use inline stage progression within the same modal, not a nested modal
- **Destructive action fires only on final confirmation** — a single API call after both stages are satisfied. No partial destruction on stage 1 completion
- **Loading state on final action** — button shows progress indicator, all inputs disabled, Cancel disabled during the API call

## Future Applications

This pattern applies to any operation where:
1. The action is irreversible or very expensive to reverse
2. The blast radius extends beyond a single entity
3. The user might reach the action through habitual clicking without reading

Candidates:
- **Bulk task delete** — if shipped. Stage 1 shows count + titles of affected tasks
- **Account migration** — stage 1 shows what transfers and what doesn't
- **Data import-overwrite** — stage 1 shows what existing data will be replaced
- **Archive operations** — if archive means "remove from active view + analytics exclusion"

## Anti-patterns

- **Single "Are you sure?" dialog** — comprehension and verification collapsed into one step. Users habituate to clicking "Yes" without reading. Does not prove identity
- **Confirm-by-retyping the action name** — proves the user can type, not that they understand the scope. "Type DELETE to confirm" is cargo-cult safety
- **Soft delete masquerading as hard delete** — if the UI says "permanently deleted" but the backend soft-deletes, the trust contract is violated in both directions: users who want permanence don't get it, users who accidentally delete expect recovery that isn't surfaced
- **Timeout-based undo instead of prevention** — "Undo within 30 seconds" is appropriate for low-stakes actions (task creation, reschedule). It is not appropriate for account deletion or bulk destruction. Prevention > recovery for high-stakes actions
