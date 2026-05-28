import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // VS Code dark theme palette
        ide: {
          bg:        "#1e1e1e",
          sidebar:   "#252526",
          panel:     "#2d2d2d",
          border:    "#3e3e3e",
          input:     "#3c3c3c",
          accent:    "#0e639c",
          "accent-hover": "#1177bb",
          text:      "#d4d4d4",
          muted:     "#6e7681",
          user:      "#264f78",
          assistant: "#2d2d2d",
          active:    "#37373d",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
