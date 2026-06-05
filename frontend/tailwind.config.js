/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        moss: "#2f5d50",
        cloud: "#eef2ef",
        signal: "#d86f45",
        steel: "#46606a",
      },
      boxShadow: {
        panel: "0 18px 45px rgba(23, 32, 27, 0.12)",
      },
    },
  },
  plugins: [],
};
