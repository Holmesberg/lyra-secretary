# Lyra Secretary — Frontend (Phase 2 scaffold)

Next.js 14 (App Router) + shadcn/ui + Tailwind + next-auth + TanStack Query.

## What's in this scaffold

- Sign in with Google (next-auth)
- Backend JWT minted in `lib/auth.ts` and forwarded as Bearer
- Consent modal on first login
- `/privacy` and `/terms` placeholder pages
- `lib/api.ts` typed fetch wrapper

The Today view, calendar view, table view, onboarding survey, and
insights dashboard land in Phases 3–6.

## Setup

1. Read `backend/docs/GOOGLE_OAUTH_SETUP.md` end to end. The Google
   Cloud Console clicks live there.
2. Copy `.env.local.example` to `.env.local` and fill in the values
   from §0 and §3 of that doc.
3. Install and run:

   ```bash
   npm install
   npm run dev
   ```

4. Open <http://localhost:3000>. Sign in with one of your test users.
5. Accept the consent modal. The backend should log a `POST` to
   `/v1/users/me/consent` and your `terms_accepted_at` should populate.
