import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#c8102e", dark: "#a00d24" }, // DBS red
      },
    },
  },
  plugins: [],
};
export default config;
