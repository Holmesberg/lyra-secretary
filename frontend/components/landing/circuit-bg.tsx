"use client";

/**
 * Circuit-trace substrate — a faint geometric pattern that replaces the
 * plain dark background. Pure SVG, no image dependency. Tiled via <pattern>.
 * Opacity kept very low so it reads as texture, not decoration.
 */
export function CircuitBg() {
  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.06]"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <pattern
          id="circuit"
          width="140"
          height="140"
          patternUnits="userSpaceOnUse"
        >
          {/* Horizontal trace with node */}
          <path
            d="M 0 30 L 40 30 L 55 45 L 100 45 L 115 30 L 140 30"
            fill="none"
            stroke="#4DD4E8"
            strokeWidth="0.6"
          />
          <circle cx="55" cy="45" r="1.5" fill="#4DD4E8" />
          <circle cx="100" cy="45" r="1.5" fill="#4DD4E8" />

          {/* Vertical trace */}
          <path
            d="M 30 60 L 30 90 L 50 110 L 70 110"
            fill="none"
            stroke="#4DD4E8"
            strokeWidth="0.6"
          />
          <circle cx="30" cy="90" r="1.2" fill="#4DD4E8" />

          {/* Diagonal accent */}
          <path
            d="M 90 80 L 110 80 L 125 95 L 125 125"
            fill="none"
            stroke="#F5A96A"
            strokeWidth="0.5"
            opacity="0.8"
          />
          <circle cx="125" cy="95" r="1.2" fill="#F5A96A" />

          {/* Empty pad marks */}
          <circle
            cx="15"
            cy="110"
            r="2"
            fill="none"
            stroke="#4DD4E8"
            strokeWidth="0.4"
          />
          <circle
            cx="115"
            cy="15"
            r="2"
            fill="none"
            stroke="#4DD4E8"
            strokeWidth="0.4"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#circuit)" />
    </svg>
  );
}
