const defaultTheme = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(240 5% 84%)",
        background: "hsl(0 0% 100%)",
        foreground: "hsl(240 10% 3.9%)",
        muted: "hsl(240 4.8% 95.9%)",
        primary: { DEFAULT: "#2563EB", foreground: "#ffffff" },  // ← your brand color
        ring: "#2563EB"
      },
      borderRadius: { xl: "1rem", "2xl": "1.25rem" },
      fontFamily: { sans: ["Inter", ...defaultTheme.fontFamily.sans] },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up":   { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } }
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out"
      }
    },
  },
  plugins: [require("tailwindcss-animate")],
};
