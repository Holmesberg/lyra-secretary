# Integrations Architecture

Canonical reference for how Lyra connects to third-party systems. First
written 2026-04-22 alongside the incremental-OAuth refactor (see
`strategic_decisions_april_22.md`). Intended as the forward-looking
source of truth every new integration must match.

---

## Core principle: identity ≠ authorization

Lyra's sign-in asks Google for **identity only** — `openid email
profile`. Non-sensitive scopes, zero OAuth verification required, no
Google Cloud Console Testing-mode friction for new users.

Third-party feature access (Google Calendar, Notion, future Gmail /
Outlook / Slack / Drive) is acquired **incrementally** — user-triggered
per integration from **Settings → Integrations**. Each integration
requests its own scopes at its own consent moment. A user who never
connects Google Calendar never sees a calendar consent screen.

**Why this matters:**
- **Testing-mode friction is isolated.** Sensitive-scope integrations
  will still hit the 100-user test-user wall until the app is OAuth-
  verified, but only users who connect them are affected.
- **Consent is contextual.** The user sees "Connect Google Calendar"
  with a one-line description right before Google's consent screen —
  no "why is Lyra asking for my calendar at sign-in?" cognitive drag.
- **Scope minimization is enforceable.** Sign-in cookies never carry a
  sensitive-scope token. Unused integrations have no persistent
  refresh token to leak.

---

## User journey

```
  [Landing] → [Sign in with Google]            (identity only)
                     ↓
  [Seeded starter task, /today dashboard]
                     ↓
  Settings → Integrations tile "Connect"       (per integration)
                     ↓
  Google consent screen with requested scopes
                     ↓
  OAuth callback → backend persists token
                     ↓
  Tile flips to "Connected"; feature turns on everywhere
```

---

## Architecture — code layout

```
frontend/
  lib/
    integrations.ts                       ← registry + types + API client
    calendar.ts                            ← per-integration API (can merge later)
  components/
    integration-card.tsx                   ← one reusable card component
    integrations-section.tsx               ← section wrapper for Settings
  app/
    (app)/
      settings/page.tsx                    ← hosts <IntegrationsSection />
    api/
      integrations/
        google-calendar/
          connect/route.ts                 ← OAuth initiation
          callback/route.ts                ← OAuth completion
        <future-provider>/
          connect/route.ts
          callback/route.ts

backend/
  app/
    api/v1/endpoints/
      integrations.py                      ← GET /v1/integrations (status per provider)
      users.py                              ← existing per-provider store/clear endpoints
      calendar.py                           ← per-integration feature endpoints
    services/
      calendar_sync.py                     ← per-integration sync + token refresh
