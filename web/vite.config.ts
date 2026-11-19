import { defineConfig } from "vite";

export default defineConfig({
  // Dev server: proxy API calls to the local backend.
  // In production (Vercel), VITE_API_BASE_URL is set to the backend host
  // and the frontend calls it directly — no proxy is needed.
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
