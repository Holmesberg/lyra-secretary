"use client";

import { useState } from "react";
import type { ButtonHTMLAttributes, MouseEvent } from "react";
import { cn } from "@/lib/utils";

type GoogleSignInButtonProps =
  ButtonHTMLAttributes<HTMLButtonElement> & {
    callbackUrl?: string;
    pendingLabel?: string;
  };

export function GoogleSignInButton({
  callbackUrl = "/today",
  pendingLabel = "Opening Google...",
  className,
  children,
  disabled,
  onClick,
  ...props
}: GoogleSignInButtonProps) {
  const [pending, setPending] = useState(false);

  async function handleClick(event: MouseEvent<HTMLButtonElement>) {
    onClick?.(event);
    if (event.defaultPrevented) return;

    setPending(true);
    const fallback = `/api/auth/signin?callbackUrl=${encodeURIComponent(callbackUrl)}`;
    try {
      const csrf = await fetch("/api/auth/csrf").then((res) => res.json());
      const body = new URLSearchParams({
        csrfToken: csrf.csrfToken,
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
      onClick={handleClick}
      className={cn(
        className,
        pending && "cursor-wait opacity-80"
      )}
    >
      {pending ? pendingLabel : children}
    </button>
  );
}
