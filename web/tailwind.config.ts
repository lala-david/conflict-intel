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
        // Editorial / newsroom — warm near-black "newsprint dark", cream ink, signature red
        background: "#14110D",
        surface: "#1C1813",
        "surface-2": "#26211A",
        border: "#38322A",
        "text-primary": "#F5EFE3",
        "text-dim": "#A89F8D",
        accent: "#D6482F",
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
        // Editorial serif for headlines/mastheads
        display: ["Fraunces", "Georgia", "Times New Roman", "serif"],
        serif: ["Fraunces", "Georgia", "serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
