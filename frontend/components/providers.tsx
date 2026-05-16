"use client";
/**
 * Providers — global React Query + NextAuth setup.
 *
 * 2026-04-30: persistence layer added so the app feels instant on
 * reopen. The in-memory React Query cache normally dies on tab close;
 * `PersistQueryClientProvider` mirrors it to localStorage and rehydrates
 * on next page load. Effect compounded with the server-side caches we
 * already shipped (me_cache 30s, tasks_range_cache 60s):
 *
 *   - First paint after reopen: localStorage hit → ~5ms
 *   - Background refetch hits Redis cache (warm 60s window): ~5ms
 *   - UI updates only if data actually changed
 *
 * vs. status quo before this commit: cold reopen paid full Cairo→
 * Supabase RTT for every query (~700ms each, 5 in parallel).
 *
 * Cache lifetime:
 *   - gcTime 24h — data older than 24h is dropped from the persist store
 *     on next dehydrate. Long enough that overnight reopens are fast,
 *     short enough that no truly stale data accumulates indefinitely.
 *   - staleTime defaults stay per-query (most queries set their own
 *     30-60s windows for refetch behavior; persistence is independent).
 *
 * Auth boundary:
 *   - On signOut()/401/account deletion, callers use
 *     `lib/sign-out-and-clear.ts` so React Query memory, backend token
 *     cache, and the persisted cache are invalidated together.
 */
import { SessionProvider } from "next-auth/react";
import type { Session } from "next-auth";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { useState } from "react";
import { primeBackendToken } from "@/lib/api";

const ONE_HOUR = 1000 * 60 * 60;
const TWENTY_FOUR_HOURS = ONE_HOUR * 24;
const PERSISTED_CACHE_BUSTER = "v2";
const PERSISTED_CACHE_KEY = `lyra-rq-cache:${PERSISTED_CACHE_BUSTER}`;
const MAX_PERSISTED_QUERY_BYTES = 100_000;
const PERSISTED_QUERY_ROOTS = new Set([
  "me",
  "tasks",
  "tasks-range",
  "calendar-events",
  "calendar-events-today",
  "deadlines",
  "integrations",
  "insights",
  "proximity",
  "proximity-trend",
]);

type PersistableQuery = {
  queryKey: unknown;
  state: {
    status: string;
    dataUpdatedAt?: number;
    data: unknown;
  };
};

function shouldPersistQuery(query: PersistableQuery): boolean {
  if (query.state.status !== "success") return false;

  const root = Array.isArray(query.queryKey) ? query.queryKey[0] : null;
  if (typeof root !== "string" || !PERSISTED_QUERY_ROOTS.has(root)) {
    return false;
  }

  const dataUpdatedAt = query.state.dataUpdatedAt ?? 0;
  if (Date.now() - dataUpdatedAt > ONE_HOUR) return false;

  try {
    return JSON.stringify(query.state.data).length <= MAX_PERSISTED_QUERY_BYTES;
  } catch {
    return false;
  }
}

export function Providers({
  children,
  session,
}: {
  children: React.ReactNode;
  session?: Session | null;
}) {
  primeBackendToken((session as any)?.backendToken as string | undefined);

  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Poll only where a surface explicitly opts in. A global poll
            // makes heavy analytics queries refetch while mounted, which
            // turns tab clicks into backend contention.
            refetchInterval: false,
            refetchOnWindowFocus: false,
            // gcTime governs how long INACTIVE queries stay in cache
            // (formerly cacheTime in v4). Bumped from the default 5min
            // to 24h so persisted-and-rehydrated queries are usable.
            // Active queries always stay; inactive ones aged > 24h get
            // dropped on next dehydrate.
            gcTime: TWENTY_FOUR_HOURS,
          },
        },
      })
  );

  // Persister — synchronous localStorage adapter. Per-tab storage; if
  // the user opens the same Lyra account in two tabs, each maintains
  // its own cache (last-writer wins on dehydrate). For our scale this
  // is fine; if it ever bites we can switch to indexedDB.
  const [persister] = useState(() => {
    if (typeof window === "undefined") {
      // SSR safety — return a no-op-shaped persister; Provider will
      // skip persistence on the server. Real one rehydrates on hydrate.
      return undefined;
    }
    return createSyncStoragePersister({
      storage: window.localStorage,
      // Bump the key when we change the cache shape so old persisted
      // payloads don't deserialize wrong. Mirrors the me_cache 'v1'
      // versioning convention.
      key: PERSISTED_CACHE_KEY,
      // Throttle writes — React Query writes the full cache on every
      // mutation by default, which can be hundreds of writes/sec on
      // a chatty session. 1s window is invisible to humans.
      throttleTime: 1000,
    });
  });

  // SSR — render the plain provider without persistence (no window).
  // First client paint hydrates from localStorage when the component
  // re-renders client-side and `persister` is set.
  if (!persister) {
    return (
      <SessionProvider
        session={session}
        refetchOnWindowFocus={false}
        refetchInterval={0}
      >
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </SessionProvider>
    );
  }

  return (
    <SessionProvider
      session={session}
      refetchOnWindowFocus={false}
      refetchInterval={0}
    >
      <PersistQueryClientProvider
        client={qc}
        persistOptions={{
          persister,
          maxAge: TWENTY_FOUR_HOURS,
          // Mirror the cache key version in the buster so a deploy
          // can invalidate everyone's stale cache by bumping it.
          buster: PERSISTED_CACHE_BUSTER,
          dehydrateOptions: {
            shouldDehydrateQuery: shouldPersistQuery,
          },
        }}
      >
        {children}
      </PersistQueryClientProvider>
    </SessionProvider>
  );
}
