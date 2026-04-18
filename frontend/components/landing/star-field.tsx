"use client";

import { useMemo } from "react";

/**
 * Observatory background — ~80 stars positioned on a deterministic seeded-random
 * grid so SSR and client render match. Three size/opacity classes for depth.
 * Twinkle via CSS keyframe (Tailwind `animate-twinkle`); the whole layer drifts
 * slowly via `animate-star-drift` so the viewport feels alive without asking
 * anything from the reader. Respects prefers-reduced-motion through Tailwind's
 * motion-safe variant at the consumer.
 */
export function StarField() {
  const stars = useMemo(() => generateStars(80), []);
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      <div className="absolute inset-0 motion-safe:animate-star-drift">
        {stars.map((s, i) => (
          <span
            key={i}
            className={`absolute rounded-full bg-parchment ${
              s.size === "xs"
                ? "h-[1px] w-[1px] opacity-40"
                : s.size === "sm"
                ? "h-[2px] w-[2px] opacity-60"
                : "h-[3px] w-[3px] opacity-80"
            } motion-safe:animate-twinkle`}
            style={{
              top: `${s.top}%`,
              left: `${s.left}%`,
              animationDelay: `${s.delay}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function generateStars(n: number) {
  // Deterministic LCG so SSR/CSR agree.
  let seed = 1337;
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) % 0xffffffff;
    return seed / 0xffffffff;
  };
  return Array.from({ length: n }, () => {
    const r = rand();
    return {
      top: rand() * 100,
      left: rand() * 100,
      size: r < 0.6 ? "xs" : r < 0.9 ? "sm" : ("md" as const),
      delay: rand() * 4,
    };
  });
}
