# Claude Code feedback-triage recipe

**Created:** 2026-04-28
**Owner:** Operator (Ali)
**Goal:** Turn the alpha-cohort feedback queue into a weekly autonomous-triage cycle without building webhook infrastructure.

---

## Why this exists

The alpha feedback widget (alembic 040) writes rows to `feedback` and emails/Telegrams operator on each submission. But when you accumulate 5-10 reports a week, manual triage drags. This recipe runs Claude Code on a schedule to summarize, categorize, and propose fixes — operator decides which to ship.

Zero infra: uses Claude Code's built-in `/schedule` command. No webhook, no SDK, no auth setup beyond Claude Code itself.

---

## The recipe

Paste this into Claude Code to set up a weekly Sunday triage:

```
/schedule
when: every Sunday at 10:00
do: Pull unresolved feedback from /v1/admin/feedback (operator-only,
    requires auth). For each row, classify:
      - quick-fix bug (1-line repro, <20-line patch): propose patch
      - design-choice bug (needs operator decision): summarize and ask
      - suggestion: bucket by theme; surface top 3 themes
      - confused: identify the surface that confused them; suggest
        microcopy changes
    Then post a single summary:
      - n unread, n acted_on this week
      - top 3 themes
      - 2-3 quick-fix patches you'd ship if I approved
      - 1-2 design-choice questions for me to answer
    Don't ship anything autonomously. Operator-approve every patch.
```

You can also run it ad-hoc:

```
/triage-feedback
```

(define this as a custom slash command pointing to the same prompt above)

---

## Operator-side guardrails

- **Don't auto-resolve.** Every status flip from `unread` → `acted_on` should be operator-driven, even when Claude proposes the patch. The `operator_note` field is for the operator's own context, not Claude's.
- **Watch for repeat reporters.** If user X submits 5 bugs in a week, that's a signal — either the surface they touch is genuinely broken OR they're feedback-loop power users who'd be great for a 30-min interview. Don't filter their reports out, but tag them.
- **Email yourself the summary.** Claude Code's `/schedule` output goes to your Claude Code thread. If you want it in your inbox too, ask Claude to also send via Resend.

---

## When to upgrade to a real webhook

If feedback hits 50+/week or you want sub-hour latency on patches:
- Build a `POST /v1/feedback` → AWS Lambda or Cloudflare Worker → Claude Agent SDK invocation
- Lambda passes the feedback row to a Claude agent in a sandboxed branch
- Agent commits to a `feedback-fix-{id}` branch + opens a PR for operator review
- Cost: ~1-2 days of setup + Claude Agent SDK billing

Until that volume, this recipe is enough.

---

## Schema reference (alembic 040)

```sql
SELECT feedback_id, kind, body, page_url, status, submitted_at
FROM feedback
WHERE status = 'unread'
ORDER BY submitted_at DESC;
```

Fields:
- `kind`: `'bug' | 'suggestion' | 'confused' | 'other'`
- `status`: `'unread' | 'read' | 'acted_on' | 'dismissed'`
- `error_context`: JSON array of last 3 client-side errors (path, status, message)
- `page_url`: URL where user submitted from

---

## Anti-pattern to avoid

Don't have Claude auto-commit fixes from feedback rows without operator review. Two reasons:
1. **Trust:** users who report bugs deserve to see operator engagement, not bot replies.
2. **Quality:** automated patches at 10am Sunday before coffee = bad code reaching prod.

The recipe explicitly says "don't ship anything autonomously." That's the line.
