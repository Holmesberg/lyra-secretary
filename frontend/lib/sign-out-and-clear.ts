"use client";

import type { QueryClient } from "@tanstack/react-query";
import { signOut } from "next-auth/react";
import { clearPersistedCache } from "@/lib/clear-persisted-cache";
import { clearBackendTokenCache } from "@/lib/api";

type SignOutOptions = Parameters<typeof signOut>[0];

export function clearClientAuthState(queryClient?: QueryClient): void {
  clearBackendTokenCache();
  queryClient?.clear();
  clearPersistedCache();
}

export function signOutAndClear(
  queryClient?: QueryClient,
  options: SignOutOptions = { callbackUrl: "/" }
) {
  clearClientAuthState(queryClient);
  return signOut(options);
}
