---
authority: active-contract
may_authorize_code: false
runtime_owner: none
created: 2026-06-29
---

# Identity And Scoping Ownership

Status: S1a safety-rail contract. This document names owners and forbidden
authority drift. It does not authorize schema changes, auth-provider changes,
or new identity behavior.

## Core Rule

```text
Identity resolution, user provisioning, and request scoping are separate
authorities.
```

The active owner map is:

| Surface | Owner | Scope |
|---|---|---|
| IdentityResolver | `backend/app/main.py` and `backend/app/api/deps.py` current middleware/dependency boundary | Resolve bearer identity and test-only identity. |
| UserProvisioningService | Current first-login creation path, to be extracted later | Create the local user row after trusted auth identity resolves. |
| RequestUserContext | `backend/app/db/scoping.py` plus request context vars | Hold request-scoped user state for ORM filters and endpoint use. |
| Runtime topology | `runtime_topology.json` | Decide whether local/public auth and API origins agree. |

## Test-Only Identity Boundary

`X-User-Id` is test-only and operator-tooling-only. It must remain impossible
in normal runtime unless the existing test-mode guard explicitly allows it.

Rules:

- production browser traffic must use normal session/bearer identity;
- test-only headers must fail closed when test identity mode is disabled;
- request scoping must never silently fall back to user `1`;
- operator/browser verification must use real cookies when checking runtime
  behavior;
- export/delete and operator reads must preserve the resolved request user.

## Parked Extraction

Future R4/R5 extraction may introduce explicit modules named
`IdentityResolver`, `UserProvisioningService`, and `RequestUserContext`.
That extraction is behavior-preserving only and must not change auth semantics
without a separate big-decision stop.
