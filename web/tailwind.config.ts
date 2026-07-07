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
        // Clean cool-neutral dark — analyst tool tone (no warmth)
        background: "#0C0D0F",
        surface: "#15171B",
        "surface-2": "#1E2127",
        border: "#2A2E36",
        "text-primary": "#ECEEF1",
        "text-dim": "#98A0AC",
        accent: "#EF4444",
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
        sans: ["Pretendard", "system-ui", "-apple-system", "sans-serif"],
        display: ["Fraunces", "Times New Roman", "Georgia", "serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
