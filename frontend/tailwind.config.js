/** Tailwind config — Edama V8 palette (Navy / Turquoise / Ivory / Orange). */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans Arabic"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        // V8 tokens
        navy: {
          DEFAULT: "hsl(216, 65%, 11%)",
          50: "hsl(216, 30%, 96%)",
          100: "hsl(216, 30%, 90%)",
          400: "hsl(216, 40%, 40%)",
          700: "hsl(216, 55%, 20%)",
          900: "hsl(216, 65%, 11%)",
        },
        turquoise: {
          DEFAULT: "hsl(180, 53%, 47%)",
          50: "hsl(180, 45%, 96%)",
          200: "hsl(180, 50%, 85%)",
          600: "hsl(180, 55%, 40%)",
        },
        ivory: {
          DEFAULT: "hsl(40, 33%, 98%)",
          100: "hsl(40, 30%, 94%)",
        },
        orange: {
          DEFAULT: "hsl(21, 90%, 52%)",
          50: "hsl(21, 90%, 96%)",
          600: "hsl(21, 90%, 45%)",
        },
        edGreen: "hsl(83, 51%, 51%)",
        edGray: "hsl(0, 0%, 61%)",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
