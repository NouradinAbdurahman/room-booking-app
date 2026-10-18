import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The browser only ever talks to this origin; /api is proxied to Django,
// so no CORS is needed (ADR 0004). The Host header is left as the browser
// sent it so Django's CSRF origin check sees localhost:5173.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: false },
    },
  },
  test: {
    environment: "node",
  },
});
