# Trusted-Alpha Security Blueprint

**Status:** operational security blueprint.
**Created:** 2026-05-17.
**Scope:** trusted-alpha access control, auditability, data isolation, provider
failure handling, and future scalability gates.
**Governance:** operational/security governance. This document does not change
research doctrine, clean-data admission, or behavioral-instrumentation claims.

This blueprint defines the minimum security posture LyraOS needs before wider
trusted-alpha use, public beta, or institutional review.

---

## 1. Hard Invariants

Security audit rows are governance records only.

```text
SecurityAuditEvent must never become behavioral telemetry.
```

Security audit rows must not feed:

- productivity inference,
- execution modeling,
- Cortex,
- clean-data profiles,
- adaptive scheduling,
- user behavior analysis,
- archetype inference,
- or research outcome claims.

Provider outages must reduce functionality, not security.

```text
Provider failure must degrade functionality, not weaken authentication or user scoping.
```

If Moodle, Google Calendar, Notion, or another provider is unavailable or
rejects credentials, Lyra may pause sync, surface reconnect guidance, preserve
existing connection state where safe, or retry later. It must not bypass bearer
identity, fall back to operator scope, widen user queries, or accept
provider-returned identity as a substitute for Lyra user scoping.

## 2. Access-Control Model

Trusted alpha has two roles:

| Role | Meaning |
| --- | --- |
| `user` | normal account, scoped to own data |
| `operator` | trusted-alpha operator/admin/debug role |

This pass intentionally does not implement full RBAC. Operator-only surfaces
remain binary gates.

Canonical backend helpers:

- `require_current_user_scope()`
- `require_authenticated_user()`
- `require_operator_user()`
- `operator_user_from_scope()`

Sensitive routes must use the shared operator helper rather than repeating
ad hoc checks.

Operator-only surfaces include:

- admin dashboards,
- alpha funnel,
- JARVIS endpoints,
- output-surface diagnostics,
- Cortex diagnostics,
- behavioral-signature diagnostics,
- exposure-policy effect-log writes,
- feedback triage,
- operator Telegram mirror,
- environment-invariant diagnostics.

## 3. Runtime Identity Authority

Runtime HTTP identity authority is:

```text
Authorization: Bearer <backend JWT>
```

The bearer token is decoded by `UserScopeMiddleware`, which resolves the Lyra
`User` row and sets the request-scoped user id.

`X-User-Id` is test-only. It may authenticate requests only when the test
harness explicitly sets `app.state.allow_test_identity_header = True`.

Rules:

- bearer identity beats `X-User-Id`,
- missing identity fails closed,
- invalid bearer fails closed,
- database unavailability during bearer resolution fails closed as a platform
  degradation (`503`), not as an expired-token/auth-rotation signal,
- runtime `X-User-Id` fails closed,
- no route may silently fall back to `user_id=1`,
- JWT secret strength is enforced in public/prod topology.

## 4. Data Isolation

User-owned ORM queries are protected by `app.db.scoping.install_scoping`, which
adds request-user predicates to models with `user_id`.

This is necessary but not sufficient.

Raw SQL bypasses the ORM scoping hook. Any `db.execute(text(...))` touching
user-owned tables must include an explicit user predicate or be listed in a
narrow static-test allowlist with a reason.

Protected user-owned surfaces include:

- tasks,
- stopwatch sessions,
- deadlines,
- academic pressure,
- Moodle connection state,
- feedback submissions and admin triage,
- exposure decisions/renders/acks,
- export/delete flows,
- calendar outcomes,
- correction and prediction logs.

Cross-user access must fail as 403 or 404 and must not mutate the target row.
Where the backend can identify an explicit cross-user attempt, it should write
a `cross_user_access_blocked` security audit event.

## 5. Operator Boundary

Operator routes are allowed to disable request user scoping only after an
operator check has succeeded.

The safe pattern is:

```text
require operator
remember original user scope
temporarily clear scope for aggregate/operator query
restore original user scope in finally
```

Operator tools must avoid exporting user secrets. Operator-facing alerts and
diagnostics should summarize counts, status, provider names, and hashed or
redacted user references rather than raw private content.

## 6. Security Audit Taxonomy

`SecurityAuditEvent` is append-only in product code.

Fields:

- `event_id`,
- `actor_user_id`,
- `user_id`,
- `event_type`,
- `surface`,
- `target_type`,
- `target_id`,
- `status`,
- `ip_hash`,
- `user_agent_hash`,
- `redacted_metadata`,
- `created_at`.

Allowed event families:

