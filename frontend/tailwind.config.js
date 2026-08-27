/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // Kiosk-friendly: large tap targets, calm clinical palette.
      colors: {
        kiosk: {
          bg: "#f4f7fb",
          primary: "#0b6b5b",
          accent: "#1f7ae0",
          danger: "#c62828",
          warn: "#e08a00",
        },
      },
    },
  },
  plugins: [],
};
