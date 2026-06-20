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
        accent: {
          50: "#eef2ff",
          100: "#dde5ff",
          200: "#bcccff",
          300: "#94a9ff",
          400: "#7ba4ff",
          500: "#5b8af7",
          600: "#4f6fcf",
          700: "#3a56aa",
          800: "#2a3b7f",
          900: "#172255",
        },
        surface: {
          base: "#08090D",
          elevated: "#111318",
          card: "#161920",
          glass: "rgba(255,255,255,0.025)",
          overlay: "rgba(0,0,0,0.60)",
        },
        score: {
          high: "#10B981",
          medium: "#F59E0B",
          low: "#9AA0AE",
        },
        warning: "#F59E0B",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.15s ease-out",
        "slide-up": "slideUp 0.2s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
    },
  },
  plugins: [],
};

export default config;
