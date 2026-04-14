import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0a",
        surface: "#171717",
        "surface-2": "#262626",
        border: "#404040",
        "text-primary": "#fafafa",
        "text-dim": "#a3a3a3",
        accent: "#dc2626",
        "cat-war": "#991b1b",
        "cat-civil-war": "#dc2626",
        "cat-terrorism": "#6d28d9",
        "cat-mass-atrocity": "#7f1d1d",
        "cat-state-violence": "#db2777",
        "cat-cartel": "#d97706",
        "cat-communal": "#0d9488",
        "cat-insurgency": "#2563eb",
        "cat-counterterrorism": "#16a34a",
        "cat-armed-violence": "#475569",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Inter Tight", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
