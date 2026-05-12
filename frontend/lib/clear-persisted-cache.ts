/**
 * clearPersistedCache — wipe the React Query persister's localStorage
 * entry so the cache doesn't survive sign-out.
 *
 * Called from AppShell's signOut() handler before redirecting to /. If
 * we don't clear, the next user to sign in on the same browser would
 * see the previous user's persisted data flash on first paint (before
 * their own queries refetch + overwrite). Same blast-radius concern as
 * not clearing localStorage on logout in any auth-sensitive app.
 *
 * Key matches `createSyncStoragePersister` config in components/providers.tsx.
 */
const PERSISTER_KEYS = ["lyra-rq-cache:v1", "lyra-rq-cache:v2"];

export function clearPersistedCache(): void {
  if (typeof window === "undefined") return;
  try {
    for (const key of PERSISTER_KEYS) {
      window.localStorage.removeItem(key);
    }
  } catch {
    // localStorage access can throw in private-browsing modes / quota
    // exhaustion / etc. Silent fail — clear is best-effort hygiene,
    // not a security boundary (NextAuth session is the actual auth).
  }
}
