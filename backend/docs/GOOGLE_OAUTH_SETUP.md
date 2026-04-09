# Google OAuth Setup — Lyra Secretary

Step-by-step Google Cloud Console instructions to wire up Sign in with
Google for the Lyra Secretary web frontend. Follow this in order. The
**redirect URIs are the failure mode** — getting them wrong gives a
cryptic `redirect_uri_mismatch` error that wastes 30 minutes to debug.
The exact strings to register are in §4.

---

## 0. Generate the JWT shared secret first

The frontend (next-auth) and the backend (FastAPI) **must** use the
**identical** secret. Generate one cryptographically secure value and
put it in two places: `backend/.env` as `JWT_SECRET` and
`frontend/.env.local` as `NEXTAUTH_SECRET`.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run that command once. Copy the output. Use the **same** value in both
files. If they differ, every backend request from the frontend will
401.

---

## 1. Create the Google Cloud project

1. Go to <https://console.cloud.google.com/>.
2. Top bar → project selector → **New Project**.
3. Name: `lyra-secretary` (or anything — the human label only).
4. Location: leave as "No organization".
5. Click **Create**. Wait ~10 seconds for the project to provision,
   then make sure it's selected in the top bar.

---

## 2. Configure the OAuth consent screen

This is the screen Google shows the user when they click "Sign in with
Google" the first time.

1. Left sidebar → **APIs & Services** → **OAuth consent screen**.
2. User type: **External**. Click **Create**.
3. Fill in:
   - **App name**: `Lyra Secretary`
   - **User support email**: your Google email
   - **App logo**: skip for alpha
   - **App domain → Application home page**:
     `https://lyrasecretary.com` (placeholder is fine until DNS is up)
   - **App domain → Privacy policy link**:
     `https://lyrasecretary.com/privacy`
   - **App domain → Terms of service link**:
     `https://lyrasecretary.com/terms`
   - **Authorized domains**: `lyrasecretary.com`
   - **Developer contact email**: your Google email
4. Click **Save and Continue**.
5. **Scopes** screen: click **Add or Remove Scopes**, check
   `.../auth/userinfo.email` and `.../auth/userinfo.profile` and
   `openid`. Click **Update** → **Save and Continue**.
6. **Test users** screen: click **Add Users** and add the Google
   emails of the 3 alpha users *and* your own. Until the app is
   verified, only listed test users can sign in. **Save and Continue**.
7. **Summary** screen → **Back to Dashboard**.

> **Note on the unverified app warning.** While the project is in
> "Testing" mode and not verified by Google, every test user will see
> a "Google hasn't verified this app" warning before login. They click
> Advanced → "Go to Lyra Secretary (unsafe)" to proceed. This is
> expected for alpha. Verification is only needed at >100 users.

---

## 3. Create the OAuth 2.0 Client ID

1. Left sidebar → **APIs & Services** → **Credentials**.
2. Top → **+ Create Credentials** → **OAuth client ID**.
3. **Application type**: `Web application`.
4. **Name**: `Lyra Secretary Web` (internal label only).
5. **Authorized JavaScript origins** — add **both** of these,
   one per line:

   ```
   http://localhost:3000
   https://lyrasecretary.com
   ```

6. **Authorized redirect URIs** — add **both** of these,
   exactly as written, one per line. **Spelling, scheme, and trailing
   slash all matter:**

   ```
   http://localhost:3000/api/auth/callback/google
   https://lyrasecretary.com/api/auth/callback/google
   ```

   These come from next-auth's URL convention
   (`/api/auth/callback/<provider>`). Do not add or remove a trailing
   slash. Do not change `google` to `Google`. The `redirect_uri_mismatch`
   error comes from any single character not matching what next-auth
   actually sends.

7. Click **Create**.
8. A dialog pops up with **Your Client ID** and **Your Client Secret**.
   Copy both immediately — the secret is shown once.

---

## 4. Wire the credentials into the project

Two files need to be updated. Same client ID, same client secret, same
JWT secret.

### `backend/.env`

```env
# from §0
JWT_SECRET=<paste the python -c output here>
JWT_ALGORITHM=HS256

# from §3 step 8
GOOGLE_CLIENT_ID=<your client id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your client secret>

FRONTEND_URL=http://localhost:3000
```

### `frontend/.env.local`

```env
# Must equal backend/.env JWT_SECRET — see §0
NEXTAUTH_SECRET=<same value as JWT_SECRET above>
NEXTAUTH_URL=http://localhost:3000

# from §3 step 8
GOOGLE_CLIENT_ID=<same value as backend>
GOOGLE_CLIENT_SECRET=<same value as backend>

# Backend base URL the frontend calls
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 5. Verify locally

After both `.env` files are filled in:

```bash
# Backend
docker-compose up -d --build backend
curl http://localhost:8000/v1/health   # → {"status":"ok"}

# Frontend
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000` in a browser, click **Sign in with
Google**, choose your test-user account. You should land on the
authenticated app shell. The backend log should show a `POST` to
`/v1/users/me/consent` after you accept the consent modal.

If you get `redirect_uri_mismatch`, re-read §3 step 6 character by
character. The string in the Google Cloud Console must equal the URL
in the browser address bar at the moment of failure.

---

## 6. Production deploy checklist (when domain is live)

1. Add the production redirect URI to §3 step 6 (already there if you
   followed the instructions: `https://lyrasecretary.com/api/auth/callback/google`).
2. Update both `.env` files: `NEXTAUTH_URL=https://lyrasecretary.com`,
   `FRONTEND_URL=https://lyrasecretary.com`,
   `NEXT_PUBLIC_API_URL=https://lyrasecretary.com` (single origin via
   the nginx reverse proxy in Phase 8).
3. Re-run the `python -c "import secrets; ..."` command to generate a
   **new** production secret. Do not reuse the dev secret in prod.
4. Restart both containers.
