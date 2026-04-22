# Strategic Decisions — April 22, 2026

One structural refactor plus a publishing-timing call. Grounded in the
2026-04-21 Google Calendar push (see
`strategic_decisions_april_21.md §6 / §6.1`) and the retention audit
after Spring School week 1.

---

## 1. Identity-Authorization Split — Settings → Integrations panel shipped

**Previous state (2026-04-21):** NextAuth's Google provider requested
`openid email profile + calendar.readonly` at sign-in. Every new
user's first interaction with Lyra was a Google consent screen asking
for calendar access. Two consequences:

1. **Testing-mode wall on every signup.** Because `calendar.readonly`
   is a sensitive scope, Google blocks consent from any account not
   on the OAuth app's test-user list. With only 5 test-user slots
   used so far, any new external user hitting the landing page
   couldn't sign up at all.
2. **Scope decision at the wrong moment.** Users on the landing page
   hadn't yet seen Lyra's value — asking for calendar access at that
   moment is a trust request without context.

**Clarified state (today):** Sign-in asks for identity only —
`openid email profile`, non-sensitive, no OAuth verification
required. Third-party integrations acquire their scopes
**incrementally**, user-triggered, from a new **Settings →
Integrations** panel. Each integration has its own Connect button,
its own consent screen, its own disconnect affordance.

**Data that forced the refactor (2026-04-22 activity audit):**

| Non-operator user | Signed up | Onboarded | Tasks | Returning | GCal connected |
|---|---|---|---|---|---|
| u3 mariamnasser | 04-16 | **No** | 0 | No | No |
| u4 ghadatawfik | 04-16 | 04-18 | 2 | No (mom, guided demo) | No |
| u5 t90seegg2006 | 04-17 | 04-18 | 3 | **Yes** (2 active days) | No |
| u6 medo.tamer | 04-17 | 04-20 | 5 | **Yes** (2 active days) | No |
| u7 meroo0jj | 04-18 | **No** | 0 | No | No |

**Zero of the external users have connected Google Calendar.** Every
one of them consented to `calendar.readonly` at sign-in and then
never used it. The scope was pure drag. Worse: 2/5 never completed
onboarding at all — the sign-in friction is a plausible contributor
to the 29% onboarding-bounce rate.

**Ship decision:** refactor today. The unblock (new users sign up
without a calendar consent screen) is immediate; the long-term
scaffold (unified Integrations panel with per-provider cards) is
reusable for Notion, ICS, Outlook, Gmail, Slack, and any future
OAuth-shaped provider.

**Architectural principles locked in** (see
`docs/integrations_architecture.md`):
- Sign-in scope is identity-only, forever.
- Every integration connects from Settings with its own consent
  moment and its own scope request.
- Refresh tokens stay server-side; client JS never sees them.
- External data stays out of the `task` table unless explicitly
  marked with an `external_source` field (protects H1 test set).
- Every new integration ships with a pre-registered kill criterion
  measured at a specific sample size.

**What changed in code (eight files):**
- `frontend/lib/auth.ts` — scope dropped to identity; removed
  refresh_token capture + `hasGoogleRefreshToken` surface.
- `frontend/app/(app)/layout.tsx` — removed the auto-handshake
  useEffect that forwarded the sign-in refresh_token.
- `frontend/app/api/calendar/setup/route.ts` — **deleted.** No
  longer has a source of tokens to forward.
- `frontend/app/api/integrations/google-calendar/connect/route.ts`
  — NEW, OAuth initiation with signed state (10-min TTL, HS256,
  purpose=`gcal_connect`).
- `frontend/app/api/integrations/google-calendar/callback/route.ts`
  — NEW, validates state, exchanges code, account-match check via
  `id_token.email`, forwards refresh_token to backend.
- `backend/app/api/v1/endpoints/integrations.py` — NEW, `GET
  /v1/integrations` returns per-user status per registered integration.
- `frontend/lib/integrations.ts`, `components/integration-card.tsx`,
  `components/integrations-section.tsx` — NEW, the UI pattern.
- `frontend/app/(app)/settings/page.tsx` — hosts the new section.

