/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: "#0a2618",
        accent: "#22d3ee",
      },
    },
  },
  plugins: [],
};
