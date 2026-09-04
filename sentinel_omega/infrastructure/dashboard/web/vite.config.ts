import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/health": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/kpis": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/telemetry": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/consenso": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/analysis": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/agents": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/system": { target: "http://127.0.0.1:8787", changeOrigin: true },
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
      },
    },
  },
});
