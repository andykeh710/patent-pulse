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
          400: "#7b94ff",
          500: "#6b8cff",
          600: "#5570d4",
          700: "#3f55aa",
          800: "#2a3b7f",
          900: "#172255",
        },
        surface: {
          base: "#08090D",
          elevated: "#101318",
          card: "#151920",
          glass: "rgba(255,255,255,0.025)",
          overlay: "rgba(0,0,0,0.60)",
        },
        score: {
          high: "#34D399",
          medium: "#F59E0B",
          low: "#9BA1B0",
        },
        warning: "#F59E0B",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.5s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
      },
    },
  },
  plugins: [],
};

export default config;
