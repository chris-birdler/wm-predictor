/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // FIFA editorial: light surfaces, near-black text, minimal accent use.
        fifa: {
          ink: "#0A0A0F",        // primary text
          dim: "#4B5563",        // secondary text
          muted: "#9CA3AF",      // tertiary text / icons
          line: "#E5E7EB",       // dividers / borders
          surface: "#FFFFFF",    // cards
          page: "#F5F5F7",       // page background
          chip: "#F3F4F6",       // pill / tag bg
          pink: "#E5007E",       // brand accent — magenta
          magenta: "#C8006D",
          teal: "#00BEC8",
          green: "#00875A",      // advancing / live
          red: "#DC2626",        // eliminated / loss
          gold: "#F59E0B",       // best-third highlight
        },
        accent: "#E5007E",
      },
      fontFamily: {
        display: ['"Inter Tight"', "Inter", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "fifa-gradient":
          "linear-gradient(135deg, #E5007E 0%, #C8006D 28%, #00BEC8 62%, #00875A 86%, #F59E0B 100%)",
      },
    },
  },
  plugins: [],
};
