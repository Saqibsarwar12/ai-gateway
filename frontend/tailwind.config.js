/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#030711",
        foreground: "#f1f5f9",
        card: "#0d1424",
        "card-border": "#1e2d4d",
      },
    },
  },
  plugins: [],
};
