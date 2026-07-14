"use client";
/**
 * Category dropdown used in new-task and retroactive-log modals.
 *
 * Fixes the 2026-04-21 dogfood report: "categories don't persist
 * after creating a new category, it should assign a color." Previous
 * implementation rendered a hardcoded list from frontend/lib/categories.ts
 * — custom categories typed via "+ Create a new category…" landed on
 * the task row but were absent from the next modal open. Users re-typed
 * them every time.
 *
 * Behavior now:
 *   - Fetches /v1/users/me/categories on mount (TanStack Query, cached
 *     60s so rapid modal open/close doesn't hit the backend repeatedly)
 *   - Renders built-in categories in canonical order + any user-custom
 *     categories the backend returned (distinct values from user's
 *     non-voided tasks that aren't already built-in)
 *   - Trailing "+ Create a new category…" option bubbles up a sentinel
 *     value the parent modal handles by swapping to a text input
 *
 * Color assignment for rendered category badges happens elsewhere
 * (see frontend/lib/categories.ts `getCategoryColor`). This component
 * is purely the selection surface.
 */
import { useQuery } from "@tanstack/react-query";
import { CATEGORIES } from "@/lib/categories";
import { queryKeys } from "@/lib/query-keys";
import { getUserCategories } from "@/lib/tasks";

interface Props {
  value: string;
  onChange: (value: string) => void;
  id?: string;
  className?: string;
}

export function CategorySelect({ value, onChange, id = "category", className }: Props) {
  const categoriesQ = useQuery({
    queryKey: queryKeys.userCategories,
    queryFn: getUserCategories,
    staleTime: 60_000,
  });

  // Fallback to the hardcoded taxonomy if the endpoint hasn't
  // responded yet (fresh mount) or errored. Ensures the picker is
  // always usable — a network blip shouldn't block task creation.
  const builtIn = categoriesQ.data?.built_in ?? (CATEGORIES as readonly string[]);
  const custom = categoriesQ.data?.custom ?? [];

  return (
    <select
      data-testid={`${id}-select`}
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={
        className ??
        "h-9 rounded-sm border border-hairline-signal/30 bg-transparent px-3 text-sm text-parchment"
      }
    >
      {builtIn.map((c) => (
        <option key={c} value={c} className="bg-void">
          {c.replace("_", " ")}
        </option>
      ))}
      {custom.length > 0 && (
        <optgroup label="Your categories" className="bg-void">
          {custom.map((c) => (
            <option key={c} value={c} className="bg-void">
              {c.replace("_", " ")}
            </option>
          ))}
        </optgroup>
      )}
      <option value="__CREATE_NEW__" className="bg-void text-signal">
        + Create a new category…
      </option>
    </select>
  );
}
