import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
  // Tremor v3 generates color classes (e.g. fill-cyan-500, stroke-amber-500)
  // at runtime from `colors={["cyan"]}` props. Tailwind JIT cannot see those
  // strings in source files, so they get purged → invisible chart fills/
  // strokes on dark background. Safelist per official Tremor setup.
  safelist: [
    {
      pattern:
        /^(bg|text|border|fill|stroke|ring)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(50|100|200|300|400|500|600|700|800|900|950)$/,
      variants: ["hover", "focus"],
    },
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        border: "hsl(var(--border))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        // LyraOS brand palette — matches logo glow exactly.
        void: "#05070C",
        "void-2": "#0A0F1A",
        ink: "#141926",
        signal: "#4DD4E8",
        "signal-muted": "#2A7A87",
        ember: "#F5A96A",
        parchment: "#F0EFEA",
        dust: "#8A92A3",
        "dust-deep": "#4A5168",
        hairline: "rgba(240, 239, 234, 0.08)",
      },
      fontFamily: {
        sans: [
          "var(--font-geist-sans)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "var(--font-geist-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "monospace",
        ],
      },
      letterSpacing: {
        micro: "0.14em",
      },
      keyframes: {
        twinkle: {
          "0%, 100%": { opacity: "0.2" },
          "50%": { opacity: "0.7" },
        },
        "star-drift": {
          "0%": { transform: "translateY(0)" },
          "100%": { transform: "translateY(-24px)" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        twinkle: "twinkle 4s ease-in-out infinite",
        "star-drift": "star-drift 60s linear infinite",
        "fade-in-up": "fade-in-up 800ms ease-out forwards",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
