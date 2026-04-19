import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input
    type={type}
    ref={ref}
    className={cn(
      "flex h-9 w-full rounded-sm border border-hairline-signal/30 bg-transparent px-3 py-1 text-sm text-parchment shadow-sm transition-colors placeholder:text-dust-deep focus-visible:border-signal/60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-signal/40 disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  />
));
Input.displayName = "Input";
