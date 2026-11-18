import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        ink: "#241C16",
        canvas: "#F6F3EE",
        line: "#E7E1D8",
        brand: "#0E7C66",
        copper: "#C46B2C",
        mastered: "#0F7A4A",
        progress: "#C47B12",
        risk: "#BE123C",
      },
      boxShadow: {
        card: "0 1px 2px rgba(36, 28, 22, 0.05)",
        lift: "0 16px 36px rgba(36, 28, 22, 0.1)",
      },
    },
  },
  plugins: [],
};

export default config;
