import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        popover: "hsl(var(--popover))",
        "popover-foreground": "hsl(var(--popover-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        secondary: "hsl(var(--secondary))",
        "secondary-foreground": "hsl(var(--secondary-foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        accent: "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      fontFamily: {
        sans: ["Geist Sans", "system-ui", "sans-serif"],
      },
      keyframes: {
        marquee: { to: { transform: "translateX(-50%)" } },
        "title-sheen": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        "grid-flow": { to: { backgroundPosition: "180px 120px" } },
        orbit: { to: { transform: "translate(-50%, -50%) rotate(360deg)" } },
        "orbit-reverse": { to: { transform: "translate(-50%, -50%) rotate(-360deg)" } },
        "float-core": {
          "0%, 100%": { transform: "translate(-50%, -50%) translateY(-8px)" },
          "50%": { transform: "translate(-50%, -50%) translateY(8px)" },
        },
      },
      animation: {
        marquee: "marquee 20s linear infinite",
        "title-sheen": "title-sheen 8s ease-in-out infinite",
        "grid-flow": "grid-flow 18s linear infinite",
        orbit: "orbit 14s linear infinite",
        "orbit-reverse": "orbit-reverse 20s linear infinite",
        "float-core": "float-core 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