**Backward compatibility:** the operator's existing
`google_refresh_token` stays valid. `calendar_sync.py` is untouched.
No database migration. Users who were connected at the old sign-in
time remain connected without re-doing the OAuth flow.

**Manual operator step (required before live deploy):** add the new
redirect URI to the Google Cloud Console OAuth client:
- `https://lyraos.org/api/integrations/google-calendar/callback`
- `http://localhost:3000/api/integrations/google-calendar/callback`

---

## 2. OAuth Verification — deferred until retention signal

**Question raised:** should we submit the app for Google OAuth
verification now to escape Testing-mode?

**Answer: no. Wait for (a) VT-23 clearing its kill threshold, OR (b)
≥10 returning users, whichever comes first.**

**Rationale:**
- **Verification is weeks of back-and-forth.** Google requires a
  privacy policy at the verified domain, a demo video showing each
  scope's usage, homepage + ToS + domain verification, and often
  requests changes. 4–6 weeks of async review cycles during Spring
  School is the wrong investment.
- **VT-23 might kill the calendar feature.** Pre-registered kill:
  at n≥20 connected users, if <15% of past events get marked within
  7 days, the external-attendance signal is too sparse to justify
  ongoing investment. Verifying now risks burning effort on a
  feature we may deprioritize.
- **Incremental OAuth isolates the pain.** With Decision 1 shipped,
  only users who click "Connect Google Calendar" hit the test-user
  wall. Users who don't touch calendar are unaffected. The operator
  adds Testing-mode test users one at a time as real demand lands.
- **Retention signal first, verification effort second.** 2 returning
  external users is not a verification-worthy cohort. When n≥10,
  priorities shift.

**Pre-registered triggers to revisit:**
- VT-23 retention lift ≥1.25× at n≥20 → verify immediately.
- ≥10 users actively want to connect calendar and hit the wall →
  verify immediately.
- Non-calendar sensitive scope needed (Gmail, Drive) → verification
  bundle includes both.

**Deferred prep (low-priority, start in background):**
- Privacy policy at `lyraos.org/privacy` (route already exists;
  content scrub needed for OAuth-verification-ready wording).
- ToS at `lyraos.org/terms` (same).
- Demo video script for `calendar.readonly` scope usage (per
  Google's verification video requirements).
- Domain verification in Google Search Console (one-time).

These cost ~2 hours of prep work and are worth having ready so that
when the trigger fires, verification submission is same-day.

---

## 3. Retention data surfaced for clarity

During the review that triggered Decision 1, the activity audit
clarified the real cohort shape:

- **Operator alts:** u1 (main), u2 (asabryhafez — operator alt), u9
  (moriartyholmesberg — operator alt). Do not count toward external
  adoption.
- **Guided demo:** u4 (ghadatawfik — operator's mother) used the app
  once with guidance and couldn't return independently. Signal: a
  usability/independence gap for the low-tech-literacy segment, not
  churn. Investigation owed: what specifically blocked her from
  coming back?
- **Signup-to-no-onboarding:** u3 (mariamnasser), u7 (meroo0jj) —
  two users consented to terms, reached the app shell, and never
  created a task. 29% bounce. Investigation owed: what's on the
  first screen that doesn't land?
- **Real returning users:** u5 (t90seegg2006), u6 (medo.tamer). Both
  have 2 active days across their first 5 days, both hit "execute 1
  task then come back" successfully. These are the only two users
  currently generating real retention signal.

VT-23 threshold (n≥20 connected users) is ~18 external users away.
VT-17 (pause prediction) self-activates at 7 days per-user pause
history — only the operator has enough data to trigger it at all.

**Implication for product shape:** the first-screen + guided-demo
failure modes are more urgent than any feature work. Next-session
candidates:
- UX audit of the sign-in → first-task path (what does u3/u7 see?)
- Mom-proof onboarding test pass (what did u4 get stuck on?)
- First-week email nudge for users who onboarded but haven't come
  back in 48h.

None of these ship this round — but Decision 1 removes the
calendar-scope drag from that path, which is the biggest single
friction we can see today.