```

---

## Per-integration contract

Every integration must define six things:

| Element | Where | Notes |
|---------|-------|-------|
| Registry entry | `frontend/lib/integrations.ts` `INTEGRATIONS[]` | name, description, scopes, authShape, icon, `available` flag |
| Status mapping | `backend/app/api/v1/endpoints/integrations.py` `list_integrations` | returns `connected` / `disconnected` / `coming_soon` for this user |
| Connect flow | `frontend/app/api/integrations/<id>/connect/route.ts` (OAuth) or API-key / file-upload UI in the card | OAuth: signed `state`, Google-side redirect |
| Completion flow | `frontend/app/api/integrations/<id>/callback/route.ts` (OAuth) | validates state, exchanges code, email-match, stores refresh_token server-side |
| Disconnect | Backend `DELETE` endpoint + `disconnectIntegration(id)` dispatcher in `frontend/lib/integrations.ts` | clears local state; never revokes with the upstream provider |
| Research note | registry `researchNote` field | if the integration participates in a pre-registered research question (VT-23, IMP-3, etc.) |

---

## OAuth-shape integrations — detailed flow

### Initiate (connect route)
1. Read NextAuth session via `getToken()`. Reject if unauthenticated.
2. Mint short-lived **signed state** (10-min TTL, HS256 with
   `NEXTAUTH_SECRET`) carrying `{purpose, user_sub, email, nonce}`.
   Purpose claim must be unique per integration (`gcal_connect`,
   future `notion_connect`, etc.) so states can't cross-replay.
3. Build provider authorization URL with:
   - `client_id`, `redirect_uri`, `response_type=code`
   - **Only the scopes this integration needs** — no scope-bundling
   - `access_type=offline` (if refresh_token required)
   - `prompt=consent` (force consent screen → guaranteed refresh_token)
   - `include_granted_scopes=true` (don't re-prompt for already-granted scopes)
   - `login_hint={user.email}` (nudge correct account picker)
4. `NextResponse.redirect(...)` to the provider.

### Callback route
1. **Validate `error` param first** — Google redirects with `error=access_denied`
   when user cancels, `error=admin_policy_enforced` for Testing-mode blocks,
   etc. Surface as `/settings?integration_error=<id>&reason=<mapped>`.
2. Validate `state` signature + TTL + purpose claim. Reject on mismatch.
3. **User-swap guard:** state's `user_sub` must equal current session's
   `user_sub`. Prevents shared-device replay.
4. Exchange `code` for tokens at the provider's token endpoint. On
   failure, redirect to settings with `token_exchange_failed`.
5. **Account-match guard:** parse `id_token` payload (no signature
   check — see threat model below), verify `email` matches the
   signed-in user's email. Prevents "alice signed in, bob's data
   connected" when the user has multiple accounts with the provider.
6. Forward `refresh_token` to the backend via the per-integration
   store endpoint (e.g., `POST /v1/users/me/google-refresh-token`),
   authenticated with the user's backend JWT.
7. Redirect to `/settings?integration_connected=<id>`.

### id_token threat model
**We skip id_token signature verification** because:
- The token was delivered directly by Google over TLS in response to
  a request carrying our `client_secret`.
- We use only the `email` claim for cross-checking account identity
  against the already-verified NextAuth session.
- A forged id_token would require compromising our TLS channel to
  Google, which already compromises every other secret in flight.

When a future integration uses id_tokens for authoritative identity
(not just cross-check), upgrade to full signature + issuer + audience
validation against the provider's JWKS endpoint.

### State purpose uniqueness
States are signed with the same `NEXTAUTH_SECRET` across all
integrations. The `purpose` claim (`gcal_connect`, `notion_connect`,
etc.) segregates states so a stolen state for one provider can't be
replayed against another. When adding a new OAuth integration, pick a
purpose string no other route uses and enforce it in the callback.

---

## Non-OAuth shapes

### API-key integrations
User pastes an API key into an input on the Integration card. Frontend
POSTs to a per-integration endpoint that validates the key with one
test call against the provider, then stores it server-side. Same
pattern as OAuth except no browser redirect.

### File-upload / URL-subscription (ICS, CSV)
No credentials. The card's Connect affordance is a file picker or URL
input. Frontend parses locally or POSTs to the backend for parsing.
One-shot import is one state; URL subscription (periodic re-fetch)
adds a `last_sync_at` field.

---

## Research-integrity rules

**External data never enters the `task` table without an explicit
`external_source` marker.** This invariant was established for the
Google Calendar read-only integration (see
`strategic_decisions_april_21.md §6`) and applies to every future
integration.

- `external_event_outcome` table (alembic 027) is the template for
  "user-marked outcome on external data." Imported events go there,
  not in Task rows.
- If a future integration (Notion import, ICS) elects to persist
  imported items as Lyra plans, those rows MUST carry a non-null
  `external_source` field and every H1 query MUST filter with
  `WHERE external_source IS NULL`.
- No default-filling for research fields: imported items without
  user-provided readiness / reflection / scope stay NULL. Never
  fabricate data to fill required columns.

---

## Kill-criterion pre-registration

Every integration ships with a pre-defined exit condition measured
against a specific sample size. Examples:

- **Google Calendar (IMP-3):** at n≥20 connected users, D7 session
  ratio must be ≥1.25× the unconnected cohort, else the integration
  is retention-neutral.
- **GCal attendance self-report (VT-23):** at n≥20 connected users,
  ≥15% of past events must be marked within 7 days of elapsing,
  else signal is too sparse for research or retention use.

Kill criteria are written into `docs/strategic_decisions_<date>.md`
at ship time, not after. An integration with no pre-registered kill
criterion is a liability — it will accumulate maintenance cost with
no objective off-ramp.

---

## Security rules (non-negotiable)

1. **Server-side token handling only.** Refresh tokens never reach
   client JS. NextAuth cookies are encrypted; the only path from
   cookie to backend is the server-to-server hop inside a Next.js
   route handler.
2. **Never log tokens.** Not on success, not on failure, not in
   error traces. `console.warn` on token-exchange failure logs
   status + truncated body — no credentials.
3. **Plaintext in v1, Fernet at Phase 6+.** Current refresh tokens
   live plaintext in `user.google_refresh_token`. Blast radius is
   read-only calendar access per user. Fernet-at-rest encryption is
   tracked in `docs/building_phases.md` as a Phase 6+ security debt
   item; the refactor will add a key-rotation path at the same time
   (single-key encryption is only marginally better than plaintext).
4. **401 → clear local copy.** If the provider returns 401, clear
   Lyra's stored token and flip UI state to Disconnected. Do not
   attempt silent refresh beyond google-auth's own refresh path.
5. **Disconnect never revokes upstream.** Disconnect clears Lyra's
   copy only. Users visit the provider's own permissions page to
   revoke globally. Document this on the card.

---

## UI conventions

### Status chip colors
- **Connected** — signal (cyan) accent
- **Disconnected** — dust (muted) accent
- **Coming soon** — void-2 / dust-deep (dim) accent

### Preview tiles
Integrations with `available: false` render as "Coming soon" with a
short roadmap note (`comingSoonNote: "Shipping Phase 7"`). The purpose
is to communicate that Lyra is more than a one-integration product,
and to give users a queue they can look forward to — not to overload
the surface.

### Scope disclosure
Every OAuth card has a "View permissions requested" toggle that
reveals the raw scope strings in monospace. Users who care can
inspect; users who don't see a clean card.

### Callback feedback banners
The callback route redirects to `/settings?integration_connected=<id>`
or `/settings?integration_error=<id>&reason=<x>&detail=<optional>`.
Settings reads these once on mount, displays a dismissible banner,
and cleans the URL so a page refresh doesn't replay the banner.

Every error reason has a human copy in
`components/integrations-section.tsx` `ERROR_COPY`. Adding a new
error reason means adding to both that map and the list of reasons
the callback route can emit.

---

## Adding a new integration — checklist

- [ ] Add registry entry to `frontend/lib/integrations.ts`
  (name, description, scopes, `available`, monogram, monogramClass)
- [ ] Add status branch to `backend/app/api/v1/endpoints/integrations.py`
- [ ] OAuth: create `frontend/app/api/integrations/<id>/{connect,callback}/route.ts`
  with unique `purpose` claim
- [ ] API-key: extend `IntegrationCard` with the appropriate input UI
  and a `POST /v1/integrations/<id>/token` endpoint
- [ ] File: add file-picker UI + `POST /v1/integrations/<id>/import`
- [ ] Add backend store/clear endpoints if new columns are needed
- [ ] Add dispatch branch in `disconnectIntegration()` in
  `frontend/lib/integrations.ts`
- [ ] Register Google Cloud Console redirect URI (or provider
  equivalent) for the new callback
- [ ] Document in `docs/strategic_decisions_<date>.md` with kill
  criterion
- [ ] Append entry to `docs/project_history.md`
- [ ] If integration participates in research, add `researchNote`
  and tie to a VT-NN in `MANIFESTO.md`
- [ ] Ensure external data stays out of `task` unless marked with
  `external_source`

---

## Known pitfalls (for future integrations)

| Pitfall | Source | Prevention |
|---|---|---|
| External event id with `:` crashes Schedule-X | LYR-102 (2026-04-21) | All external ids must match `[a-zA-Z_][a-zA-Z0-9_-]*` |
| Notion date property double-TZ conversion | LYR-068 (open) | Write dates to Notion without offsets; let Notion render in its own TZ config |
| Plaintext refresh_token in v1 | migration 026 | Document as Phase 6+ security debt; never log |
| `google_id` placeholder backfill | LYR-091 | For OAuth integrations that key on `sub`, backfill real value on first real sign-in (Phase 9) |
| Single-timezone alpha blocks multi-region | TIMEZONE CONTRACT | Naked Cairo-local ISO over the wire today; multi-TZ refactor before second-region import |

---

## Forward compatibility

Current per-integration storage on `user` table (`google_refresh_token`,
`notion_enabled`) is appropriate for 2 integrations. When the third
integration lands (likely ICS in Phase 7), revisit migrating to a
generic `integration_connection` table:

```sql
CREATE TABLE integration_connection (
  user_id INTEGER NOT NULL,
  integration_id TEXT NOT NULL,
  auth_type TEXT NOT NULL,           -- 'oauth', 'api_key', 'file', 'url'
  status TEXT NOT NULL,              -- 'connected', 'error', 'expired'
  credentials_encrypted BYTEA,       -- Fernet-encrypted blob
  scopes TEXT[],
  connected_at TIMESTAMP NOT NULL,
  last_sync_at TIMESTAMP,
  last_error TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  PRIMARY KEY (user_id, integration_id)
);
```

The `GET /v1/integrations` endpoint's shape is already forward-
compatible with this schema — only the query inside changes. Frontend
code is unaffected.
