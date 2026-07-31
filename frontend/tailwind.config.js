/**
 * Tailwind config — Edama Accelerator official identity.
 * Exact palette pulled from the PowerPoint identity kit:
 *   Turquoise (primary) : #30BEBC
 *   Green (accent)      : #88C656
 *   Gray (support text) : #939598
 * Fonts: SOMAR (via Somar Sans) primary; Tahoma graceful fallback.
 */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Somar Sans"', 'SOMAR', 'Tahoma', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'Tahoma', 'monospace'],
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
        // Edama official brand tokens
        turquoise: {
          DEFAULT: "#30BEBC",
          50: "#E9F8F8",
          100: "#CBEEED",
          200: "#9FDEDD",
          400: "#4CC9C7",
          600: "#249A98",
          700: "#1C7E7D",
          900: "#0F4B4A",
        },
        edGreen: {
          DEFAULT: "#88C656",
          50: "#F1F8E9",
          200: "#CEE4A6",
          600: "#6BA841",
          700: "#4E7E2E",
        },
        edGray: {
          DEFAULT: "#939598",
          50: "#F5F5F6",
          200: "#D2D3D5",
          700: "#5F6266",
          900: "#33363A",
        },
        // Deep ink text (was navy; kept for legacy uses)
        navy: {
          DEFAULT: "#1C2934",
          50: "hsl(216, 20%, 96%)",
          100: "hsl(216, 20%, 90%)",
          400: "hsl(216, 20%, 40%)",
          700: "hsl(216, 30%, 20%)",
          900: "#0F1922",
        },
        ivory: {
          DEFAULT: "#FBFAF6",
          100: "#F5F3EC",
        },
        orange: {
          DEFAULT: "hsl(21, 90%, 52%)",
          50: "hsl(21, 90%, 96%)",
          600: "hsl(21, 90%, 45%)",
        },
      },
      backgroundImage: {
        // Faint chevron motif to echo the logo's arrow marks.
        "edama-chevrons": "url(\"data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20width%3D%2764%27%20height%3D%2740%27%20viewBox%3D%270%200%2064%2040%27%3E%3Cg%20fill%3D%27none%27%20stroke%3D%27%2388C656%27%20stroke-opacity%3D%270.08%27%20stroke-width%3D%272%27%3E%3Cpath%20d%3D%27M8%2020%20L20%208%20M8%2020%20L20%2032%27%2F%3E%3Cpath%20d%3D%27M28%2020%20L40%208%20M28%2020%20L40%2032%27%2F%3E%3Cpath%20d%3D%27M48%2020%20L60%208%20M48%2020%20L60%2032%27%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E\")",
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
