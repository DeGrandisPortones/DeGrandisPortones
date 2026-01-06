import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({
  server: {
    port: 5173,
    proxy: {
      // Proxy API and web session to Odoo (adjust target if needed)
      "/api": { target: "http://localhost:8069", changeOrigin: true },
      "/web": { target: "http://localhost:8069", changeOrigin: true },
      "/my": { target: "http://localhost:8069", changeOrigin: true },
    },
  },
  plugins: [react()],
  build: {
    manifest: true,
    outDir: path.resolve(__dirname, "../odoo_addons/dflex_presupuestador_spa/static/app"),
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.tsx"),
    },
  },
}));
