import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The kiosk calls the API at VITE_API_BASE (default localhost:8000).
// Backend CORS is open in dev, so no proxy is required.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
