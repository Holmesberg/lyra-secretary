import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
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
        // Barzakh Neural Noir palette
        void: "#05070C",
        "void-2": "#0A0E18",
        ink: "#141B2A",
        signal: "#4DD4E8",
        "signal-neon": "#00E5FF",
        "signal-muted": "#2A7A87",
        ember: "#F5A96A",
        "ember-neon": "#FF8A3D",
        parchment: "#F0EFEA",
        dust: "#8A92A3",
        "dust-deep": "#4A5168",
        hairline: "rgba(240, 239, 234, 0.08)",
        "hairline-signal": "rgba(77, 212, 232, 0.25)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Chakra Petch", "sans-serif"],
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
        macro: "0.22em",
      },
      keyframes: {
        twinkle: {
          "0%, 100%": { opacity: "0.2" },
          "50%": { opacity: "0.7" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.4", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.05)" },
        },
        "scan-slide": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(200%)" },
        },
        "slow-rotate": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        "glow-flicker": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.85" },
          "52%": { opacity: "0.98" },
          "54%": { opacity: "0.88" },
        },
      },
      animation: {
        twinkle: "twinkle 4s ease-in-out infinite",
        "pulse-glow": "pulse-glow 5s ease-in-out infinite",
        "scan-slide": "scan-slide 8s linear infinite",
        "slow-rotate": "slow-rotate 60s linear infinite",
        "glow-flicker": "glow-flicker 6s ease-in-out infinite",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};
export default config;
