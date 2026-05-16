# 24h Admin Bug Sweep

**Updated:** 2026-05-16  
**Owner:** Operator (Ali)  
**Tracker:** GitHub Issues is active; `archive/LYRA_BUGS.md` is historical plus durable sync notes.

This is a lightweight operator routine, not backend automation. User bug reports
already reach the operator through Telegram and the in-app feedback queue. Once
per day, the operator batches the non-critical reports and asks Codex to turn
them into clean, deduplicated GitHub issue state.

---

## P0 Immediate Escalation

P0 reports do **not** wait for the 24h sweep. Handle them immediately.

P0 includes:

- cross-user data leak or privacy breach
- auth/sign-in outage
- production unavailable
- account deletion/export failure
- exposed secret/token
- data corruption or irreversible user-data loss
- core task/timer flow unusable for active users

For P0, send Codex the redacted report immediately and ask for incident triage,
root-cause analysis, issue documentation, and fix planning/implementation as a
separate urgent task.

---

## Privacy Rule Before Codex Or GitHub

Before pasting reports into Codex or GitHub, redact:

- raw tokens, API keys, bearer strings, cookies, refresh tokens, private URLs
- email addresses and unnecessary personal identifiers
- screenshots with personal data
- private user task/deadline/calendar content unless it is essential to the bug
- stack traces or request payloads that include secrets

Use stable placeholders instead:

```text
[user A]
[user B]
[redacted email]
[redacted token]
[private task title]
[private URL]
```

If a reproduction needs private content, paraphrase the structure rather than
copying the content.

---

## Daily Sweep Workflow

Every 24h:

1. Gather non-P0 reports from Telegram, `/v1/admin/feedback`, and direct user
   messages.
2. Redact the batch using the privacy rule above.
3. Send Codex the daily prompt below.
4. Codex dedupes against GitHub Issues and `archive/LYRA_BUGS.md`.
5. Codex creates or updates canonical GitHub issues.
6. Codex comments on existing issues rather than creating duplicates.
7. Codex updates `archive/LYRA_BUGS.md` only for durable tracker changes or
   fixed issues.

---

## GitHub Issue Rules

- Every real bug gets exactly one canonical GitHub issue.
- Title format: `[LYR-NNN] concise symptom`.
- Always apply the `bug` label.
- Add `duplicate`, `documentation`, or `wontfix` only when appropriate.
- If the report duplicates an existing issue, do not create a new issue.
- If an accidental duplicate exists, comment on it and close it into the
  canonical issue.

Issue body should include:

- user-visible symptom
- redacted source report date/context
- affected surface
- suspected subsystem
- priority
- reproduction clues
- current status

---

## Priority Rules

| Priority | Meaning |
| --- | --- |
| P0 / critical | Privacy, auth, production availability, irreversible data loss, or active-user core-flow outage. Immediate escalation. |
| P1 / high | User-facing core flow broken: onboarding, task create, timer start/stop, deadlines, Moodle/Calendar sync, account settings. |
| P2 / medium | Confusing but recoverable behavior, stale UI, incorrect labels, partial sync, non-blocking notification failure. |
| P3 / low | Cosmetic, copy, docs, known third-party limitation, rare operator-only annoyance. |

---

## Daily Prompt

```text
Run the 24h admin bug sweep.

Reports since last sweep, already redacted:
[paste reports]

For each report:
1. dedupe against GitHub issues and LYRA_BUGS.md
2. inspect relevant code/docs if needed
3. assign priority
4. create or update GitHub issues
5. tell me what was filed, merged, ignored, or needs reproduction

P0 reports were/will be sent separately immediately.
```

---

## Codex Output Contract

At the end of a sweep, Codex should report:

- issues created
- issues updated
- reports merged into existing issues
- reports ignored as non-bugs or already fixed
- reports needing more reproduction detail
- any P0 discovered during the sweep and escalated out of batch handling

No implementation should be bundled into the sweep unless the operator
explicitly asks for the fix after triage.
