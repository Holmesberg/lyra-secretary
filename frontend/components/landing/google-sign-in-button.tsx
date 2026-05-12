"use client";

import { useState } from "react";
import type {
  ButtonHTMLAttributes,
  FocusEvent,
  MouseEvent,
  PointerEvent,
} from "react";
import { cn } from "@/lib/utils";

type GoogleSignInButtonProps =
  ButtonHTMLAttributes<HTMLButtonElement> & {
    callbackUrl?: string;
    pendingLabel?: string;
  };

let cachedCsrfToken: string | null = null;
let cachedCsrfUntil = 0;
let csrfPromise: Promise<string> | null = null;

async function getCsrfToken(): Promise<string> {
  if (cachedCsrfToken && cachedCsrfUntil > Date.now()) {
    return cachedCsrfToken;
  }
  if (!csrfPromise) {
    csrfPromise = fetch("/api/auth/csrf")
      .then((res) => res.json())
      .then((body) => {
        cachedCsrfToken = body.csrfToken;
        cachedCsrfUntil = Date.now() + 60_000;
        return cachedCsrfToken as string;
      })
      .finally(() => {
        csrfPromise = null;
      });
  }
  return csrfPromise;
}

function warmGoogleSignIn() {
  void getCsrfToken();
  void fetch("/api/auth/providers").catch(() => {});
}

export function GoogleSignInButton({
  callbackUrl = "/today",
  pendingLabel = "Opening Google...",
  className,
  children,
  disabled,
  onClick,
  onFocus,
  onPointerEnter,
  ...props
}: GoogleSignInButtonProps) {
  const [pending, setPending] = useState(false);

  function handleFocus(event: FocusEvent<HTMLButtonElement>) {
    warmGoogleSignIn();
    onFocus?.(event);
  }

  function handlePointerEnter(event: PointerEvent<HTMLButtonElement>) {
    warmGoogleSignIn();
    onPointerEnter?.(event);
  }

  async function handleClick(event: MouseEvent<HTMLButtonElement>) {
    onClick?.(event);
    if (event.defaultPrevented) return;

    setPending(true);
    const fallback = `/api/auth/signin?callbackUrl=${encodeURIComponent(callbackUrl)}`;
    try {
      const csrfToken = await getCsrfToken();
      const body = new URLSearchParams({
        csrfToken,
        callbackUrl,
        json: "true",
      });
      const response = await fetch("/api/auth/signin/google", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const result = await response.json();
      window.location.assign(result?.url ?? fallback);
    } catch {
      window.location.assign(fallback);
    }
  }

  return (
    <button
      {...props}
      type="button"
      disabled={disabled || pending}
      aria-busy={pending}
      onFocus={handleFocus}
      onClick={handleClick}
      onPointerEnter={handlePointerEnter}
      className={cn(
        className,
        pending && "cursor-wait opacity-80"
      )}
    >
      {pending ? pendingLabel : children}
    </button>
  );
}
