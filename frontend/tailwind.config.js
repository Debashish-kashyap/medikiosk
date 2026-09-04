/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Outfit"', '"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        kiosk: {
          bg: "#f3f7fd",
          primary: "#2563eb",       // Electric / Royal Blue (from reference)
          primaryDark: "#1d4ed8",
          accent: "#3b82f6",
          accentLight: "#eff6ff",
          danger: "#ef4444",
          warn: "#f59e0b",
        },
      },
      boxShadow: {
        'glow-blue': '0 8px 30px -4px rgba(37, 99, 235, 0.25)',
        'glow-soft': '0 10px 40px -10px rgba(37, 99, 235, 0.12)',
        'card-clean': '0 4px 25px 0 rgba(15, 23, 42, 0.05)',
      },
    },
  },
  plugins: [],
};
