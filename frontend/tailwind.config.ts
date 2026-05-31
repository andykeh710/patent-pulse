import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        accent: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          200: "#99f6e4",
          300: "#5eead4",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0f766e",
          800: "#115e59",
          900: "#134e4a",
        },
        signal: {
          electric: "#6366f1",
          violet: "#8b5cf6",
          cyan: "#06b6d4",
          glow: "#818cf8",
        },
        score: {
          high: "#22c55e",
          medium: "#eab308",
          low: "#6b7280",
        },
        speculative: "#f59e0b",
        surface: {
          nav: "#0a0e27",
          card: "rgba(255,255,255,0.04)",
          glass: "rgba(255,255,255,0.06)",
        },
      },
      animation: {
        "signal-pulse": "signalPulse 3s ease-in-out infinite",
        "drift-slow": "drift 20s ease-in-out infinite",
        "drift-slower": "drift 30s ease-in-out infinite alternate",
        "scan-sweep": "scanSweep 4s ease-in-out infinite",
        "shine": "shine 1.5s ease-out infinite",
        "glow-border": "glowBorder 2s ease-in-out infinite",
      },
      keyframes: {
        signalPulse: {
          "0%, 100%": { opacity: "0.4", transform: "scale(1)" },
          "50%": { opacity: "0.8", transform: "scale(1.05)" },
        },
        drift: {
          "0%": { transform: "translate(0%, 0%)" },
          "33%": { transform: "translate(20%, -15%)" },
          "66%": { transform: "translate(-10%, 10%)" },
          "100%": { transform: "translate(0%, 0%)" },
        },
        scanSweep: {
          "0%": { top: "-4px", opacity: "0" },
          "10%": { opacity: "0.3" },
          "90%": { opacity: "0.3" },
          "100%": { top: "calc(100% + 4px)", opacity: "0" },
        },
        shine: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        glowBorder: {
          "0%, 100%": { borderColor: "rgba(99,102,241,0.3)" },
          "50%": { borderColor: "rgba(99,102,241,0.6)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