- `auth_failure`,
- `test_identity_header_denied`,
- `user_provisioned`,
- `operator_access_denied`,
- `auth_required_denied`,
- `provider_connected`,
- `provider_disconnected`,
- `account_export`,
- `account_delete_requested`,
- `cross_user_access_blocked`,
- production secret/topology guard failures where capturable.

Forbidden event families:

- task execution telemetry,
- session timing telemetry,
- productivity scoring,
- behavioral labels,
- attention/focus inference,
- learning/completion inference,
- clean-data eligibility.

## 7. Redaction Rules

Security audit rows must never store:

- task titles,
- notes,
- emails,
- OAuth payloads,
- refresh/access tokens,
- Moodle Web Services tokens,
- Moodle iCal URLs or authtokens,
- cookies,
- raw provider URLs,
- feedback body text,
- behavioral session content.

Request IP and user-agent are hashed before storage. Metadata is recursively
redacted by sensitive key and by sensitive string patterns.

Security audit logging is best-effort. A failed audit write must not weaken
auth, authorization, scoping, or provider token handling.

Application logs are part of the redaction surface. HTTP client libraries must
not emit raw provider URLs that contain bot tokens, OAuth values, Moodle
tokens, authtokens, or signed URLs.

## 8. Provider Failure Boundary

Provider failure classes:

| Failure | Product behavior | Security behavior |
| --- | --- | --- |
| Moodle iCal 503/rate limit | retry later, keep connection | preserve user scope |
| Moodle WS invalid token | stop submission inference, ask reconnect | do not infer completion |
| Google Calendar auth failure | pause calendar sync, surface reconnect | do not widen calendar reads |
| Notion unavailable | degrade Notion sync | do not affect task ownership |
| Provider timeout | mark sync degraded | do not bypass auth |
| Lyra DB unavailable during auth | return temporary platform failure | fail closed; do not accept fallback identity |

Provider failures should not page as Lyra product failures unless widespread
or persistent. Scheduler, bootstrap, and database failures are Lyra platform
failures and deserve immediate triage when repeated.

Every operator alert must include:

- affected provider/subsystem,
- affected user count or redacted/hash user reference,
- retry behavior,
- whether user action is needed,
- whether data integrity is at risk.

## 9. Current Deployment Topology

Current trusted-alpha topology:

- `https://lyraos.org` frontend,
- `https://api.lyraos.org` backend,
- Cloudflare Tunnel ingress to local services,
- Next.js production build served by `next start`,
- FastAPI backend in Docker,
- Redis in Docker,
- Supabase Postgres primary DB.

Topology verification is part of security verification. Browser smoke is not
trusted until the runtime topology check passes for the intended local or
public mode.

Canonical topology references:

- `runtime_topology.json`,
- `docs/deployment_architecture.md`,
- backend `/v1/health/topology`,
- frontend `/api/topology`.

## 10. Trusted-Alpha Checklist

Required before trusted-alpha expansion:

- bearer/JWT runtime identity works,
- `X-User-Id` remains test-only,
- non-operators get 403 on operator/admin/JARVIS surfaces,
- unauthenticated runtime requests get 401,
- bearer identity beats `X-User-Id`,
- raw SQL user-scope scan passes,
- adversarial multi-user isolation suite passes,
- audit redaction tests pass,
- provider failures preserve auth and user scoping,
- topology verifier passes for the intended runtime,
- browser smoke passes with at least two accounts.

## 11. Public-Beta Upgrade Checklist

Before public beta, Lyra should add:

- explicit account/session management review,
- stronger rate limiting on auth and mutation routes,
- CSRF review for browser-origin mutation flows,
- encryption-at-rest pass for provider credentials,
- structured secret rotation playbook,
- audit retention policy,
- operator access review workflow,
- privacy policy and data deletion SLA,
- incident-response runbook,
- dependency vulnerability scanning,
- backup/restore drill,
- production observability dashboard,
- provider-reconnect UX for every supported adapter.

## 12. Future Institutional Requirements

Before institutional or organization use, Lyra will need:

- tenant boundary model,
- role-based access control beyond binary operator,
- organization admin vs individual worker separation,
- privacy-preserving aggregation defaults,
- data-processing agreement review,
- audit export and retention controls,
- consent and revocation flows,
- policy for manager-visible vs worker-private data,
- anti-bossware product review,
- independent security review or penetration test,
- provider-specific security assessment for LMS/workplace adapters.

Institutional scale must preserve the same invariant:

```text
Lyra can help people and teams understand execution reality.
Lyra must not become surveillance infrastructure.
```
